"""
Modernized batch uploader for Google Earth Engine assets.

Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import ee
import requests
from requests.adapters import HTTPAdapter
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm
from urllib3.util.retry import Retry

from .metadata_loader import MetadataCollection

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class AssetState(Enum):
    """Asset upload states for tracking."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskState(Enum):
    """Earth Engine task states."""

    RUNNING = "RUNNING"
    PENDING = "PENDING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class UploadState:
    """Track upload progress for resumability."""

    assets: Dict[str, str]  # filename -> state
    failed_reasons: Dict[str, str]  # filename -> error message
    timestamp: float
    collection_path: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def save(self, state_file: Path):
        """Save state to disk."""
        with open(state_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, state_file: Path):
        """Load state from disk."""
        if not state_file.exists():
            return None
        with open(state_file, "r") as f:
            return cls.from_dict(json.load(f))


class PathValidator:
    """Validate GEE paths and filenames."""

    VALID_CHARS = r"^[a-zA-Z0-9/_-]+$"

    @staticmethod
    def validate_path(path: str) -> Tuple[bool, Optional[str]]:
        """Validate a GEE path."""
        import re

        if not re.match(PathValidator.VALID_CHARS, path):
            return False, (
                "GEE path cannot have spaces and can only contain "
                "letters, numbers, hyphens, underscores, and forward slashes"
            )
        return True, None


class SessionManager:
    """Manage Google authentication sessions with retry logic."""

    COOKIE_FILE = Path("cookie_jar.json")

    def __init__(self):
        self.session = self._create_session_with_retry()
        self._url_lock = __import__("threading").Lock()

    def _create_session_with_retry(self) -> requests.Session:
        """Create a session with automatic retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def load_cookies(self) -> bool:
        """Load and validate cookies."""
        if not self.COOKIE_FILE.exists():
            return self._prompt_for_cookies()

        with open(self.COOKIE_FILE, "r") as f:
            cookie_list = json.load(f)

        if self._validate_cookies(cookie_list):
            logger.info("Using saved cookies")
            self._set_cookies(cookie_list)
            return True
        else:
            logger.warning("Saved cookies expired")
            return self._prompt_for_cookies()

    def _validate_cookies(self, cookie_list: list) -> bool:
        """Check if cookies are still valid."""
        test_session = requests.Session()
        for cookie in cookie_list:
            test_session.cookies.set(cookie["name"], cookie["value"])

        try:
            response = test_session.get(
                "https://code.earthengine.google.com/assets/upload/geturl", timeout=10
            )
            return (
                response.status_code == 200
                and "application/json" in response.headers.get("content-type", "")
            )
        except requests.RequestException:
            return False

    def _prompt_for_cookies(self) -> bool:
        """Prompt user for cookie list."""
        try:
            cookie_input = input("Enter your Cookie List: ")
            cookie_list = json.loads(cookie_input)

            with open(self.COOKIE_FILE, "w") as f:
                json.dump(cookie_list, f, indent=2)

            self._set_cookies(cookie_list)
            self._clear_screen()
            return True
        except (json.JSONDecodeError, KeyboardInterrupt) as e:
            logger.error(f"Failed to load cookies: {e}")
            return False

    def _set_cookies(self, cookie_list: list):
        """Set cookies in session."""
        for cookie in cookie_list:
            self.session.cookies.set(cookie["name"], cookie["value"])

    @staticmethod
    def _clear_screen():
        """Clear terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")
        # Reset terminal settings on Unix
        if sys.platform in ["linux", "darwin"]:
            subprocess.run(["stty", "icanon"], check=False)

    def get_upload_url(self) -> Optional[str]:
        """Get GCS upload URL. Thread-safe for concurrent calls."""
        with self._url_lock:
            try:
                response = self.session.get(
                    "https://code.earthengine.google.com/assets/upload/geturl",
                    timeout=10,
                )
                return response.json().get("url")
            except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to get upload URL: {e}")
                return None


class EETaskManager:
    """Manage Earth Engine tasks."""

    def __init__(self):
        ee.Initialize()

    def get_task_count(self, states: Optional[List[TaskState]] = None) -> int:
        """Count tasks in specified states."""
        if states is None:
            states = [TaskState.RUNNING, TaskState.PENDING]

        state_names = [s.value for s in states]
        operations = ee.data.listOperations()

        return sum(
            1
            for task in operations
            if task.get("metadata", {}).get("state") in state_names
        )

    def get_ingestion_tasks(self, collection_path: str) -> Set[str]:
        """Get asset names with pending/running ingestion tasks."""
        tasks = set()
        for task in ee.data.listOperations():
            metadata = task.get("metadata", {})
            if metadata.get("type") == "INGEST_IMAGE" and metadata.get("state") in [
                TaskState.RUNNING.value,
                TaskState.PENDING.value,
            ]:
                desc = metadata.get("description", "")
                # Extract asset name from description
                if desc:
                    asset_name = desc.split(":")[-1].split("/")[-1].replace('"', "")
                    tasks.add(asset_name)
        return tasks

    def wait_for_capacity(self, max_tasks: int = 2800, check_interval: int = 300):
        """Wait until task count is below threshold."""
        task_count = self.get_task_count()
        while task_count >= max_tasks:
            logger.info(
                f"Task limit reached ({task_count}/{max_tasks}). "
                f"Waiting {check_interval}s..."
            )
            time.sleep(check_interval)
            task_count = self.get_task_count()


class CollectionManager:
    """Manage Earth Engine image collections."""

    def __init__(self):
        ee.Initialize()

    def exists(self, path: str) -> bool:
        """Check if collection exists."""
        try:
            return ee.data.getInfo(path) is not None
        except ee.EEException:
            return False

    def create(self, path: str):
        """Create image collection if it doesn't exist."""
        if self.exists(path):
            logger.info(f"Collection already exists: {path}")
            return

        logger.info(f"Creating collection: {path}")
        try:
            ee.data.createAsset({"type": ee.data.ASSET_TYPE_IMAGE_COLL_CLOUD}, path)
        except Exception:
            # Fallback for older EE versions
            ee.data.createAsset({"type": ee.data.ASSET_TYPE_IMAGE_COLL}, path)

    def list_assets(self, path: str) -> Set[str]:
        """List asset names in collection."""
        try:
            assets = ee.data.getList(params={"id": path})
            return {Path(asset["id"]).name for asset in assets}
        except ee.EEException:
            return set()


class BatchUploader:
    """Main batch uploader class."""

    # Valid pyramiding policies
    VALID_PYRAMIDING = ["MEAN", "MODE", "MIN", "MAX", "SAMPLE"]

    def __init__(
        self,
        source_path: Path,
        destination_path: str,
        metadata_path: Optional[Path] = None,
        pyramiding: str = "MEAN",
        nodata_value: Optional[float] = None,
        mask: bool = False,
        overwrite: bool = False,
        dry_run: bool = False,
        workers: int = 1,
        max_inflight_tasks: int = 2800,
        resume: bool = False,
        retry_failed: bool = False,
        show_progress: bool = True,
    ):
        self.source_path = Path(source_path)
        self.destination_path = destination_path
        self.metadata_path = Path(metadata_path) if metadata_path else None

        # Validate and normalize pyramiding policy
        pyramiding_upper = pyramiding.upper()
        if pyramiding_upper not in self.VALID_PYRAMIDING:
            raise ValueError(
                f"Invalid pyramiding policy: {pyramiding}. "
                f"Must be one of: {', '.join(self.VALID_PYRAMIDING)}"
            )
        self.pyramiding = pyramiding_upper

        self.nodata_value = nodata_value
        self.mask = mask
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.workers = workers
        self.max_inflight_tasks = max_inflight_tasks
        self.resume = resume
        self.retry_failed = retry_failed
        self.show_progress = show_progress

        self.state_file = self.source_path / ".geeup-state.json"
        self.metadata_collection = None

        # Initialize managers
        self.task_manager = EETaskManager()
        self.collection_manager = CollectionManager()
        self.session_manager = None if dry_run else SessionManager()

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration before upload."""
        errors = []

        # Validate destination path
        valid, error = PathValidator.validate_path(self.destination_path)
        if not valid:
            errors.append(f"Invalid destination path: {error}")

        # Validate source path
        if not self.source_path.exists():
            errors.append(f"Source path does not exist: {self.source_path}")

        # Find images
        images = list(self.source_path.glob("*.tif"))
        if not images:
            errors.append(f"No .tif images found in: {self.source_path}")

        # Validate and load metadata
        if self.metadata_path:
            if not self.metadata_path.exists():
                errors.append(f"Metadata file not found: {self.metadata_path}")
            else:
                try:
                    # Use MetadataCollection for validation
                    self.metadata_collection = MetadataCollection.from_csv(
                        self.metadata_path
                    )

                    # Check for missing metadata
                    image_names = {img.stem for img in images}
                    missing = self.metadata_collection.validate_all_assets_present(
                        image_names
                    )

                    if missing:
                        errors.append(
                            f"Missing metadata for {len(missing)} images. "
                            f"Examples: {', '.join(list(missing)[:5])}"
                        )

                    # Check for extra metadata (warning only)
                    metadata_names = set(self.metadata_collection.entries.keys())
                    extra = metadata_names - image_names
                    if extra:
                        logger.warning(
                            f"Metadata exists for {len(extra)} images not in source. "
                            f"Examples: {', '.join(list(extra)[:5])}"
                        )

                except Exception as e:
                    errors.append(f"Failed to load metadata: {e}")

        return len(errors) == 0, errors

    def estimate_quota(self) -> dict:
        """Estimate quota impact."""
        images = list(self.source_path.glob("*.tif"))
        total_size = sum(img.stat().st_size for img in images)

        return {
            "total_images": len(images),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_size_gb": round(total_size / 1024 / 1024 / 1024, 2),
        }

    def print_dry_run_summary(self):
        """Print summary for dry run."""
        logger.info("=" * 60)
        logger.info("DRY RUN - No changes will be made")
        logger.info("=" * 60)

        valid, errors = self.validate()

        if not valid:
            logger.error("Validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("✓ Validation passed")
        logger.info("")

        # Get detailed upload information
        images = self._get_images_for_upload()
        all_images = list(self.source_path.glob("*.tif"))

        quota = self.estimate_quota()
        logger.info(f"Total images in source: {quota['total_images']}")
        logger.info(f"Total size: {quota['total_size_gb']:.2f} GB ({quota['total_size_mb']:.2f} MB)")
        logger.info("")

        # Check what already exists
        existing = set()
        tasked = set()
        if self.collection_manager.exists(self.destination_path):
            existing = self.collection_manager.list_assets(self.destination_path)
            tasked = self.task_manager.get_ingestion_tasks(self.destination_path)

        logger.info(f"Images to upload: {len(images)}")
        logger.info(f"Already in collection: {len(existing)}")
        logger.info(f"Currently being ingested: {len(tasked)}")
        logger.info("")

        if images:
            logger.info("Files that will be uploaded:")
            for img in images[:10]:  # Show first 10
                logger.info(f"  • {img.name}")
            if len(images) > 10:
                logger.info(f"  ... and {len(images) - 10} more")
            logger.info("")

        if existing:
            logger.info(f"Files already in collection (will skip): {len(existing)}")
            existing_list = list(existing)[:5]
            for name in existing_list:
                logger.info(f"  • {name}")
            if len(existing) > 5:
                logger.info(f"  ... and {len(existing) - 5} more")
            logger.info("")

        if tasked:
            logger.info(f"Files currently being ingested (will skip): {len(tasked)}")
            tasked_list = list(tasked)[:5]
            for name in tasked_list:
                logger.info(f"  • {name}")
            if len(tasked) > 5:
                logger.info(f"  ... and {len(tasked) - 5} more")
            logger.info("")

        if self.metadata_collection:
            logger.info(f"Metadata entries loaded: {len(self.metadata_collection.entries)}")
            logger.info("")

        logger.info("Configuration:")
        logger.info(f"  Destination: {self.destination_path}")
        logger.info(f"  Pyramiding policy: {self.pyramiding}")
        logger.info(f"  Overwrite mode: {self.overwrite}")
        logger.info(f"  NoData value: {self.nodata_value if self.nodata_value is not None else 'Not set'}")
        logger.info(f"  Mask bands: {self.mask}")
        logger.info(f"  Workers: {self.workers}")
        logger.info(f"  Max inflight tasks: {self.max_inflight_tasks}")

        logger.info("=" * 60)
        return True

    def _get_images_for_upload(self) -> List[Path]:
        """Get list of images that need uploading."""
        all_images = sorted(self.source_path.glob("*.tif"))

        if not self.collection_manager.exists(self.destination_path):
            logger.info(f"Collection does not exist yet, will create: {self.destination_path}")
            return all_images

        if self.overwrite:
            logger.info("Overwrite mode enabled - will re-upload all images")
            return all_images

        # Check existing assets
        existing = self.collection_manager.list_assets(self.destination_path)
        tasked = self.task_manager.get_ingestion_tasks(self.destination_path)

        # Load state for resume
        state = None
        if self.resume or self.retry_failed:
            state = UploadState.load(self.state_file)

        images_to_upload = []
        skipped_existing = []
        skipped_ingesting = []
        skipped_state = []

        for img in all_images:
            name = img.stem

            # Skip if already exists
            if name in existing:
                skipped_existing.append(name)
                logger.debug(f"Skipping {name}: already exists in collection")
                continue

            # Skip if task is running
            if name in tasked:
                skipped_ingesting.append(name)
                logger.debug(f"Skipping {name}: ingestion task already running")
                continue

            # Handle resume/retry
            if state:
                asset_state = state.assets.get(name)
                if self.retry_failed and asset_state == AssetState.FAILED.value:
                    images_to_upload.append(img)
                elif self.resume and asset_state not in [AssetState.SUCCEEDED.value]:
                    images_to_upload.append(img)
                elif not self.resume and not self.retry_failed:
                    images_to_upload.append(img)
                else:
                    skipped_state.append(name)
            else:
                images_to_upload.append(img)

        # Detailed logging
        logger.info(
            f"Found {len(images_to_upload)} images to upload "
            f"(skipped: {len(skipped_existing)} existing, "
            f"{len(skipped_ingesting)} ingesting, "
            f"{len(skipped_state)} by state)"
        )

        # Show which specific files were skipped and why
        if skipped_existing:
            logger.info(f"Skipped {len(skipped_existing)} images already in collection:")
            for name in skipped_existing[:5]:
                logger.info(f"  • {name}")
            if len(skipped_existing) > 5:
                logger.info(f"  ... and {len(skipped_existing) - 5} more")

        if skipped_ingesting:
            logger.info(f"Skipped {len(skipped_ingesting)} images currently being ingested:")
            for name in skipped_ingesting[:5]:
                logger.info(f"  • {name}")
            if len(skipped_ingesting) > 5:
                logger.info(f"  ... and {len(skipped_ingesting) - 5} more")

        return images_to_upload

    def upload(self) -> bool:
        """Execute the upload."""
        # Dry run
        if self.dry_run:
            return self.print_dry_run_summary()

        # Validate (this also loads metadata)
        valid, errors = self.validate()
        if not valid:
            logger.error("Validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        # Load authentication
        if not self.session_manager.load_cookies():
            logger.error("Failed to authenticate")
            return False

        # Create collection
        self.collection_manager.create(self.destination_path)

        # Get images to upload
        images = self._get_images_for_upload()
        if not images:
            logger.info("No images to upload")
            return True

        logger.info(
            f"Starting upload of {len(images)} images with {self.workers} worker(s)"
        )

        # Initialize state
        state = UploadState(
            assets={},
            failed_reasons={},
            timestamp=time.time(),
            collection_path=self.destination_path,
        )

        # Upload with workers
        total = len(images)
        success_count = 0

        try:
            if self.workers == 1:
                # Sequential upload
                for i, image_path in enumerate(images, 1):
                    success = self._upload_single(image_path, state, i, total)
                    if success:
                        success_count += 1
            else:
                # Parallel upload
                with ThreadPoolExecutor(max_workers=self.workers) as executor:
                    futures = {
                        executor.submit(self._upload_single, img, state, i, total): img
                        for i, img in enumerate(images, 1)
                    }

                    for future in as_completed(futures):
                        if future.result():
                            success_count += 1

        except KeyboardInterrupt:
            logger.warning("\n\nUpload interrupted by user (Ctrl+C)")
            logger.info(f"Processed {success_count}/{total} images before interruption")
            logger.info("Upload state has been saved. Use --resume to continue later.")
            state.save(self.state_file)
            sys.exit(130)  # Standard exit code for SIGINT
        except Exception as e:
            logger.error(f"\n\nUpload failed with error: {e}")
            state.save(self.state_file)
            raise

        # Save final state
        state.save(self.state_file)

        logger.info(f"\nUpload complete: {success_count}/{total} successful")
        return success_count == total

    def _upload_single(
        self, image_path: Path, state: UploadState, current: int, total: int
    ) -> bool:
        """Upload a single image."""
        filename = image_path.stem

        try:
            # Wait for capacity
            self.task_manager.wait_for_capacity(self.max_inflight_tasks)

            # Check metadata (if required)
            if self.metadata_collection and not self.metadata_collection.has_metadata(
                filename
            ):
                logger.warning(f"[{current}/{total}] Skipping {filename}: no metadata")
                state.assets[filename] = AssetState.SKIPPED.value
                return False

            # Upload to GCS (gets fresh URL per file)
            gsid = self._upload_to_gcs(image_path, current, total)
            if not gsid:
                raise Exception("Failed to upload to GCS")

            # Get metadata properties (already validated and converted)
            props = {}
            start_time = None
            end_time = None

            if self.metadata_collection:
                gee_props = self.metadata_collection.get(filename)
                if gee_props:
                    props = gee_props.copy()

                    # Extract and convert timestamps (milliseconds -> seconds for API)
                    if "system:time_start" in props:
                        start_time_ms = props.pop("system:time_start")
                        start_time = int(start_time_ms / 1000)

                    if "system:time_end" in props:
                        end_time_ms = props.pop("system:time_end")
                        end_time = int(end_time_ms / 1000)

                    # Remove system:index from properties (not needed in payload)
                    props.pop("system:index", None)

            # Build asset path
            asset_path = f"{self.destination_path}/{filename}"

            # Validate asset path
            valid, error = PathValidator.validate_path(asset_path)
            if not valid:
                raise ValueError(error)

            # Build payload
            payload = {
                "name": asset_path,
                "pyramidingPolicy": self.pyramiding,
                "tilesets": [{"sources": [{"uris": gsid}]}],
                "properties": props,
            }

            if start_time:
                payload["start_time"] = {"seconds": start_time}
            if end_time:
                payload["end_time"] = {"seconds": end_time}
            if self.nodata_value is not None:
                payload["missing_data"] = {"values": [self.nodata_value]}
            if self.mask:
                payload["maskBands"] = {"bandIds": [], "tilesetId": ""}

            # Start ingestion
            request_id = ee.data.newTaskId()[0]
            output = ee.data.startIngestion(
                request_id, payload, allow_overwrite=self.overwrite
            )

            logger.info(
                f"[{current}/{total}] Started {filename} | "
                f"Task: {output['id']} | Status: {output.get('started', 'submitted')}"
            )

            state.assets[filename] = AssetState.RUNNING.value
            state.save(self.state_file)
            return True

        except KeyboardInterrupt:
            # Re-raise to be caught by main upload loop
            logger.info(f"\n[{current}/{total}] Upload of {filename} interrupted")
            state.assets[filename] = AssetState.FAILED.value
            state.failed_reasons[filename] = "Interrupted by user"
            state.save(self.state_file)
            raise
        except Exception as e:
            logger.error(f"[{current}/{total}] Failed {filename}: {e}")
            state.assets[filename] = AssetState.FAILED.value
            state.failed_reasons[filename] = str(e)
            state.save(self.state_file)
            return False

    def _upload_to_gcs(self, file_path: Path, current: int, total: int) -> Optional[str]:
        """
        Upload file to Google Cloud Storage with tqdm progress tracking.
        Gets a fresh upload URL for each file (URLs are single-use).
        """
        # Get fresh URL for this file
        upload_url = self.session_manager.get_upload_url()
        if not upload_url:
            return None

        try:
            with open(file_path, "rb") as f:
                m = MultipartEncoder(fields={"image_file": (file_path.name, f)})

                # Add tqdm progress monitoring
                if self.show_progress:
                    # Create tqdm progress bar
                    with tqdm(
                        total=m.len,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"[{current}/{total}] {file_path.stem}",
                        leave=False,
                        position=0,
                        ncols=100
                    ) as pbar:
                        def callback(monitor):
                            # Update progress bar with bytes read since last update
                            pbar.update(monitor.bytes_read - pbar.n)

                        monitor = MultipartEncoderMonitor(m, callback)

                        response = self.session_manager.session.post(
                            upload_url,
                            data=monitor,
                            headers={"Content-Type": monitor.content_type},
                            timeout=300,
                        )
                else:
                    response = self.session_manager.session.post(
                        upload_url,
                        data=m,
                        headers={"Content-Type": m.content_type},
                        timeout=300,
                    )

                response.raise_for_status()
                return response.json()[0]

        except Exception as e:
            logger.error(f"GCS upload failed for {file_path.name}: {e}")
            return None


def upload(
    user: str,
    source_path: str,
    destination_path: str,
    metadata_path: Optional[str] = None,
    nodata_value: Optional[float] = None,
    mask: bool = False,
    pyramiding: str = "MEAN",
    overwrite: Optional[str] = None,
    dry_run: bool = False,
    workers: int = 1,
    max_inflight_tasks: int = 2800,
    resume: bool = False,
    retry_failed: bool = False,
):
    """
    Upload images to Google Earth Engine.

    Args:
        user: Username (deprecated, kept for compatibility)
        source_path: Path to directory containing .tif files
        destination_path: GEE collection path
        metadata_path: Path to metadata CSV (must contain 'asset_id' or 'system:index' column)
        nodata_value: No data value for images
        mask: Whether to apply mask bands
        pyramiding: Pyramiding policy (MEAN, SAMPLE, MIN, MAX, MODE) - defaults to MEAN
        overwrite: Whether to overwrite existing assets ('yes'/'y')
        dry_run: Run validation without uploading
        workers: Number of parallel workers
        max_inflight_tasks: Maximum concurrent EE tasks
        resume: Resume from previous state
        retry_failed: Retry only failed uploads
    """
    try:
        uploader = BatchUploader(
            source_path=source_path,
            destination_path=destination_path,
            metadata_path=metadata_path,
            pyramiding=pyramiding,  # Will be validated in __init__
            nodata_value=nodata_value,
            mask=mask,
            overwrite=overwrite and overwrite.lower() in ["yes", "y"],
            dry_run=dry_run,
            workers=workers,
            max_inflight_tasks=max_inflight_tasks,
            resume=resume,
            retry_failed=retry_failed,
            show_progress=True,
        )

        success = uploader.upload()
        if not success:
            sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
