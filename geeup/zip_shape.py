"""
Shapefile zipping utilities for geeup.
Python 3.10+
"""

import logging
from pathlib import Path
from zipfile import ZipFile

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

logger = logging.getLogger(__name__)
console = Console()

REQUIRED_EXTENSIONS = {".shp", ".shx", ".dbf", ".prj"}


class MissingShapefileComponents(Exception):
    """Raised when a shapefile is missing required sidecar files."""


def zip_shapefiles(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, int]:
    """
    Zip ESRI Shapefiles into individual archives.

    Returns a summary dict.
    """
    input_path = Path(input_dir).expanduser().resolve()
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    shapefiles = list(input_path.rglob("*.shp"))

    if not shapefiles:
        return {
            "created": 0,
            "skipped": 0,
            "failed": 0,
            "total": 0,
        }

    created = skipped = failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Zipping shapefiles...",
            total=len(shapefiles)
        )

        for shp in shapefiles:
            try:
                stem = shp.stem
                components = [
                    shp.parent / f"{stem}{ext}" for ext in REQUIRED_EXTENSIONS
                ]

                if not all(p.exists() for p in components):
                    raise MissingShapefileComponents(stem)

                out_zip = output_path / f"{stem}.zip"
                if out_zip.exists() and not overwrite:
                    skipped += 1
                else:
                    with ZipFile(out_zip, "w") as zf:
                        for p in components:
                            zf.write(p, arcname=p.name)
                    created += 1

            except Exception as e:
                logger.warning("Failed %s: %s", shp.name, e)
                failed += 1
            finally:
                progress.update(task, advance=1)

    return {
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "total": len(shapefiles),
    }
