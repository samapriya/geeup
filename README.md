# [geeup: Simple CLI for Earth Engine Uploads](https://geeup.geetools.xyz)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=plastic&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/samapriya/)
[![Medium](https://img.shields.io/badge/Medium-12100E?style=flat&logo=medium&logoColor=white)](https://medium.com/@samapriyaroy)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8385048.svg)](https://doi.org/10.5281/zenodo.8385048)
[![PyPI version](https://badge.fury.io/py/geeup.svg)](https://badge.fury.io/py/geeup)
[![Downloads](https://static.pepy.tech/badge/geeup)](https://pepy.tech/project/geeup)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![CI geeup](https://github.com/samapriya/geeup/workflows/CI%20geeup/badge.svg)
[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/samapriya)

**geeup** is a comprehensive command-line tool designed to simplify data preparation and batch uploading to Google Earth Engine. Handle images, shapefiles, and metadata with retry logic, parallel processing, and enhanced path normalization.

## Citation

If you use this project, please star and cite it as below:

```
Samapriya Roy. (2023). samapriya/geeup: geeup: Simple CLI for Earth Engine Uploads (1.0.0).
Zenodo. https://doi.org/10.5281/zenodo.8385048
```

## Table of Contents

- [geeup: Simple CLI for Earth Engine Uploads](#geeup-simple-cli-for-earth-engine-uploads)
  - [Citation](#citation)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [Method 1: PyPI (Recommended)](#method-1-pypi-recommended)
    - [Method 2: From Source](#method-2-from-source)
  - [Getting Started](#getting-started)
  - [Authentication](#authentication)
    - [Cookie Setup](#cookie-setup)
    - [Service Account Configuration](#service-account-configuration)
  - [Data Preparation](#data-preparation)
    - [Rename Files](#rename-files)
    - [Zip Shapefiles](#zip-shapefiles)
    - [Generate Metadata](#generate-metadata)
  - [Batch Upload](#batch-upload)
    - [Upload Images](#upload-images)
    - [Upload Tables (Tabup)](#upload-tables-tabup)
  - [Monitoring](#monitoring)
    - [Check Quota](#check-quota)
    - [Task Status](#task-status)
    - [Cancel Tasks](#cancel-tasks)
  - [Utilities](#utilities)
    - [Delete Assets](#delete-assets)
    - [Open Documentation](#open-documentation)
  - [Full Documentation](#full-documentation)
  - [Changelog](#changelog)
    - [Version 2.0.0](#version-200)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Installation

### Method 1: PyPI (Recommended)

```bash
pip install geeup
```

### Method 2: From Source

```bash
git clone https://github.com/samapriya/geeup.git
cd geeup
pip install -e .
```

**Requirements:**
- Python 3.7+
- Earth Engine Python API
- Authenticated Earth Engine account (`earthengine authenticate`)

## Getting Started

View all available commands:

```bash
geeup -h
```

Main interface output:

```
usage: geeup [-h] {readme,quota,auth,rename,zipshape,getmeta,cookie_setup,upload,tabup,tasks,cancel,delete} ...

Simple Client for Earth Engine Uploads with Enhanced UI and Service Account Support

positional arguments:
  {readme,quota,auth,rename,zipshape,getmeta,cookie_setup,upload,tabup,tasks,cancel,delete}
    readme              Open the geeup documentation page
    quota               Print Earth Engine storage and asset count quota with visual progress bars
    auth                Configure service account authentication
    rename              Rename files to adhere to EE naming rules with interactive preview
    zipshape            Zip all shapefiles and subsidiary files in folder with progress tracking
    getmeta             Create generalized metadata for rasters in folder with progress tracking
    cookie_setup        Setup cookies to be used for upload
    upload              Batch Image Uploader for uploading TIF files to a GEE collection
    tabup               Batch Table Uploader for uploading shapefiles/CSVs to a GEE folder
    tasks               Query current task status with rich formatting [completed, running, ready, failed, cancelled]
    cancel              Cancel all, running, pending tasks or specific task ID with progress tracking
    delete              Delete collection and all items inside recursively
```

## Authentication

### Cookie Setup

The `cookie_setup` command configures authentication cookies required for uploads. This uses the [Copy Cookies Chrome extension](https://chrome.google.com/webstore/detail/copy-cookies/jcbpglbplpblnagieibnemmkiamekcdg/related).

**Setup Steps:**

1. Install the Copy Cookies extension in Chrome
2. Log into [code.earthengine.google.com](https://code.earthengine.google.com)
3. Click the extension icon to copy cookies
4. Run the setup command and paste when prompted:

```bash
geeup cookie_setup
```

**Important Notes:**
- Use a fresh browser window (not incognito)
- Clear cookies and retry if you get "Unable to read" errors
- Ensure cookies match the account initialized with `earthengine authenticate`

**Platform-Specific Instructions:**

For Bash users experiencing paste limitations:
```bash
stty -icanon
geeup cookie_setup
stty icanon
```

For Mac users, you may need to change your default shell from `/bin/zsh` to `/bin/sh`.

### Service Account Configuration

The `auth` command manages service account authentication for automated workflows.

**Initialize with service account:**
```bash
geeup auth --cred "/path/to/service-account.json"
```

**Check authentication status:**
```bash
geeup auth --status
```

**Remove credentials:**
```bash
geeup auth --remove
```

**Arguments:**
- `--cred`: Path to service account JSON credentials file (optional)
- `--status`: Show current authentication status (optional)
- `--remove`: Remove stored service account credentials (optional)

## Data Preparation

### Rename Files

Sanitize filenames to adhere to Earth Engine naming conventions. Removes spaces and special characters.

```bash
geeup rename --input "./raw_data" --batch
```

**Arguments:**
- `--input`: Path to directory with files to rename (required)
- `--batch`: Skip confirmation and rename all files automatically (optional)

**Interactive Mode:**
By default, shows a preview of changes and asks for confirmation before renaming.

### Zip Shapefiles

Package shapefile components (.shp, .shx, .dbf, .prj) into individual ZIP archives for upload.

```bash
geeup zipshape --input "./vectors" --output "./zipped_vectors"
```

**Arguments:**
- `--input`: Path to directory containing raw shapefiles (required)
- `--output`: Destination folder for ZIP archives (required)

### Generate Metadata

Create a metadata CSV file for rasters, defining properties like image IDs, dimensions, and data types.

```bash
geeup getmeta --input "./rasters" --metadata "./metadata.csv"
```

**Arguments:**
- `--input`: Path to directory containing raster (TIF) files (required)
- `--metadata`: Full path for exported metadata CSV file (required)

**Generated Fields:**
- `system:index`: Asset ID (filename without extension)
- `xsize`, `ysize`: Raster dimensions
- `num_bands`: Number of bands
- `data_type`: Data type (e.g., Byte, Float32)
- `color_interpretation`: Color interpretation (if not "Undefined")
- `inferred_kind`: Inferred semantic type (image, categorical, continuous)

## Batch Upload

### Upload Images

Batch upload GeoTIFF files to an Earth Engine Image Collection with advanced features like retry logic and parallel processing.

**Basic Usage:**
```bash
geeup upload \
  --source "./rasters" \
  --dest "users/username/collection" \
  --metadata "./metadata.csv" \
  --user "email@gmail.com"
```

**Advanced Usage with Parallel Workers:**
```bash
geeup upload \
  --source "./rasters" \
  --dest "users/username/collection" \
  --metadata "./metadata.csv" \
  --user "email@gmail.com" \
  --workers 4 \
  --resume \
  --pyramids MEAN \
  --nodata -9999
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `--source` | Required | Path to directory with images for upload |
| `--dest` | Required | Destination path for GEE Image Collection (e.g., `users/you/collection`) |
| `--metadata`, `-m` | Required | Path to metadata CSV file |
| `--user`, `-u` | Required | Google account email address |
| `--nodata` | Optional | Integer value to burn as NoData (missing data) |
| `--mask` | Optional | Boolean (True/False). Use last band as validity mask |
| `--pyramids` | Optional | Pyramiding policy: MEAN, MODE, MIN, MAX, SAMPLE (default: MEAN) |
| `--overwrite` | Optional | Overwrite existing assets (pass 'yes' or 'y') |
| `--dry-run` | Optional | Run validation without uploading |
| `--workers` | Optional | Number of parallel upload workers (default: 1) |
| `--max-inflight-tasks` | Optional | Maximum concurrent EE tasks (default: 2800) |
| `--resume` | Optional | Resume from previous state |
| `--retry-failed` | Optional | Retry only failed uploads |

**Features:**
- **Path Normalization**: Automatic handling of legacy (`users/`) and cloud project paths
- **Collection Auto-Creation**: Prompts to create missing collections and parent folders
- **State Persistence**: Saves progress to `.geeup-state.json` for resumption
- **Parallel Uploads**: Multi-threaded GCS uploads with progress bars
- **Task Throttling**: Automatically waits when task limit is reached

### Upload Tables (Tabup)

Batch upload table data (vectors) from zipped shapefiles or CSVs to a GEE folder.

**Basic Usage:**
```bash
geeup tabup \
  --source "./zipped_vectors" \
  --dest "users/username/folder" \
  --user "email@gmail.com"
```

**CSV with Geometry Columns:**
```bash
geeup tabup \
  --source "./csv_files" \
  --dest "users/username/folder" \
  --user "email@gmail.com" \
  --x "longitude" \
  --y "latitude"
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `--source` | Required | Path to directory with zipped files or CSV files |
| `--dest` | Required | Destination path for GEE Folder (e.g., `users/you/folder`) |
| `--user`, `-u` | Required | Google account email address |
| `--x` | Optional | Column name containing longitude values (for CSVs) |
| `--y` | Optional | Column name containing latitude values (for CSVs) |
| `--metadata` | Optional | Path to CSV with metadata |
| `--overwrite` | Optional | Overwrite existing assets (pass 'yes' or 'y') |
| `--dry-run` | Optional | Run validation without uploading |
| `--workers` | Optional | Number of parallel workers (default: 1) |
| `--max-inflight-tasks` | Optional | Maximum concurrent EE tasks (default: 2500) |
| `--resume` | Optional | Resume from previous state |
| `--retry-failed` | Optional | Retry only failed uploads |
| `--max-error-meters` | Optional | Maximum geometry error in meters (default: 1.0) |
| `--max-vertices` | Optional | Maximum vertices per geometry (default: 1000000) |

**Features:**
- Supports both zipped shapefiles and CSV files
- Automatic folder creation with confirmation
- State persistence for resumable uploads
- Progress tracking with file-level details

## Monitoring

### Check Quota

Display Earth Engine storage usage and asset counts with visual progress bars.

**Check all quotas:**
```bash
geeup quota
```

**Check specific project:**
```bash
geeup quota --project "projects/my-project"
```

**Arguments:**
- `--project`: Project name in format `projects/project-name/assets/` (optional)

**Output includes:**
- Storage usage (bytes/GB)
- Asset count
- Visual progress bars
- Support for both legacy and cloud projects

### Task Status

Query the status of Earth Engine tasks with rich formatting.

**Summary of all tasks:**
```bash
geeup tasks
```

**Filter by state:**
```bash
geeup tasks --state RUNNING
```

**Query specific task:**
```bash
geeup tasks --id "TASK_ID_HERE"
```

**Arguments:**
- `--state`: Filter by state (COMPLETED, READY, RUNNING, FAILED, CANCELLED)
- `--id`: Query specific task ID

### Cancel Tasks

Cancel Earth Engine tasks with progress tracking.

**Cancel all tasks:**
```bash
geeup cancel --tasks all
```

**Cancel running tasks:**
```bash
geeup cancel --tasks running
```

**Cancel pending tasks:**
```bash
geeup cancel --tasks pending
```

**Cancel specific task:**
```bash
geeup cancel --tasks "TASK_ID_HERE"
```

**Arguments:**
- `--tasks`: Specify 'all', 'running', 'pending', or a specific task ID (required)

## Utilities

### Delete Assets

Recursively delete an Earth Engine asset (collection, folder, or image).

```bash
geeup delete --id "users/username/test_collection"
```

**Arguments:**
- `--id`: Full path to asset for deletion (required)

**Warning:** This action cannot be undone. Use with caution.

### Open Documentation

Open the official geeup documentation in your default web browser.

```bash
geeup readme
```

## Full Documentation

Find the complete documentation at: [https://geeup.geetools.xyz](https://geeup.geetools.xyz)

## Changelog

### Version 2.0.0
- Enhanced path normalization for legacy and cloud projects
- Added service account authentication support
- Improved parallel processing with worker threads
- Added resume and retry capabilities for failed uploads
- Enhanced metadata generation with GDAL integration
- Better error handling and progress tracking
- Rich console output with visual progress bars
- State persistence for resumable workflows

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

This tool borrows features from another project of mine, [geeadd](https://geeadd.geetools.xyz), such as quota estimation, task monitoring, and cancellation capabilities.
