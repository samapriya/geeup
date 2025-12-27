"""
Modernized batch uploader for Google Earth Engine assets with simplified path handling.

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
from google.auth.transport.requests import AuthorizedSession
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


# ============================================================================
# SIMPLIFIED PATH UTILITIES
# ============================================================================

def get_authenticated_session() -> Tuple[AuthorizedSession, Optional[str]]:
    """Get authenticated session for API calls."""
    try:
        session = AuthorizedSession(ee.data.get_persistent_credentials())
        return session, None
    except Exception as e:
        logger.error(f"Failed to get authenticated session: {e}")
        raise


def get_legacy_roots(session: AuthorizedSession) -> List[str]:
    """Get all legacy root assets."""
    legacy_roots = []
    try:
        url = 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy:listAssets'
        response = session.get(url=url)
        if response.status_code == 200:
            for asset in response.json().get('assets', []):
                legacy_roots.append(asset['id'])
        logger.debug(f"Found {len(legacy_roots)} legacy roots")
    except Exception as e:
        logger.warning(f"Could not retrieve legacy roots: {str(e)}")
    return legacy_roots


def get_asset_safe(asset_path: str) -> Optional[dict]:
    """Safely get asset metadata."""
    try:
        return ee.data.getAsset(asset_path)
    except ee.EEException as e:
        if 'not found' in str(e).lower() or 'does not exist' in str(e).lower():
            return None
        raise
    except Exception:
        return None


def create_folder(folder_path: str) -> bool:
    """Create folder if it doesn't exist."""
    if get_asset_safe(folder_path):
        logger.debug(f"Folder already exists: {folder_path}")
        return True

    try:
        logger.info(f"Creating folder: {folder_path}")
        ee.data.createAsset({"type": "FOLDER"}, folder_path)
        return True
    except Exception:
        try:
            ee.data.createAsset({"type": "Folder"}, folder_path)
            return True
        except Exception as e:
            logger.error(f"Error creating folder {folder_path}: {e}")
            return False


def create_image_collection(collection_path: str) -> bool:
    """Create image collection if it doesn't exist."""
    asset = get_asset_safe(collection_path)
    if asset:
        asset_type = asset.get('type', '').upper()
        if asset_type == 'IMAGE_COLLECTION':
            logger.info(f"Collection already exists: {collection_path}")
            return True
        else:
            logger.error(f"Path exists but is not a collection: {collection_path}")
            return False

    try:
        logger.info(f"Creating collection: {collection_path}")
        ee.data.createAsset({"type": "IMAGE_COLLECTION"}, collection_path)
        return True
    except Exception:
        try:
            ee.data.createAsset({"type": "ImageCollection"}, collection_path)
            return True
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False


def normalize_path(path: str, legacy_roots: List[str]) -> str:
    """Normalize path to canonical form."""
    # If exists, get canonical path
    existing = get_asset_safe(path)
    if existing:
        return existing.get('name', path)

    parts = path.split('/')

    # Legacy user path (users/username/...)
    if parts[0] == 'users':
        for root in legacy_roots:
            if path.startswith(f"users/{parts[1]}"):
                root_asset = get_asset_safe(root)
                if root_asset:
                    canonical_root = root_asset['name']
                    return path.replace(f"users/{parts[1]}", canonical_root)
        return f"projects/earthengine-legacy/assets/{path}"

    # Project paths
    if parts[0] == 'projects' and len(parts) >= 2:
        # If already has /assets/, return as-is
        if '/assets/' in path:
            return path

        project_id = parts[1]
        potential_root = f"projects/{project_id}"

        # Check if this matches a legacy root and get its canonical form
        for root in legacy_roots:
            if root == potential_root or root.startswith(f"{potential_root}/"):
                # Get the canonical name for this legacy root
                root_asset = get_asset_safe(root)
                if root_asset:
                    canonical_root = root_asset['name']
                    # Replace the shorthand with canonical path
                    normalized = path.replace(potential_root, canonical_root)
                    logger.debug(f"Normalized legacy root: {path} -> {normalized}")
                    return normalized

        # Not a legacy root - must be a cloud project, add /assets/
        remaining = '/'.join(parts[2:])
        normalized = f"projects/{project_id}/assets/{remaining}"
        logger.debug(f"Normalized cloud project: {path} -> {normalized}")
        return normalized

    return path


def ensure_collection_path(
    collection_path: str,
    legacy_roots: List[str]
) -> Tuple[bool, str, Optional[str]]:
    """Ensure collection path is valid and create if needed."""
    normalized_path = normalize_path(collection_path, legacy_roots)
    parts = normalized_path.split('/')

    if len(parts) < 2:
        if create_image_collection(normalized_path):
            return True, normalized_path, None
        return False, normalized_path, "Failed to create collection"

    parent_folder = '/'.join(parts[:-1])

    # For cloud projects, the assets folder needs a trailing slash to be found
    # Check if this looks like a cloud project assets folder
    if parent_folder.endswith('/assets'):
        parent_asset = get_asset_safe(parent_folder + '/')
    else:
        parent_asset = get_asset_safe(parent_folder)

    if not parent_asset:
        # Find the root - check if parent matches a legacy root first
        root = None

        # Check if parent IS a legacy root
        for legacy_root in legacy_roots:
            if parent_folder == legacy_root or parent_folder.startswith(f"{legacy_root}/"):
                root = legacy_root
                break

        # If not found in legacy roots, try to find it by structure
        if not root:
            if 'assets' in parts:
                assets_idx = parts.index('assets')
                # For cloud projects, root is projects/project-id/assets/
                # Note: trailing slash is required for getAsset() to work
                root = '/'.join(parts[:assets_idx + 1]) + '/'
            else:
                # For paths like projects/sat-io/something, root is projects/sat-io
                root = '/'.join(parts[:2]) if len(parts) >= 2 else parent_folder

        root_asset = get_asset_safe(root)
        if not root_asset:
            return False, normalized_path, (
                f"Root does not exist or is not accessible: {root}\n"
                f"Please verify you have access to this project."
            )

        # Check nesting depth from root
        root_canonical = root_asset['name'].rstrip('/')
        parent_folder_clean = parent_folder.rstrip('/')

        if parent_folder_clean.startswith(root_canonical + '/'):
            remaining = parent_folder_clean.replace(root_canonical + '/', '')
            remaining_parts = remaining.split('/') if remaining else []
        elif parent_folder_clean == root_canonical:
            # Parent folder IS the root, no nesting
            remaining_parts = []
        else:
            # Fallback for edge cases
            remaining_parts = parent_folder_clean.replace(root.rstrip('/') + '/', '').split('/')
            remaining_parts = [p for p in remaining_parts if p]  # Filter empty strings

        if len(remaining_parts) > 1:
            return False, normalized_path, (
                f"Parent folder is nested too deep: {parent_folder}\n"
                f"Can only auto-create one level. Please create intermediate folders first."
            )

        # Prompt to create parent
        response = input(
            f"\nParent folder does not exist: {parent_folder}\n"
            f"Create it? [y/N]: "
        ).strip().lower()

        if response not in ['y', 'yes']:
            return False, normalized_path, "Parent folder creation declined"

        if not create_folder(parent_folder):
            return False, normalized_path, f"Failed to create parent: {parent_folder}"

    if create_image_collection(normalized_path):
        return True, normalized_path, None
    return False, normalized_path, "Failed to create collection"


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class AssetState(Enum):
    """Asset upload states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskState(Enum):
    """EE task states."""
    RUNNING = "RUNNING"
    PENDING = "PENDING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class UploadState:
    """Track upload progress."""
    assets: Dict[str, str]
    failed_reasons: Dict[str, str]
    timestamp: float
    collection_path: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def save(self, state_file: Path):
        with open(state_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, state_file: Path):
        if not state_file.exists():
            return None
        with open(state_file, "r") as f:
            return cls.from_dict(json.load(f))


# ============================================================================
# MANAGERS
# ============================================================================

class SessionManager:
    """Manage Google auth sessions."""
    COOKIE_FILE = Path("cookie_jar.json")

    def __init__(self):
        self.session = self._create_session_with_retry()
        self._url_lock = __import__("threading").Lock()

    def _create_session_with_retry(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def load_cookies(self) -> bool:
        if not self.COOKIE_FILE.exists():
            return self._prompt_for_cookies()

        with open(self.COOKIE_FILE) as f:
            cookie_list = json.load(f)

        if self._validate_cookies(cookie_list):
            logger.info("Using saved cookies")
            self._set_cookies(cookie_list)
            return True
        else:
            logger.warning("Saved cookies expired")
            return self._prompt_for_cookies()

    def _validate_cookies(self, cookie_list: list) -> bool:
        test_session = requests.Session()
        for cookie in cookie_list:
            test_session.cookies.set(cookie["name"], cookie["value"])

        try:
            response = test_session.get(
                "https://code.earthengine.google.com/assets/upload/geturl",
                timeout=10
            )
            return (response.status_code == 200 and
                    "application/json" in response.headers.get("content-type", ""))
        except requests.RequestException:
            return False

    def _prompt_for_cookies(self) -> bool:
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
        for cookie in cookie_list:
            self.session.cookies.set(cookie["name"], cookie["value"])

    @staticmethod
    def _clear_screen():
        os.system("cls" if os.name == "nt" else "clear")
        if sys.platform in ["linux", "darwin"]:
            subprocess.run(["stty", "icanon"], check=False)

    def get_upload_url(self) -> Optional[str]:
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
    """Manage EE tasks."""
    def __init__(self):
        ee.Initialize()

    def get_task_count(self, states: Optional[List[TaskState]] = None) -> int:
        if states is None:
            states = [TaskState.RUNNING, TaskState.PENDING]

        state_names = [s.value for s in states]
        operations = ee.data.listOperations()

        return sum(
            1 for task in operations
            if task.get("metadata", {}).get("state") in state_names
        )

    def get_ingestion_tasks(self, collection_path: str) -> Set[str]:
        tasks = set()
        for task in ee.data.listOperations():
            metadata = task.get("metadata", {})
            if (metadata.get("type") == "INGEST_IMAGE" and
                metadata.get("state") in [TaskState.RUNNING.value, TaskState.PENDING.value]):
                desc = metadata.get("description", "")
                if desc:
                    asset_name = desc.split(":")[-1].split("/")[-1].replace('"', "")
                    tasks.add(asset_name)
        return tasks

    def wait_for_capacity(self, max_tasks: int = 2800, check_interval: int = 300):
        task_count = self.get_task_count()
        while task_count >= max_tasks:
            logger.info(f"Task limit reached ({task_count}/{max_tasks}). Waiting {check_interval}s...")
            time.sleep(check_interval)
            task_count = self.get_task_count()


class CollectionManager:
    """Manage EE collections with simplified paths."""
    def __init__(self):
        ee.Initialize()
        self.session, self.project = get_authenticated_session()
        self.legacy_roots = get_legacy_roots(self.session)

        if self.legacy_roots:
            logger.info(f"Found {len(self.legacy_roots)} legacy root(s)")

    def exists(self, path: str) -> bool:
        asset = get_asset_safe(path)
        if not asset:
            return False
        return asset.get('type', '').upper() == 'IMAGE_COLLECTION'

    def ensure_collection(self, path: str) -> str:
        success, normalized_path, error = ensure_collection_path(path, self.legacy_roots)
        if not success:
            raise ValueError(error or f"Failed to ensure collection: {path}")
        return normalized_path

    def list_assets(self, path: str) -> Set[str]:
        try:
            assets = ee.data.getList(params={"id": path})
            return {Path(asset["id"]).name for asset in assets}
        except ee.EEException:
            return set()


# ============================================================================
# BATCH UPLOADER
# ============================================================================

class BatchUploader:
    """Main batch uploader with simplified path handling."""
    VALID_PYRAMIDING = ["MEAN", "MODE", "MIN", "MAX", "SAMPLE"]

    def __init__(self, source_path: Path, destination_path: str,
                 metadata_path: Optional[Path] = None, pyramiding: str = "MEAN",
                 nodata_value: Optional[float] = None, mask: bool = False,
                 overwrite: bool = False, dry_run: bool = False,
                 workers: int = 1, max_inflight_tasks: int = 2800,
                 resume: bool = False, retry_failed: bool = False,
                 show_progress: bool = True):

        self.source_path = Path(source_path)
        self.destination_path = destination_path
        self.normalized_destination_path = None
        self.metadata_path = Path(metadata_path) if metadata_path else None

        pyramiding_upper = pyramiding.upper()
        if pyramiding_upper not in self.VALID_PYRAMIDING:
            raise ValueError(
                f"Invalid pyramiding: {pyramiding}. "
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

        self.task_manager = EETaskManager()
        self.collection_manager = CollectionManager()
        self.session_manager = None if dry_run else SessionManager()

    def validate(self) -> Tuple[bool, List[str]]:
        errors = []

        if not self.source_path.exists():
            errors.append(f"Source path does not exist: {self.source_path}")

        images = list(self.source_path.glob("*.tif"))
        if not images:
            errors.append(f"No .tif images found in: {self.source_path}")

        if self.metadata_path:
            if not self.metadata_path.exists():
                errors.append(f"Metadata file not found: {self.metadata_path}")
            else:
                try:
                    self.metadata_collection = MetadataCollection.from_csv(self.metadata_path)

                    image_names = {img.stem for img in images}
                    missing = self.metadata_collection.validate_all_assets_present(image_names)

                    if missing:
                        errors.append(
                            f"Missing metadata for {len(missing)} images. "
                            f"Examples: {', '.join(list(missing)[:5])}"
                        )

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

    def print_dry_run_summary(self):
        logger.info("=" * 60)
        logger.info("DRY RUN - No changes will be made")
        logger.info("=" * 60)

        valid, errors = self.validate()

        if not valid:
            logger.error("Validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("✓ Validation passed\n")

        normalized_path = normalize_path(
            self.destination_path,
            self.collection_manager.legacy_roots
        )
        logger.info(f"Normalized destination: {normalized_path}")

        images = self._get_images_for_upload(use_normalized=False)
        quota = {
            "total_images": len(list(self.source_path.glob("*.tif"))),
            "total_size_gb": sum(img.stat().st_size for img in self.source_path.glob("*.tif")) / 1024**3
        }
        logger.info(f"Total images: {quota['total_images']}, Size: {quota['total_size_gb']:.2f} GB\n")

        existing = set()
        tasked = set()
        if self.collection_manager.exists(normalized_path):
            existing = self.collection_manager.list_assets(normalized_path)
            tasked = self.task_manager.get_ingestion_tasks(normalized_path)

        logger.info(f"Images to upload: {len(images)}")
        logger.info(f"Already in collection: {len(existing)}")
        logger.info(f"Currently being ingested: {len(tasked)}\n")

        if images:
            logger.info("Files to upload:")
            for img in images[:10]:
                logger.info(f"  • {img.name}")
            if len(images) > 10:
                logger.info(f"  ... and {len(images) - 10} more\n")

        logger.info("Configuration:")
        logger.info(f"  Pyramiding: {self.pyramiding}")
        logger.info(f"  NoData: {self.nodata_value if self.nodata_value is not None else 'Not set'}")
        logger.info(f"  Workers: {self.workers}")
        logger.info("=" * 60)
        return True

    def _get_images_for_upload(self, use_normalized: bool = True) -> List[Path]:
        all_images = sorted(self.source_path.glob("*.tif"))

        collection_path = (self.normalized_destination_path
                          if use_normalized and self.normalized_destination_path
                          else self.destination_path)

        if not self.collection_manager.exists(collection_path):
            return all_images

        if self.overwrite:
            return all_images

        existing = self.collection_manager.list_assets(collection_path)
        tasked = self.task_manager.get_ingestion_tasks(collection_path)

        state = None
        if self.resume or self.retry_failed:
            state = UploadState.load(self.state_file)

        images_to_upload = []
        for img in all_images:
            name = img.stem

            if name in existing or name in tasked:
                continue

            if state:
                asset_state = state.assets.get(name)
                if self.retry_failed and asset_state == AssetState.FAILED.value:
                    images_to_upload.append(img)
                elif self.resume and asset_state not in [AssetState.SUCCEEDED.value]:
                    images_to_upload.append(img)
                elif not self.resume and not self.retry_failed:
                    images_to_upload.append(img)
            else:
                images_to_upload.append(img)

        return images_to_upload

    def upload(self) -> bool:
        if self.dry_run:
            return self.print_dry_run_summary()

        valid, errors = self.validate()
        if not valid:
            logger.error("Validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        if not self.session_manager.load_cookies():
            logger.error("Failed to authenticate")
            return False

        try:
            self.normalized_destination_path = self.collection_manager.ensure_collection(
                self.destination_path
            )
            logger.info(f"Using collection: {self.normalized_destination_path}")
        except ValueError as e:
            logger.error(f"Failed to create collection: {e}")
            return False

        images = self._get_images_for_upload(use_normalized=True)
        if not images:
            logger.info("No images to upload")
            return True

        logger.info(f"Starting upload of {len(images)} images with {self.workers} worker(s)")

        state = UploadState(
            assets={},
            failed_reasons={},
            timestamp=time.time(),
            collection_path=self.normalized_destination_path,
        )

        total = len(images)
        success_count = 0

        try:
            if self.workers == 1:
                for i, image_path in enumerate(images, 1):
                    if self._upload_single(image_path, state, i, total):
                        success_count += 1
            else:
                with ThreadPoolExecutor(max_workers=self.workers) as executor:
                    futures = {
                        executor.submit(self._upload_single, img, state, i, total): img
                        for i, img in enumerate(images, 1)
                    }

                    for future in as_completed(futures):
                        if future.result():
                            success_count += 1

        except KeyboardInterrupt:
            logger.warning("\n\nUpload interrupted (Ctrl+C)")
            logger.info(f"Processed {success_count}/{total} images")
            state.save(self.state_file)
            sys.exit(130)
        except Exception as e:
            logger.error(f"\n\nUpload failed: {e}")
            state.save(self.state_file)
            raise

        state.save(self.state_file)
        logger.info(f"\nUpload complete: {success_count}/{total} successful")
        return success_count == total

    def _upload_single(self, image_path: Path, state: UploadState,
                      current: int, total: int) -> bool:
        filename = image_path.stem

        try:
            self.task_manager.wait_for_capacity(self.max_inflight_tasks)

            if self.metadata_collection and not self.metadata_collection.has_metadata(filename):
                logger.warning(f"[{current}/{total}] Skipping {filename}: no metadata")
                state.assets[filename] = AssetState.SKIPPED.value
                return False

            gsid = self._upload_to_gcs(image_path, current, total)
            if not gsid:
                raise Exception("Failed to upload to GCS")

            props = {}
            start_time = None
            end_time = None

            if self.metadata_collection:
                gee_props = self.metadata_collection.get(filename)
                if gee_props:
                    props = gee_props.copy()

                    if "system:time_start" in props:
                        start_time_ms = props.pop("system:time_start")
                        start_time = int(start_time_ms / 1000)

                    if "system:time_end" in props:
                        end_time_ms = props.pop("system:time_end")
                        end_time = int(end_time_ms / 1000)

                    props.pop("system:index", None)

            asset_path = f"{self.normalized_destination_path}/{filename}"

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

            request_id = ee.data.newTaskId()[0]
            output = ee.data.startIngestion(request_id, payload, allow_overwrite=self.overwrite)

            logger.info(
                f"[{current}/{total}] Started {filename} | "
                f"Task: {output['id']}"
            )

            state.assets[filename] = AssetState.RUNNING.value
            state.save(self.state_file)
            return True

        except KeyboardInterrupt:
            logger.info(f"\n[{current}/{total}] Upload of {filename} interrupted")
            state.assets[filename] = AssetState.FAILED.value
            state.failed_reasons[filename] = "Interrupted"
            state.save(self.state_file)
            raise
        except Exception as e:
            logger.error(f"[{current}/{total}] Failed {filename}: {e}")
            state.assets[filename] = AssetState.FAILED.value
            state.failed_reasons[filename] = str(e)
            state.save(self.state_file)
            return False

    def _upload_to_gcs(self, file_path: Path, current: int, total: int) -> Optional[str]:
        upload_url = self.session_manager.get_upload_url()
        if not upload_url:
            return None

        try:
            with open(file_path, "rb") as f:
                m = MultipartEncoder(fields={"image_file": (file_path.name, f)})

                if self.show_progress:
                    with tqdm(
                        total=m.len, unit='B', unit_scale=True, unit_divisor=1024,
                        desc=f"[{current}/{total}] {file_path.stem}",
                        leave=False, position=0, ncols=100
                    ) as pbar:
                        def callback(monitor):
                            pbar.update(monitor.bytes_read - pbar.n)

                        monitor = MultipartEncoderMonitor(m, callback)
                        response = self.session_manager.session.post(
                            upload_url, data=monitor,
                            headers={"Content-Type": monitor.content_type},
                            timeout=300,
                        )
                else:
                    response = self.session_manager.session.post(
                        upload_url, data=m,
                        headers={"Content-Type": m.content_type},
                        timeout=300,
                    )

                response.raise_for_status()
                return response.json()[0]

        except Exception as e:
            logger.error(f"GCS upload failed for {file_path.name}: {e}")
            return None


# ============================================================================
# PUBLIC API
# ============================================================================

def upload(user: str, source_path: str, destination_path: str,
           metadata_path: Optional[str] = None, nodata_value: Optional[float] = None,
           mask: bool = False, pyramiding: str = "MEAN",
           overwrite: Optional[str] = None, dry_run: bool = False,
           workers: int = 1, max_inflight_tasks: int = 2800,
           resume: bool = False, retry_failed: bool = False):
    """
    Upload images to Google Earth Engine.

    Args:
        user: Username (deprecated, kept for compatibility)
        source_path: Path to directory containing .tif files
        destination_path: GEE collection path (e.g., users/username/collection)
        metadata_path: Path to metadata CSV
        nodata_value: No data value for images
        mask: Whether to apply mask bands
        pyramiding: Pyramiding policy (MEAN, SAMPLE, MIN, MAX, MODE)
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
            pyramiding=pyramiding,
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
