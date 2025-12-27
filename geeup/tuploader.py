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
# SIMPLIFIED PATH UTILITIES (Same as batch_uploader.py)
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


def ensure_folder_path(
    folder_path: str,
    legacy_roots: List[str]
) -> Tuple[bool, str, Optional[str]]:
    """Ensure folder path is valid and create if needed."""
    normalized_path = normalize_path(folder_path, legacy_roots)
    parts = normalized_path.split('/')

    if len(parts) < 2:
        if create_folder(normalized_path):
            return True, normalized_path, None
        return False, normalized_path, "Failed to create folder"

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

    if create_folder(normalized_path):
        return True, normalized_path, None
    return False, normalized_path, "Failed to create folder"


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

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


# ============================================================================
# MANAGERS
# ============================================================================

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
    """Manage Earth Engine folders with proper path normalization."""
    def __init__(self):
        ee.Initialize()
        self.session, self.project = get_authenticated_session()
        self.legacy_roots = get_legacy_roots(self.session)

        if self.legacy_roots:
            logger.info(f"Found {len(self.legacy_roots)} legacy root(s)")

    def exists(self, path: str) -> bool:
        """Check if folder exists."""
        asset = get_asset_safe(path)
        if not asset:
            return False
        return asset.get('type', '').upper() == 'FOLDER'

    def ensure_folder(self, path: str) -> str:
        """Create folder if needed and return normalized path."""
        success, normalized_path, error = ensure_folder_path(path, self.legacy_roots)
        if not success:
            raise ValueError(error or f"Failed to ensure folder: {path}")
        return normalized_path

    def list_assets(self, path: str) -> Set[str]:
        """List table names in folder."""
        try:
            assets = ee.data.getList(params={"id": path})
            return {Path(asset["id"]).name for asset in assets}
        except ee.EEException:
            return set()


# ============================================================================
# TABLE UPLOADER
# ============================================================================

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
        self.destination_path = destination_path
        self.normalized_destination_path = None
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

        logger.info("✓ Validation passed\n")

        normalized_path = normalize_path(
            self.destination_path,
            self.folder_manager.legacy_roots
        )
        logger.info(f"Normalized destination: {normalized_path}")

        tables = self._get_tables_for_upload(use_normalized=False)
        quota = self.estimate_quota()
        logger.info(f"Total tables: {quota['total_tables']}, Size: {quota['total_size_gb']:.2f} GB\n")

        existing = set()
        tasked = set()
        if self.folder_manager.exists(normalized_path):
            existing = self.folder_manager.list_assets(normalized_path)
            tasked = self.task_manager.get_ingestion_tasks(normalized_path)

        logger.info(f"Tables to upload: {len(tables)}")
        logger.info(f"Already in folder: {len(existing)}")
        logger.info(f"Currently being ingested: {len(tasked)}\n")

        if tables:
            logger.info("Files to upload:")
            for table in tables[:10]:
                logger.info(f"  • {table.name}")
            if len(tables) > 10:
                logger.info(f"  ... and {len(tables) - 10} more\n")

        logger.info("Configuration:")
        logger.info(f"  Max error meters: {self.max_error_meters}")
        logger.info(f"  Max vertices: {self.max_vertices}")
        logger.info(f"  Workers: {self.workers}")
        logger.info("=" * 60)
        return True

    def _get_tables_for_upload(self, use_normalized: bool = True) -> List[TableFile]:
        """Get list of tables that need uploading."""
        all_tables = self._find_tables()

        folder_path = (self.normalized_destination_path
                      if use_normalized and self.normalized_destination_path
                      else self.destination_path)

        if not self.folder_manager.exists(folder_path):
            return all_tables

        if self.overwrite:
            return all_tables

        existing = self.folder_manager.list_assets(folder_path)
        tasked = self.task_manager.get_ingestion_tasks(folder_path)

        state = None
        if self.resume or self.retry_failed:
            state = UploadState.load(self.state_file)

        tables_to_upload = []
        for table in all_tables:
            name = table.name

            if name in existing or name in tasked:
                continue

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

        return tables_to_upload

    def upload(self) -> bool:
        """Execute the upload."""
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
            self.normalized_destination_path = self.folder_manager.ensure_folder(
                self.destination_path
            )
            logger.info(f"Using folder: {self.normalized_destination_path}")
        except ValueError as e:
            logger.error(f"Failed to create folder: {e}")
            return False

        tables = self._get_tables_for_upload(use_normalized=True)
        if not tables:
            logger.info("No tables to upload")
            return True

        logger.info(f"Starting upload of {len(tables)} tables with {self.workers} worker(s)")

        state = UploadState(
            assets={},
            failed_reasons={},
            timestamp=time.time(),
            folder_path=self.normalized_destination_path,
        )

        total = len(tables)
        success_count = 0

        try:
            if self.workers == 1:
                for i, table in enumerate(tables, 1):
                    if self._upload_single(table, state, i, total):
                        success_count += 1
            else:
                with ThreadPoolExecutor(max_workers=self.workers) as executor:
                    futures = {
                        executor.submit(self._upload_single, table, state, i, total): table
                        for i, table in enumerate(tables, 1)
                    }

                    for future in as_completed(futures):
                        if future.result():
                            success_count += 1

        except KeyboardInterrupt:
            logger.warning("\n\nUpload interrupted (Ctrl+C)")
            logger.info(f"Processed {success_count}/{total} tables")
            state.save(self.state_file)
            sys.exit(130)
        except Exception as e:
            logger.error(f"\n\nUpload failed: {e}")
            state.save(self.state_file)
            raise

        state.save(self.state_file)
        logger.info(f"\nUpload complete: {success_count}/{total} successful")
        return success_count == total

    def _upload_single(
        self, table: TableFile, state: UploadState, current: int, total: int
    ) -> bool:
        """Upload a single table."""
        filename = table.name

        try:
            self.task_manager.wait_for_capacity(self.max_inflight_tasks)

            if self.metadata_collection and not self.metadata_collection.has_metadata(
                filename
            ):
                logger.warning(f"[{current}/{total}] Skipping {filename}: no metadata")
                state.assets[filename] = AssetState.SKIPPED.value
                return False

            gsid = self._upload_to_gcs(table, current, total)
            if not gsid:
                raise Exception("Failed to upload to GCS")

            props = {}
            if self.metadata_collection:
                gee_props = self.metadata_collection.get(filename)
                if gee_props:
                    props = gee_props.copy()
                    props.pop("system:index", None)

            asset_path = f"{self.normalized_destination_path}/{filename}"

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

                if self.x_column and self.y_column:
                    source["xColumn"] = self.x_column
                    source["yColumn"] = self.y_column

                payload = {"name": asset_path, "sources": [source], "properties": props}

            request_id = ee.data.newTaskId()[0]
            output = ee.data.startTableIngestion(
                request_id, payload, allow_overwrite=self.overwrite
            )

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

    def _upload_to_gcs(self, table: TableFile, current: int, total: int) -> Optional[str]:
        """Upload table file to Google Cloud Storage with tqdm progress tracking."""
        upload_url = self.session_manager.get_upload_url()
        if not upload_url:
            return None

        try:
            with open(table.path, "rb") as f:
                field_name = "zip_file" if table.type == TableType.ZIP else "csv_file"
                m = MultipartEncoder(fields={field_name: (table.path.name, f)})

                if self.show_progress:
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


# ============================================================================
# PUBLIC API
# ============================================================================

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
    try:
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
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
