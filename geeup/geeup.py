"""Simple CLI for Earth Engine Uploads

SPDX-License-Identifier: Apache-2.0
"""

import argparse
import csv
import importlib.metadata
import json
import logging
import os
import platform
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import ee
import requests
from packaging import version as pkg_version
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Import modularized components
from .auth import initialize_ee
from .batch_uploader import upload
from .quota import fetch_quota_data
from .tasks import fetch_tasks, summarize_tasks
from .tuploader import tabup
from .zip_shape import zip_shapefiles

# Initialize rich console
console = Console()

os.chdir(os.path.dirname(os.path.realpath(__file__)))
lpath = os.path.dirname(os.path.realpath(__file__))
sys.path.append(lpath)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# Initialize Earth Engine if not showing help
if len(sys.argv) > 1 and sys.argv[1] not in ["-h", "--help", "auth"]:
    initialize_ee()


def compare_version(version1: str, version2: str) -> int:
    """Compare two version strings."""
    v1 = pkg_version.parse(version1)
    v2 = pkg_version.parse(version2)
    if v1 > v2:
        return 1
    elif v1 < v2:
        return -1
    return 0


def get_latest_version(package: str) -> Optional[str]:
    """Get the latest version of a package from PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=5)
        response.raise_for_status()
        return response.json()["info"]["version"]
    except (requests.RequestException, KeyError) as e:
        logger.debug(f"Could not fetch latest version for {package}: {e}")
        return None


def get_installed_version(package: str) -> Optional[str]:
    """Get the installed version of a package."""
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def check_version():
    """Check if geeup package needs updating."""
    installed = get_installed_version("geeup")
    latest = get_latest_version("geeup")

    if not installed or not latest:
        return

    result = compare_version(latest, installed)

    if result == 1:
        console.print(
            Panel(
                f"[yellow]Current version:[/yellow] {installed}\n"
                f"[green]Latest version:[/green] {latest}\n\n"
                f"[cyan]Upgrade with:[/cyan] pip install --upgrade geeup",
                title=f"[bold red]Update Available[/bold red]",
                border_style="red",
            )
        )
    elif result == -1:
        console.print(
            Panel(
                f"[yellow]Running staging version {installed}[/yellow]\n"
                f"PyPI release: {latest}",
                title="[bold yellow]Development Version[/bold yellow]",
                border_style="yellow",
            )
        )


# Check version on import
check_version()


def readme():
    """Open the geeup documentation webpage."""
    try:
        opened = webbrowser.open("https://geeup.geetools.xyz/", new=2)
        if not opened:
            console.print("[yellow]Your setup does not have a monitor[/yellow]")
            console.print("[cyan]Visit: https://geeup.geetools.xyz/[/cyan]")
        else:
            console.print("[green]Opening documentation...[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[cyan]Visit: https://geeup.geetools.xyz/[/cyan]")


def rename(directory: str, batch: bool = False):
    """
    Rename files to adhere to EE naming rules with user confirmation.

    Args:
        directory: The path to the directory containing files
        batch: If True, skip confirmation and rename all
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        console.print(f"[red]Error: Directory not found: {directory}[/red]")
        return

    files = [f for f in directory_path.iterdir() if f.is_file()]
    rename_map = []

    # Build rename map
    for file_path in files:
        file_name = file_path.stem
        file_extension = file_path.suffix

        # Remove invalid characters and replace spaces
        cleaned = re.sub(r"[^a-zA-Z0-9 _-]", "", file_name)
        cleaned = re.sub(r"\s+", "_", cleaned)

        if file_name != cleaned:
            rename_map.append((file_path, cleaned + file_extension))

    if not rename_map:
        console.print("[green]✓ No files need renaming[/green]")
        return

    # Display rename preview
    console.print(
        f"\n[bold cyan]Found {len(rename_map)} files to rename:[/bold cyan]\n"
    )

    for old_path, new_name in rename_map:
        console.print(f"  [yellow]{old_path.name}[/yellow] → [green]{new_name}[/green]")

    # Ask for confirmation unless in batch mode
    if not batch:
        console.print()
        response = input("Proceed with renaming? [y/N]: ").lower()
        if response not in ["y", "yes"]:
            console.print("[yellow]Rename cancelled[/yellow]")
            return

    # Perform renaming
    renamed_count = 0
    for old_path, new_name in rename_map:
        try:
            new_path = old_path.parent / new_name
            old_path.rename(new_path)
            renamed_count += 1
        except Exception as e:
            console.print(f"[red]Error renaming {old_path.name}: {e}[/red]")

    console.print(
        f"\n[green]✓ Renamed {renamed_count} of {len(rename_map)} files[/green]"
    )

def auth_setup(cred_path: Optional[str] = None, remove: bool = False, status: bool = False):
    """Manage service account authentication."""
    from .auth import get_sa_credentials_path

    sa_dir, sa_file = get_sa_credentials_path()

    # Show status
    if status:
        if sa_file.exists():
            try:
                with open(sa_file) as f:
                    sa_data = json.load(f)
                    service_account = sa_data.get('client_email', 'Unknown')

                table = Table(show_header=False, box=None)
                table.add_row("[cyan]Status:[/cyan]", "[green]Service account configured[/green]")
                table.add_row("[cyan]Email:[/cyan]", service_account)
                table.add_row("[cyan]Credentials:[/cyan]", str(sa_file))
                console.print(table)
            except Exception as e:
                console.print(f"[red]Error reading credentials: {e}[/red]")
        else:
            console.print("[yellow]No service account configured[/yellow]")
            console.print("[dim]Using default Earth Engine authentication[/dim]")
        return

    # Remove credentials
    if remove:
        if sa_file.exists():
            try:
                sa_file.unlink()
                console.print("[green]✓ Service account credentials removed successfully[/green]")
                console.print("[dim]Will use default Earth Engine authentication[/dim]")
            except Exception as e:
                console.print(f"[red]Error removing credentials: {e}[/red]")
        else:
            console.print("[yellow]No service account credentials found to remove[/yellow]")
        return

    # Store credentials
    if cred_path:
        cred_path_obj = Path(cred_path)

        if not cred_path_obj.exists():
            console.print(f"[red]Error: Credentials file not found: {cred_path}[/red]")
            return

        try:
            # Read and validate the credentials file
            with open(cred_path_obj) as f:
                sa_data = json.load(f)

            # Validate required fields
            if 'client_email' not in sa_data:
                console.print("[red]Error: Invalid service account file - missing 'client_email' field[/red]")
                return

            if 'private_key' not in sa_data:
                console.print("[red]Error: Invalid service account file - missing 'private_key' field[/red]")
                return

            service_account = sa_data['client_email']

            # Create directory if it doesn't exist
            sa_dir.mkdir(parents=True, exist_ok=True)

            # Copy credentials to the standard location
            with open(sa_file, 'w') as f:
                json.dump(sa_data, f, indent=2)

            console.print("[green]✓ Service account credentials stored successfully[/green]")
            console.print(f"[cyan]Service account:[/cyan] {service_account}")
            console.print(f"[cyan]Credentials saved to:[/cyan] {sa_file}")
            console.print("\n[dim]Future geeup commands will use this service account automatically[/dim]")

        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON file[/red]")
        except Exception as e:
            console.print(f"[red]Error storing credentials: {e}[/red]")
    else:
        console.print("[yellow]Please specify a credentials file path with --cred[/yellow]")
        console.print("\n[cyan]Examples:[/cyan]")
        console.print("  geeup auth --cred /path/to/service-account.json")
        console.print("  geeup auth --status")
        console.print("  geeup auth --remove")

def zipshape(directory: str, export: str):
    """
    Create ZIP archives for shapefiles using modular function.

    Args:
        directory: The path to the directory containing shapefiles
        export: The path to the directory where ZIP archives will be created
    """
    try:
        summary = zip_shapefiles(directory, export)

        console.print(f"\n[green]✓ Created {summary['created']} ZIP archives[/green]")
        if summary['skipped']:
            console.print(f"[yellow]• Skipped {summary['skipped']} existing archives[/yellow]")
        if summary['failed']:
            console.print(f"[red]✗ Failed {summary['failed']} archives[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def cookie_setup():
    """Setup cookies for GEE authentication."""
    platform_info = platform.system().lower()

    if platform_info in ("linux", "darwin"):
        try:
            subprocess.check_call(["stty", "-icanon"])
        except subprocess.CalledProcessError:
            logger.warning("Could not set terminal to raw mode")

    cookie_list = input("Enter your Cookie List: ")

    try:
        cookie_data = json.loads(cookie_list)
        with open("cookie_jar.json", "w") as outfile:
            json.dump(cookie_data, outfile, indent=2)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON format - {e}[/red]")
        sys.exit(1)

    time.sleep(2)

    # Clear screen
    if platform_info == "windows":
        os.system("cls")
    elif platform_info in ("linux", "darwin"):
        os.system("clear")
        try:
            subprocess.check_call(["stty", "icanon"])
        except subprocess.CalledProcessError:
            pass

    console.print("[green]✓ Cookie setup completed[/green]")


def humansize(nbytes: int) -> str:
    """Convert bytes to human readable format."""
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = f"{nbytes:.2f}".rstrip("0").rstrip(".")
    return f"{f} {suffixes[i]}"


def quota(project: Optional[str] = None):
    """Display quota information using modular fetch_quota_data."""

    def draw_bar(percent, width=30):
        """Draw a simple progress bar"""
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percent:.1f}%"

    def display_quota_info(project_name, info, project_type="Project"):
        """Display quota info uniformly"""
        if "quota" in info:
            quota_info = info["quota"]

            table = Table(
                title=f"[bold cyan]{project_type}: {project_name}[/bold cyan]",
                show_header=False,
                box=None,
            )

            # Size quota
            used_size = int(quota_info.get("sizeBytes", 0))
            max_size = int(quota_info.get("maxSizeBytes", 1))
            percent = (used_size / max_size * 100) if max_size > 0 else 0

            table.add_row(
                "[cyan]Storage:[/cyan]",
                f"{humansize(used_size)} of {humansize(max_size)}",
            )
            table.add_row("", draw_bar(percent))

            # Asset count quota
            used_assets = int(quota_info.get("assetCount", 0))
            max_assets = int(quota_info.get("maxAssets", 1))
            percent = (used_assets / max_assets * 100) if max_assets > 0 else 0

            table.add_row("[cyan]Assets:[/cyan]", f"{used_assets:,} of {max_assets:,}")
            table.add_row("", draw_bar(percent))

            console.print(table)
            console.print()
        elif "sizeBytes" in info:
            # Direct API response format
            table = Table(
                title=f"[bold cyan]{project_type}: {project_name}[/bold cyan]",
                show_header=False,
                box=None,
            )

            used_size = int(info.get("sizeBytes", 0))
            table.add_row("[cyan]Storage:[/cyan]", humansize(used_size))

            if "featureCount" in info:
                table.add_row("[cyan]Features:[/cyan]", f"{info['featureCount']:,}")
            if "imageCount" in info:
                table.add_row("[cyan]Images:[/cyan]", f"{info['imageCount']:,}")

            console.print(table)
            console.print()
        elif "asset_size" in info:
            # Legacy format
            table = Table(
                title=f"[bold cyan]{project_type}: {project_name}[/bold cyan]",
                show_header=False,
                box=None,
            )

            size_usage = info["asset_size"]["usage"]
            size_limit = info["asset_size"]["limit"]
            size_percent = (size_usage / size_limit * 100) if size_limit > 0 else 0

            count_usage = info["asset_count"]["usage"]
            count_limit = info["asset_count"]["limit"]
            count_percent = (count_usage / count_limit * 100) if count_limit > 0 else 0

            table.add_row(
                "[cyan]Storage:[/cyan]",
                f"{humansize(size_usage)} of {humansize(size_limit)}",
            )
            table.add_row("", draw_bar(size_percent))
            table.add_row("[cyan]Assets:[/cyan]", f"{count_usage:,} of {count_limit:,}")
            table.add_row("", draw_bar(count_percent))

            console.print(table)
            console.print()

    # Fetch quota data using modular function
    with console.status("[bold cyan]Fetching quota information...", spinner="dots"):
        quota_data = fetch_quota_data(project)

    if not quota_data:
        console.print("[yellow]No quota information available.[/yellow]")
        return

    if project is None:
        console.print("[bold cyan]Earth Engine Quota Summary[/bold cyan]\n")

    for project_path, info in quota_data.items():
        project_type = "Legacy Project" if project_path.startswith("users/") else "Cloud Project"
        display_quota_info(project_path, info, project_type)

def getmeta(indir: str, mfile: str):
    """
    Generate minimal, safe raster metadata for GeoTIFFs.

    Produces a CSV compatible with batch_uploader.py using:
    - system:index (asset id)
    - raster dimensions (xsize, ysize)
    - band count (num_bands)
    - data type
    - color interpretation (skipped if "Undefined")
    - inferred semantic kind (skipped if "unknown")
    """
    try:
        from osgeo import gdal
        gdal.UseExceptions()
        # Silence GDAL warnings (like TIFF tag order warnings) to keep the UI clean
        gdal.PushErrorHandler('CPLQuietErrorHandler')
    except Exception:
        os_name = platform.system().lower()
        console.print("[red]Error: GDAL Python bindings are not available.[/red]\n")

        if os_name == "windows":
            console.print("[yellow]Windows installation options:[/yellow]")
            console.print(
                "  • Using pipgeo:\n"
                "    pip install pipgeo && pipgeo fetch --lib gdal\n"
            )
            console.print(
                "  • Or download a prebuilt wheel:\n"
                "    https://github.com/cgohlke/geospatial-wheels/releases\n"
            )
        elif os_name == "darwin":  # macOS
            console.print("[yellow]macOS installation options:[/yellow]")
            console.print(
                "  1. Install GDAL system libraries with Homebrew:\n"
                "     brew install gdal\n"
                "  2. Install Python bindings: pip install gdal\n"
            )
        elif os_name == "linux":
            console.print("[yellow]Linux (Ubuntu/Debian) installation options:[/yellow]")
            console.print(
                "  1. sudo apt install -y libgdal-dev gdal-bin python3-gdal\n"
                "  2. pip install GDAL==$(gdal-config --version)\n"
            )
        else:
            console.print("[yellow]Please install GDAL via your package manager or Conda.[/yellow]")

        sys.exit(1)

    try:
        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------
        def safe(fn):
            """Safely execute a GDAL function and return None on failure."""
            try:
                return fn()
            except Exception:
                return None

        def classify_band(band):
            """Infers the 'kind' of raster based on band properties."""
            dtype = safe(lambda: gdal.GetDataTypeName(band.DataType))
            interp = safe(lambda: gdal.GetColorInterpretationName(band.GetColorInterpretation()))
            has_ct = safe(lambda: band.GetColorTable() is not None)

            if interp in ("Red", "Green", "Blue", "Alpha"):
                return "image"
            if interp == "Palette" or has_ct:
                return "categorical"
            if dtype and dtype.startswith("Float"):
                return "continuous"
            return "unknown"

        # ------------------------------------------------------------------
        # Input validation
        # ------------------------------------------------------------------
        indir_path = Path(indir)
        if not indir_path.exists():
            console.print(f"[red]Error: Directory not found: {indir}[/red]")
            return

        tif_files = sorted(list(indir_path.glob("*.tif")))
        if not tif_files:
            console.print(f"[yellow]Warning: No TIFF files found in {indir}[/yellow]")
            return

        # ------------------------------------------------------------------
        # CSV initialization - only core fields initially
        # ------------------------------------------------------------------
        mfile_path = Path(mfile)

        # Start with base fieldnames
        base_fieldnames = [
            "system:index",
            "xsize",
            "ysize",
            "num_bands",
            "data_type",
        ]

        # We'll determine if we need optional fields after processing first file
        fieldnames = base_fieldnames.copy()
        optional_fields = []

        # ------------------------------------------------------------------
        # Process Rasters
        # ------------------------------------------------------------------
        processed = 0
        rows_to_write = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            task = progress.add_task("[cyan]Extracting raster metadata...", total=len(tif_files))

            for tif_file in tif_files:
                try:
                    ds = gdal.Open(str(tif_file))
                    if ds is None:
                        logger.warning(f"Could not open {tif_file.name}")
                        continue

                    # Get metadata for the first band for types and interpretation
                    band = safe(lambda: ds.GetRasterBand(1))

                    # Build base row
                    row = {
                        "system:index": tif_file.stem,
                        "xsize": ds.RasterXSize,
                        "ysize": ds.RasterYSize,
                        "num_bands": ds.RasterCount,
                        "data_type": safe(lambda: gdal.GetDataTypeName(band.DataType)) if band else "unknown",
                    }

                    # Check optional fields
                    if band:
                        color_interp = safe(lambda: gdal.GetColorInterpretationName(band.GetColorInterpretation()))
                        inferred = classify_band(band)

                        # Only add if not "Undefined" or "unknown"
                        if color_interp and color_interp != "Undefined":
                            row["color_interpretation"] = color_interp
                            if "color_interpretation" not in optional_fields:
                                optional_fields.append("color_interpretation")

                        if inferred and inferred != "unknown":
                            row["inferred_kind"] = inferred
                            if "inferred_kind" not in optional_fields:
                                optional_fields.append("inferred_kind")

                    rows_to_write.append(row)
                    processed += 1
                    ds = None  # Ensure file is closed

                except Exception as e:
                    logger.error(f"Error processing {tif_file.name}: {e}")

                finally:
                    progress.update(task, advance=1)

        # ------------------------------------------------------------------
        # Write CSV with only relevant fields
        # ------------------------------------------------------------------
        if rows_to_write:
            # Finalize fieldnames with optional fields that had valid values
            fieldnames.extend(optional_fields)

            with open(mfile_path, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in rows_to_write:
                    # Only write fields that exist in our final fieldnames
                    filtered_row = {k: v for k, v in row.items() if k in fieldnames}
                    writer.writerow(filtered_row)

        console.print(f"\n[green]✓ Processed {processed} of {len(tif_files)} files[/green]")
        console.print(f"[cyan]Metadata saved to: {mfile_path}[/cyan]")

        if optional_fields:
            console.print(f"[dim]Included optional fields: {', '.join(optional_fields)}[/dim]")
        else:
            console.print(f"[dim]No optional metadata fields were populated (color_interpretation and inferred_kind were undefined)[/dim]")

    finally:
        # Restore normal error handling for the rest of the application
        gdal.PopErrorHandler()


def tasks(state: Optional[str] = None, id: Optional[str] = None):
    """Query Earth Engine task status using modular fetch_tasks."""

    if state is not None or id is not None:
        # Fetch specific tasks
        task_list = fetch_tasks(state=state, task_id=id)
        console.print_json(data=task_list)
    else:
        # Summary of all tasks
        summary = summarize_tasks()

        table = Table(
            title="[bold cyan]Task Summary[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Status", style="cyan", width=20)
        table.add_column("Count", justify="right", style="green")

        table.add_row("Running", str(summary["RUNNING"]))
        table.add_row("Pending", str(summary["READY"]))
        table.add_row("Completed", str(summary["COMPLETED"]))
        table.add_row("Failed", str(summary["FAILED"]))
        table.add_row("Cancelled", str(summary["CANCELLED"]))

        console.print(table)


def cancel_tasks(tasks_arg: str):
    """
    Cancel Earth Engine tasks with progress tracking.

    Args:
        tasks_arg: Can be 'all', 'running', 'pending', or a specific task ID
    """
    try:
        if tasks_arg == "all":
            console.print("[bold yellow]Cancelling all tasks...[/bold yellow]")
            statuses = ee.data.getTaskList()
            cancelled_count = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Cancelling...", total=len(statuses))

                for status in statuses:
                    state = status["state"]
                    task_id = status["id"]

                    if state in ("READY", "RUNNING"):
                        try:
                            ee.data.cancelTask(task_id)
                            cancelled_count += 1
                        except ee.EEException as e:
                            console.print(f"[red]Error cancelling {task_id}: {e}[/red]")
                    progress.update(task, advance=1)

            if cancelled_count > 0:
                console.print(f"[green]✓ Cancelled {cancelled_count} tasks[/green]")
            else:
                console.print("[yellow]No running or pending tasks found[/yellow]")

        elif tasks_arg == "running":
            console.print("[bold yellow]Cancelling running tasks...[/bold yellow]")
            statuses = ee.data.getTaskList()
            running_tasks = [s for s in statuses if s["state"] == "RUNNING"]

            if running_tasks:
                with Progress(console=console) as progress:
                    task = progress.add_task(
                        "[cyan]Cancelling...", total=len(running_tasks)
                    )
                    cancelled_count = 0
                    for status in running_tasks:
                        try:
                            ee.data.cancelTask(status["id"])
                            cancelled_count += 1
                        except ee.EEException as e:
                            console.print(f"[red]Error: {e}[/red]")
                        progress.update(task, advance=1)
                console.print(
                    f"[green]✓ Cancelled {cancelled_count} running tasks[/green]"
                )
            else:
                console.print("[yellow]No running tasks found[/yellow]")

        elif tasks_arg == "pending":
            console.print("[bold yellow]Cancelling pending tasks...[/bold yellow]")
            statuses = ee.data.getTaskList()
            pending_tasks = [s for s in statuses if s["state"] == "READY"]

            if pending_tasks:
                with Progress(console=console) as progress:
                    task = progress.add_task(
                        "[cyan]Cancelling...", total=len(pending_tasks)
                    )
                    cancelled_count = 0
                    for status in pending_tasks:
                        try:
                            ee.data.cancelTask(status["id"])
                            cancelled_count += 1
                        except ee.EEException as e:
                            console.print(f"[red]Error: {e}[/red]")
                        progress.update(task, advance=1)
                console.print(
                    f"[green]✓ Cancelled {cancelled_count} pending tasks[/green]"
                )
            else:
                console.print("[yellow]No pending tasks found[/yellow]")

        else:
            # Assume it's a task ID
            console.print(f"[bold yellow]Cancelling task: {tasks_arg}[/bold yellow]")

            try:
                statuses = ee.data.getTaskStatus([tasks_arg])
                if not statuses:
                    console.print(f"[red]Task {tasks_arg} not found[/red]")
                    return

                status = statuses[0]
                state = status["state"]

                if state == "UNKNOWN":
                    console.print(f"[red]Unknown task ID: {tasks_arg}[/red]")
                elif state in ["READY", "RUNNING"]:
                    ee.data.cancelTask(tasks_arg)
                    console.print(f"[green]✓ Cancelled task {tasks_arg}[/green]")
                else:
                    console.print(
                        f"[yellow]Task {tasks_arg} is in state '{state}' "
                        f"and cannot be cancelled[/yellow]"
                    )
            except ee.EEException as e:
                console.print(f"[red]Error accessing task {tasks_arg}: {e}[/red]")

    except Exception as e:
        console.print(f"[red]Error in cancel_tasks: {e}[/red]")


def delete(ids: str):
    """
    Recursively delete an Earth Engine asset with progress.

    Args:
        ids: Full path to asset for deletion
    """
    try:
        console.print(f"[yellow]Deleting: {ids}[/yellow]")

        with console.status("[cyan]Deleting asset...", spinner="dots"):
            result = subprocess.run(
                ["earthengine", "rm", "-r", ids],
                capture_output=True,
                text=True,
                check=False,
            )

        if result.returncode == 0:
            console.print(f"[green]✓ Deleted {ids}[/green]")
            if result.stdout:
                console.print(f"[dim]{result.stdout.strip()}[/dim]")
        else:
            console.print(f"[red]✗ Failed to delete {ids}[/red]")
            if result.stderr:
                console.print(f"[red]{result.stderr.strip()}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ============================================================================
# ARGUMENT PARSER FUNCTIONS
# ============================================================================


def read_from_parser(args):
    readme()


def rename_from_parser(args):
    rename(directory=args.input, batch=args.batch)


def cookie_setup_from_parser(args):
    cookie_setup()

def auth_from_parser(args):
    auth_setup(cred_path=args.cred, remove=args.remove, status=args.status)

def quota_from_parser(args):
    quota(project=args.project)


def zipshape_from_parser(args):
    zipshape(directory=args.input, export=args.output)


def getmeta_from_parser(args):
    getmeta(indir=args.input, mfile=args.metadata)


def upload_from_parser(args):
    upload(
        user=args.user,
        source_path=args.source,
        destination_path=args.dest,
        metadata_path=args.metadata,
        nodata_value=args.nodata,
        mask=args.mask,
        pyramiding=args.pyramids,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        workers=args.workers,
        max_inflight_tasks=args.max_inflight_tasks,
        resume=args.resume,
        retry_failed=args.retry_failed,
    )


def tabup_from_parser(args):
    tabup(
        user=args.user,
        dirc=args.source,
        destination=args.dest,
        x=args.x,
        y=args.y,
        metadata=args.metadata,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        workers=args.workers,
        max_inflight_tasks=args.max_inflight_tasks,
        resume=args.resume,
        retry_failed=args.retry_failed,
        max_error_meters=args.max_error_meters,
        max_vertices=args.max_vertices,
    )


def tasks_from_parser(args):
    tasks(state=args.state, id=args.id)


def cancel_tasks_from_parser(args):
    cancel_tasks(tasks_arg=args.tasks)


def delete_collection_from_parser(args):
    delete(args.id)


# ============================================================================
# MAIN CLI
# ============================================================================


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Simple Client for Earth Engine Uploads with Enhanced UI and Service Account Support"
    )

    subparsers = parser.add_subparsers()

    # README command
    parser_read = subparsers.add_parser(
        "readme", help="Open the geeup documentation page"
    )
    parser_read.set_defaults(func=read_from_parser)

    # QUOTA command
    parser_quota = subparsers.add_parser(
        "quota",
        help="Print Earth Engine storage and asset count quota with visual progress bars",
    )
    optional_named = parser_quota.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--project",
        help="Project Name usually in format projects/project-name/assets/",
        default=None,
    )
    parser_quota.set_defaults(func=quota_from_parser)

    # AUTH command
    parser_auth = subparsers.add_parser(
    "auth",
    help="Configure service account authentication"
    )
    optional_named = parser_auth.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--cred",
        help="Path to service account JSON credentials file"
    )
    optional_named.add_argument(
        "--remove",
        action="store_true",
        help="Remove stored service account credentials"
    )
    optional_named.add_argument(
        "--status",
        action="store_true",
        help="Show current authentication status"
    )
    parser_auth.set_defaults(func=auth_from_parser)

    # RENAME command
    parser_rename = subparsers.add_parser(
        "rename",
        help="Rename files to adhere to EE naming rules with interactive preview",
    )
    required_named = parser_rename.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--input",
        help="Path to the input directory with all files to be uploaded",
        required=True,
    )
    optional_named = parser_rename.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--batch",
        action="store_true",
        help="Skip confirmation prompt and rename all files",
    )
    parser_rename.set_defaults(func=rename_from_parser)

    # ZIPSHAPE command
    parser_zipshape = subparsers.add_parser(
        "zipshape",
        help="Zip all shapefiles and subsidiary files in folder with progress tracking",
    )
    required_named = parser_zipshape.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--input",
        help="Path to the input directory with all shape files",
        required=True,
    )
    required_named.add_argument(
        "--output",
        help="Destination folder where zipped shapefiles will be stored",
        required=True,
    )
    parser_zipshape.set_defaults(func=zipshape_from_parser)

    # GETMETA command
    parser_getmeta = subparsers.add_parser(
        "getmeta",
        help="Create generalized metadata for rasters in folder with progress tracking",
    )
    required_named = parser_getmeta.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--input",
        help="Path to the input directory with all raster files",
        required=True,
    )
    required_named.add_argument(
        "--metadata", help="Full path to export metadata.csv file", required=True
    )
    parser_getmeta.set_defaults(func=getmeta_from_parser)

    # COOKIE_SETUP command
    parser_cookie_setup = subparsers.add_parser(
        "cookie_setup",
        help="Setup cookies to be used for upload",
    )
    parser_cookie_setup.set_defaults(func=cookie_setup_from_parser)

    # UPLOAD command
    parser_upload = subparsers.add_parser(
        "upload",
        help="Batch Image Uploader for uploading TIF files to a GEE collection",
    )
    required_named = parser_upload.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--source", help="Path to the directory with images for upload", required=True
    )
    required_named.add_argument(
        "--dest",
        help="Destination. Full path for upload to Google Earth Engine image collection, e.g. users/pinkiepie/myponycollection",
        required=True,
    )
    required_named.add_argument(
        "-m", "--metadata", help="Path to CSV with metadata", required=True
    )
    required_named.add_argument(
        "-u", "--user", help="Google account name (gmail address)"
    )
    optional_named = parser_upload.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--nodata",
        type=int,
        help="The value to burn into the raster as NoData (missing data)",
    )
    optional_named.add_argument(
        "--mask",
        default=False,
        choices=("True", "False", "t", "f"),
        help="Binary to use last band for mask True or False",
    )
    optional_named.add_argument(
        "--pyramids",
        default="MEAN",
        help="Pyramiding Policy, MEAN, MODE, MIN, MAX, SAMPLE",
    )
    optional_named.add_argument(
        "--overwrite",
        help="Default is No but you can pass yes or y",
    )
    optional_named.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Run validation without uploading",
    )
    optional_named.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )
    optional_named.add_argument(
        "--max-inflight-tasks",
        type=int,
        default=2800,
        dest="max_inflight_tasks",
        help="Maximum concurrent EE tasks (default: 2800)",
    )
    optional_named.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous state",
    )
    optional_named.add_argument(
        "--retry-failed",
        action="store_true",
        dest="retry_failed",
        help="Retry only failed uploads",
    )
    parser_upload.set_defaults(func=upload_from_parser)

    # TABUP command
    parser_tabup = subparsers.add_parser(
        "tabup",
        help="Batch Table Uploader for uploading shapefiles/CSVs to a GEE folder",
    )
    required_named = parser_tabup.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--source",
        help="Path to the directory with zipped files or CSV files for upload",
        required=True,
    )
    required_named.add_argument(
        "--dest",
        help="Destination. Full path for upload to Google Earth Engine folder, e.g. users/pinkiepie/myfolder",
        required=True,
    )
    required_named.add_argument(
        "-u", "--user", help="Google account name (gmail address)"
    )
    optional_named = parser_tabup.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--x",
        help="Column with longitude value",
    )
    optional_named.add_argument(
        "--y",
        help="Column with latitude value",
    )
    optional_named.add_argument(
        "--metadata",
        help="Path to CSV with metadata",
    )
    optional_named.add_argument(
        "--overwrite",
        help="Default is No but you can pass yes or y",
    )
    optional_named.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Run validation without uploading",
    )
    optional_named.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )
    optional_named.add_argument(
        "--max-inflight-tasks",
        type=int,
        default=2500,
        dest="max_inflight_tasks",
        help="Maximum concurrent EE tasks (default: 2500)",
    )
    optional_named.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous state",
    )
    optional_named.add_argument(
        "--retry-failed",
        action="store_true",
        dest="retry_failed",
        help="Retry only failed uploads",
    )
    optional_named.add_argument(
        "--max-error-meters",
        type=float,
        default=1.0,
        dest="max_error_meters",
        help="Maximum allowed error in meters for geometry (default: 1.0)",
    )
    optional_named.add_argument(
        "--max-vertices",
        type=int,
        default=1000000,
        dest="max_vertices",
        help="Maximum vertices per geometry feature (default: 1000000)",
    )
    parser_tabup.set_defaults(func=tabup_from_parser)

    # TASKS command
    parser_tasks = subparsers.add_parser(
        "tasks",
        help="Query current task status with rich formatting [completed, running, ready, failed, cancelled]",
    )
    optional_named = parser_tasks.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--state",
        help="Query by state type COMPLETED|READY|RUNNING|FAILED|CANCELLED",
    )
    optional_named.add_argument(
        "--id",
        help="Query by task id",
    )
    parser_tasks.set_defaults(func=tasks_from_parser)

    # CANCEL command
    parser_cancel = subparsers.add_parser(
        "cancel",
        help="Cancel all, running, pending tasks or specific task ID with progress tracking",
    )
    required_named = parser_cancel.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--tasks",
        help="Provide 'all', 'running', 'pending', or a specific task ID",
        required=True,
        default=None,
    )
    parser_cancel.set_defaults(func=cancel_tasks_from_parser)

    # DELETE command
    parser_delete = subparsers.add_parser(
        "delete",
        help="Delete collection and all items inside recursively",
    )
    required_named = parser_delete.add_argument_group("Required named arguments")
    required_named.add_argument(
        "--id",
        help="Full path to asset for deletion. Recursively removes all folders, collections and images",
        required=True,
    )
    parser_delete.set_defaults(func=delete_collection_from_parser)

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.error("too few arguments")
    func(args)


if __name__ == "__main__":
    main()
