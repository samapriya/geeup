"""
Modernized batch table uploader for Google Earth Engine assets.

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
    folder_path: str

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

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize a GEE path to the full format required by the API.

        Examples:
            users/foo/bar -> projects/earthengine-legacy/assets/users/foo/bar
            projects/my-project/assets/foo -> projects/my-project/assets/foo
        """
        # If already in full format, return as-is
        if path.startswith("projects/"):
            return path

        # Convert legacy format to full format
        if path.startswith("users/") or path.startswith("projects/"):
            return f"projects/earthengine-legacy/assets/{path}"

        # If it doesn't start with users/ or projects/, assume it needs the full prefix
        return f"projects/earthengine-legacy/assets/{path}"


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

    def get_ingestion_tasks(self, folder_path: str) -> Set[str]:
        """Get table names with pending/running ingestion tasks."""
        tasks = set()
        for task in ee.data.listOperations():
            metadata = task.get("metadata", {})
            if metadata.get("type") == "INGEST_TABLE" and metadata.get("state") in [
                TaskState.RUNNING.value,
                TaskState.PENDING.value,
            ]:
                desc = metadata.get("description", "")
                # Extract table name from description
                if desc:
                    table_name = desc.split(":")[-1].split("/")[-1].replace('"', "")
                    tasks.add(table_name)
        return tasks

    def wait_for_capacity(self, max_tasks: int = 2500, check_interval: int = 300):
        """Wait until task count is below threshold."""
        task_count = self.get_task_count()
        while task_count >= max_tasks:
            logger.info(
                f"Task limit reached ({task_count}/{max_tasks}). "
                f"Waiting {check_interval}s..."
            )
            time.sleep(check_interval)
            task_count = self.get_task_count()


class FolderManager:
    """Manage Earth Engine folders."""

    def __init__(self):
        ee.Initialize()

    def exists(self, path: str) -> bool:
        """Check if folder exists."""
        try:
            asset_info = ee.data.getAsset(path)
            return (
                asset_info is not None
                and asset_info.get("type", "").lower() == "folder"
            )
        except ee.EEException:
            return False

    def create(self, path: str):
        """Create folder if it doesn't exist."""
        if self.exists(path):
            logger.info(f"Folder already exists: {path}")
            return

        logger.info(f"Creating folder: {path}")
        try:
            ee.data.createAsset({"type": ee.data.ASSET_TYPE_FOLDER_CLOUD}, path)
        except Exception:
            # Fallback for older EE versions
            ee.data.createAsset({"type": ee.data.ASSET_TYPE_FOLDER}, path)

    def list_assets(self, path: str) -> Set[str]:
        """List table names in folder."""
        try:
            # Use the path directly (already normalized)
            result = ee.data.listAssets({"parent": path})
            return {Path(asset["id"]).name for asset in result.get("assets", [])}
        except ee.EEException:
            return set()


class TableType(Enum):
    """Supported table file types."""

    CSV = ".csv"
    ZIP = ".zip"


@dataclass
class TableFile:
    """Represents a table file to upload."""

    path: Path
    name: str  # Without extension
    type: TableType

    @classmethod
    def from_path(cls, path: Path):
        """Create TableFile from path."""
        if path.suffix == ".csv":
            return cls(path, path.stem, TableType.CSV)
        elif path.suffix == ".zip":
            return cls(path, path.stem, TableType.ZIP)
        else:
            return None


class BatchTableUploader:
    """Main batch table uploader class."""

    def __init__(
        self,
        source_path: Path,
        destination_path: str,
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        metadata_path: Optional[Path] = None,
        overwrite: bool = False,
        dry_run: bool = False,
        workers: int = 1,
        max_inflight_tasks: int = 2500,
        resume: bool = False,
        retry_failed: bool = False,
        max_error_meters: float = 1.0,
        max_vertices: int = 1000000,
        show_progress: bool = True,
    ):
        self.source_path = Path(source_path)
        # Normalize the destination path to the full format
        self.destination_path = PathValidator.normalize_path(destination_path)
        self.x_column = x_column
        self.y_column = y_column
        self.metadata_path = Path(metadata_path) if metadata_path else None
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.workers = workers
        self.max_inflight_tasks = max_inflight_tasks
        self.resume = resume
        self.retry_failed = retry_failed
        self.max_error_meters = max_error_meters
        self.max_vertices = max_vertices
        self.show_progress = show_progress

        self.state_file = self.source_path / ".geeup-table-state.json"
        self.metadata_collection = None

        # Initialize managers
        self.task_manager = EETaskManager()
        self.folder_manager = FolderManager()
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

        # Find tables
        tables = self._find_tables()
        if not tables:
            errors.append(f"No .csv or .zip files found in: {self.source_path}")

        # Validate CSV requirements
        if self.x_column and not self.y_column:
            errors.append("x_column specified without y_column")
        if self.y_column and not self.x_column:
            errors.append("y_column specified without x_column")

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
                    table_names = {t.name for t in tables}
                    missing = self.metadata_collection.validate_all_assets_present(
                        table_names
                    )

                    if missing:
                        errors.append(
                            f"Missing metadata for {len(missing)} tables. "
                            f"Examples: {', '.join(list(missing)[:5])}"
                        )

                    # Check for extra metadata (warning only)
                    metadata_names = set(self.metadata_collection.entries.keys())
                    extra = metadata_names - table_names
                    if extra:
                        logger.warning(
                            f"Metadata exists for {len(extra)} tables not in source. "
                            f"Examples: {', '.join(list(extra)[:5])}"
                        )

                except Exception as e:
                    errors.append(f"Failed to load metadata: {e}")

        return len(errors) == 0, errors

    def _find_tables(self) -> List[TableFile]:
        """Find all table files in source directory."""
        tables = []
        for ext in [".csv", ".zip"]:
            for path in self.source_path.glob(f"*{ext}"):
                table = TableFile.from_path(path)
                if table:
                    tables.append(table)
        return sorted(tables, key=lambda t: t.name)

    def estimate_quota(self) -> dict:
        """Estimate quota impact."""
        tables = self._find_tables()
        total_size = sum(t.path.stat().st_size for t in tables)

        csv_count = sum(1 for t in tables if t.type == TableType.CSV)
        zip_count = sum(1 for t in tables if t.type == TableType.ZIP)

        return {
            "total_tables": len(tables),
            "csv_count": csv_count,
            "zip_count": zip_count,
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

        logger.info("Validation passed")

        quota = self.estimate_quota()
        logger.info(f"Total tables: {quota['total_tables']}")
        logger.info(f"  CSV files: {quota['csv_count']}")
        logger.info(f"  ZIP files: {quota['zip_count']}")
        logger.info(f"Total size: {quota['total_size_gb']:.2f} GB")

        tables = self._get_tables_for_upload()
        logger.info(f"Tables to upload: {len(tables)}")

        if self.metadata_collection:
            logger.info(f"Metadata entries: {len(self.metadata_collection.entries)}")

        logger.info(f"Destination: {self.destination_path}")
        logger.info(f"Overwrite mode: {self.overwrite}")
        logger.info(f"Workers: {self.workers}")
        logger.info(f"Max inflight tasks: {self.max_inflight_tasks}")

        if self.x_column and self.y_column:
            logger.info(f"CSV geometry: x={self.x_column}, y={self.y_column}")

        logger.info("=" * 60)
        return True

    def _get_tables_for_upload(self) -> List[TableFile]:
        """Get list of tables that need uploading."""
        all_tables = self._find_tables()

        if not self.folder_manager.exists(self.destination_path):
            return all_tables

        if self.overwrite:
            return all_tables

        # Check existing assets
        existing = self.folder_manager.list_assets(self.destination_path)
        tasked = self.task_manager.get_ingestion_tasks(self.destination_path)

        # Load state for resume
        state = None
        if self.resume or self.retry_failed:
            state = UploadState.load(self.state_file)

        tables_to_upload = []
        for table in all_tables:
            name = table.name

            # Skip if already exists
            if name in existing:
                continue

            # Skip if task is running
            if name in tasked:
                continue

            # Handle resume/retry
            if state:
                asset_state = state.assets.get(name)
                if self.retry_failed and asset_state == AssetState.FAILED.value:
                    tables_to_upload.append(table)
                elif self.resume and asset_state not in [AssetState.SUCCEEDED.value]:
                    tables_to_upload.append(table)
                elif not self.resume and not self.retry_failed:
                    tables_to_upload.append(table)
            else:
                tables_to_upload.append(table)

        logger.info(
            f"Found {len(tables_to_upload)} tables to upload "
            f"({len(existing)} existing, {len(tasked)} tasks running)"
        )

        return tables_to_upload

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

        # Create folder
        self.folder_manager.create(self.destination_path)

        # Get tables to upload
        tables = self._get_tables_for_upload()
        if not tables:
            logger.info("No tables to upload")
            return True

        logger.info(
            f"Starting upload of {len(tables)} tables with {self.workers} worker(s)"
        )

        # Initialize state
        state = UploadState(
            assets={},
            failed_reasons={},
            timestamp=time.time(),
            folder_path=self.destination_path,
        )

        # Upload with workers
        total = len(tables)
        success_count = 0

        if self.workers == 1:
            # Sequential upload
            for i, table in enumerate(tables, 1):
                success = self._upload_single(table, state, i, total)
                if success:
                    success_count += 1
        else:
            # Parallel upload
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {
                    executor.submit(self._upload_single, table, state, i, total): table
                    for i, table in enumerate(tables, 1)
                }

                for future in as_completed(futures):
                    if future.result():
                        success_count += 1

        # Save final state
        state.save(self.state_file)

        logger.info(f"\nUpload complete: {success_count}/{total} successful")
        return success_count == total

    def _upload_single(
        self, table: TableFile, state: UploadState, current: int, total: int
    ) -> bool:
        """Upload a single table."""
        filename = table.name

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

            # Upload to GCS
            gsid = self._upload_to_gcs(table, current, total)
            if not gsid:
                raise Exception("Failed to upload to GCS")

            # Build asset path (already normalized in __init__)
            asset_path = f"{self.destination_path}/{filename}"

            # Validate asset path
            valid, error = PathValidator.validate_path(asset_path)
            if not valid:
                raise ValueError(error)

            # Get metadata properties (already validated and converted)
            props = {}
            if self.metadata_collection:
                gee_props = self.metadata_collection.get(filename)
                if gee_props:
                    props = gee_props.copy()
                    # Remove system:index from properties (not needed in table payload)
                    props.pop("system:index", None)

            # Build payload based on file type
            if table.type == TableType.ZIP:
                payload = {
                    "name": asset_path,
                    "sources": [
                        {
                            "charset": "UTF-8",
                            "maxErrorMeters": self.max_error_meters,
                            "maxVertices": self.max_vertices,
                            "uris": [gsid],
                        }
                    ],
                    "properties": props,
                }
            else:  # CSV
                source = {
                    "charset": "UTF-8",
                    "maxErrorMeters": self.max_error_meters,
                    "uris": [gsid],
                }

                # Add geometry columns if specified
                if self.x_column and self.y_column:
                    source["xColumn"] = self.x_column
                    source["yColumn"] = self.y_column

                payload = {"name": asset_path, "sources": [source], "properties": props}

            # Start ingestion
            request_id = ee.data.newTaskId()[0]
            output = ee.data.startTableIngestion(
                request_id, payload, allow_overwrite=self.overwrite
            )

            logger.info(
                f"[{current}/{total}] Started {filename} | "
                f"Task: {output['id']} | Status: {output.get('started', 'submitted')}"
            )

            state.assets[filename] = AssetState.RUNNING.value
            state.save(self.state_file)
            return True

        except Exception as e:
            logger.error(f"[{current}/{total}] Failed {filename}: {e}")
            state.assets[filename] = AssetState.FAILED.value
            state.failed_reasons[filename] = str(e)
            state.save(self.state_file)
            return False

    def _upload_to_gcs(self, table: TableFile, current: int, total: int) -> Optional[str]:
        """
        Upload table file to Google Cloud Storage with tqdm progress tracking.
        Gets a fresh upload URL for each file (URLs are single-use).
        """
        # Get fresh URL for this file
        upload_url = self.session_manager.get_upload_url()
        if not upload_url:
            return None

        try:
            file_size = table.path.stat().st_size

            with open(table.path, "rb") as f:
                # Use appropriate field name based on file type
                field_name = "zip_file" if table.type == TableType.ZIP else "csv_file"

                m = MultipartEncoder(fields={field_name: (table.path.name, f)})

                # Add tqdm progress monitoring
                if self.show_progress:
                    # Create tqdm progress bar
                    with tqdm(
                        total=m.len,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"[{current}/{total}] {table.name}",
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
            logger.error(f"GCS upload failed for {table.path.name}: {e}")
            return None


def tabup(
    user: str,
    dirc: str,
    destination: str,
    x: Optional[str] = None,
    y: Optional[str] = None,
    metadata: Optional[str] = None,
    overwrite: Optional[str] = None,
    dry_run: bool = False,
    workers: int = 1,
    max_inflight_tasks: int = 2500,
    resume: bool = False,
    retry_failed: bool = False,
    max_error_meters: float = 1.0,
    max_vertices: int = 1000000,
):
    """
    Upload tables to Google Earth Engine.

    Args:
        user: Username (deprecated, kept for compatibility)
        dirc: Path to directory containing .csv or .zip files
        destination: GEE folder path
        x: X column name for CSV geometry (requires y)
        y: Y column name for CSV geometry (requires x)
        metadata: Path to metadata CSV (must contain 'asset_id' or 'system:index' column)
        overwrite: Whether to overwrite existing assets ('yes'/'y')
        dry_run: Run validation without uploading
        workers: Number of parallel workers
        max_inflight_tasks: Maximum concurrent EE tasks
        resume: Resume from previous state
        retry_failed: Retry only failed uploads
        max_error_meters: Maximum allowed error in meters for geometry
        max_vertices: Maximum vertices per geometry feature
    """
    uploader = BatchTableUploader(
        source_path=dirc,
        destination_path=destination,
        x_column=x,
        y_column=y,
        metadata_path=metadata,
        overwrite=overwrite and overwrite.lower() in ["yes", "y"],
        dry_run=dry_run,
        workers=workers,
        max_inflight_tasks=max_inflight_tasks,
        resume=resume,
        retry_failed=retry_failed,
        max_error_meters=max_error_meters,
        max_vertices=max_vertices,
        show_progress=True,
    )

    success = uploader.upload()
    if not success:
        sys.exit(1)
