# geeup: Simple CLI for Earth Engine Uploads with Selenium Support &nbsp; [![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=Use%20porder%20CLI%20with%20@planetlabs%20new%20ordersv2%20API&url=https://github.com/samapriya/geeup)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3369484.svg)](https://doi.org/10.5281/zenodo.3369484)
[![PyPI version](https://badge.fury.io/py/geeup.svg)](https://badge.fury.io/py/geeup)
![Build Status](https://img.shields.io/badge/dynamic/json.svg?label=downloads&url=https%3A%2F%2Fpypistats.org%2Fapi%2Fpackages%2Fgeeup%2Frecent%3Fperiod%3Dmonth&query=%24.data.last_month&colorB=blue&suffix=%2fmonth)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This tool came of the simple need to handle batch uploads of both image assets to collections but also thanks to the new table feature the possibility of batch uploading shapefiles into a folder. Though a lot of these tools including batch image uploader is part of my other project [geeadd](https://github.com/samapriya/gee_asset_manager_addon) which also includes additional features to add to the python CLI, this tool was designed to be minimal so as to allow the user to simply query their quota, upload images or tables and also to query ongoing tasks and delete assets. I am hoping this tool with a simple objective proves useful to a few users of Google Earth Engine.

-If you find this tool useful, star and cite it as below

```
Samapriya Roy. (2019, August 16). samapriya/geeup: geeup: Simple CLI for Earth Engine Uploads (Version 0.2.5). Zenodo.
http://doi.org/10.5281/zenodo.3369484
```

## Table of contents
* [Installation](#installation)
* [Getting started](#getting-started)
* [geeup Simple CLI for Earth Engine Uploads](#geeup-simple-cli-for-earth-engine-uploads)
    * [geeup init](#geeup-init)
    * [gee Quota](#gee-quota)
    * [gee getmeta](#gee-getmeta)
    * [gee Zipshape](#gee-zipshape)
    * [gee upload](#gee-upload)
    * [gee seltabup](#gee-seltabup)
    * [gee selsetup](#gee-selsetup)
    * [gee tasks](#gee-tasks)
    * [gee delete](#gee-delete)

## Installation
This assumes that you have native python & pip installed in your system, you can test this by going to the terminal (or windows command prompt) and trying

```python``` and then ```pip list```

If you get no errors and you have python 2.7.14 or higher you should be good to go. Please note that I have tested this only on python 2.7.15, but it should run on Python 3.

**This command line tool is dependent on shapely and fiona and as such uses functionality from GDAL**
For installing GDAL in Ubuntu
```
sudo add-apt-repository ppa:ubuntugis/ppa && sudo apt-get update
sudo apt-get install gdal-bin
sudo apt-get install python-gdal
```
For Windows I found this [guide](https://webcache.googleusercontent.com/search?q=cache:UZWc-pnCgwsJ:https://sandbox.idre.ucla.edu/sandbox/tutorials/installing-gdal-for-windows+&cd=4&hl=en&ct=clnk&gl=us) from UCLA

You can also install the unofficial binary for windows for [gdal here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal)

Also for Ubuntu Linux I saw that this is necessary before the install

```sudo apt install libcurl4-openssl-dev libssl-dev```

**This also needs earthengine cli to be [installed and authenticated on your system](https://developers.google.com/earth-engine/python_install_manual) and earthengine to be callable in your command line or terminal**

To install **geeup: Simple CLI for Earth Engine Uploads** you can install using two methods.

```pip install geeup```

or you can also try

```
git clone https://github.com/samapriya/geeup.git
cd geeup
python setup.py install
```
For Linux use sudo or try ```pip install geeup --user```.

Installation is an optional step; the application can also be run directly by executing geeup.py script. The advantage of having it installed is that geeup can be executed as any command line tool. I recommend installation within a virtual environment. If you don't want to install, browse into the geeup folder and try ```python geeup.py``` to get to the same result.


## Getting started

As usual, to print help:

```
usage: geeup.py [-h]
                {update,quota,zipshape,upload,selupload,seltabup,tasks,delete}
                ...

Simple Client for Earth Engine Uploads with Selenium Support

positional arguments:
  {update,quota,zipshape,upload,selupload,seltabup,tasks,delete}
    update              Updates Selenium drivers for firefox
    quota               Print Earth Engine total quota and used quota
    zipshape            Zips all shapefiles and subsidary files into
                        individual zip files
    getmeta             Generates generalized metadata for all rasters in folder
    upload              Batch Asset Uploader using Selenium
    seltabup            Batch Table Uploader using Selenium.
    selsetup            Non headless setup for new google account, use if upload
                        throws errors
    tasks               Queries current task status
                        [completed,running,ready,failed,cancelled]
    delete              Deletes collection and all items inside. Supports
                        Unix-like wildcards.

optional arguments:
  -h, --help            show this help message and exit

```

To obtain help for specific functionality, simply call it with _help_ switch, e.g.: `geeup zipshape -h`. If you didn't install geeup, then you can run it just by going to *geeup* directory and running `python geeup.py [arguments go here]`

## geeup Simple CLI for Earth Engine Uploads
The tool is designed to handle batch uploading of images and tables(shapefiles). While there are image collection where you can batch upload imagery, for vector or shapefiles you have to batch upload them to a folder.

### geeup init
**This is a key step since all upload function depends on this step, so make sure you run this**. This downloads selenium driver and places to your local directory for windows and Linux subsystems. This is the first step to use selenium supported upload.

``` geeup init```

### gee Quota
Just a simple tool to print your earth engine quota quickly.

```
usage: geeup quota [-h]

optional arguments:
  -h, --help  show this help message and exit
```

### gee Zipshape
So here's how table upload in Google Earth Engine works, you can either upload the component files shp, shx, prj and dbf or you can zip these files together and upload it as a single file. The pros for this is that it reduces the overall size of the shapefile after zipping them along, this tool looks for the shp file and finds the subsidiary files and zips them ready for upload. It also helps when you have limited upload bandwidth. Cons you have to create a replicate structure of the file system, but it saves on bandwidth and auto-arranges your files so you don't have to look for each additional file.

```
usage: geeup zipshape [-h] --input INPUT --output OUTPUT

optional arguments:
  -h, --help       show this help message and exit

Required named arguments.:
  --input INPUT    Path to the input directory with all shape files
  --output OUTPUT  Destination folder Full path where shp, shx, prj and dbf
                   files if present in input will be zipped and stored
```

### gee getmeta
This script generates a generalized metadata using information parsed from gdalinfo and metadata properties. For now it generates metadata with image name, x and y dimension of images, the pixel resolution and the number of bands.

```
usage: geeup getmeta [-h] --input INPUT --metadata METADATA

optional arguments:
  -h, --help       show this help message and exit

Required named arguments.:
  --input INPUT        Path to the input directory with all raster files
  --metadata METADATA  Full path to export metadata.csv file

```

### gee upload
The script creates an Image Collection from GeoTIFFs in your local directory. By default, the image name in the collection is the same as the local directory name; with the optional parameter you can provide a different name.

```
usage: geeup upload [-h] --source SOURCE --dest DEST -m METADATA
                    [--nodata NODATA] [-u USER]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments.:
  --source SOURCE       Path to the directory with images for upload.
  --dest DEST           Destination. Full path for upload to Google Earth
                        Engine, e.g. users/pinkiepie/myponycollection
  -m METADATA, --metadata METADATA
                        Path to CSV with metadata.
  -u USER, --user USER  Google account name (gmail address).

Optional named arguments:
  --nodata NODATA       The value to burn into the raster as NoData (missing
                        data)
```

### gee seltabup
This tool allows you to batch download tables/shapefiles to a folder. It uses a modified version of the image upload and a wrapper around the earthengine upload cli to achieve this while creating folders if they don't exist and reporting on assets and checking on uploads. This only requires a source, destination and your ee authenticated email address. This tool also uses selenium to upload the tables.

```
usage: geeup seltabup [-h] --source SOURCE --dest DEST [-u USER]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments.:
  --source SOURCE       Path to the directory with zipped folder for upload.
  --dest DEST           Destination. Full path for upload to Google Earth
                        Engine, e.g. users/pinkiepie/myponycollection
  -u USER, --user USER  Google account name (gmail address).
```

### gee selsetup
Once in a while the geckodriver requires manual input before signing into the google earth engine, this tool will allow you to interact with the initialization of Google Earth Engine code editor window. It allows the user to specify the account they want to use, and should only be needed once.

```geeup selsetup```

### gee tasks
This script counts all currently running, ready, completed, failed and canceled tasks along with failed tasks. This tool is linked to your google earth engine account with which you initialized the earth engine client. This takes no argument.

```
usage: geeup tasks [-h]

optional arguments:
  -h, --help  show this help message and exit
```

### gee delete
The delete is recursive, meaning it will also delete all children assets: images, collections, and folders. Use with caution!

```
usage: geeup delete [-h] id

positional arguments:
  id          Full path to asset for deletion. Recursively removes all
              folders, collections and images.

optional arguments:
  -h, --help  show this help message and exit
```
# Changelog

### v0.2.9

- Fixed issues caused by --no-use_cloud_api in earthengine-api package

### v0.2.7

- Fix to handle case senstive platform type for all os Fix to [Issue 11](https://github.com/samapriya/geeup/issues/11)

### v0.2.6

- Fixed geckodriver path to handle macos Fix to [Issue 10](https://github.com/samapriya/geeup/issues/10)

### v0.2.5

- Now allows for downloading geckodriver for macos Fix to [Issue 10](https://github.com/samapriya/geeup/issues/10)
- Now includes a metadata tool to generate a generalized metadata for any raster to allow upload.
Fix to [Issue 7](https://github.com/samapriya/geeup/issues/7)
- Changed from geeup update to init to signify initialization
- Added selsetup this tool allows for setting up the gecko driver with your account incase there are issues uploading
- Better error handling for selenium driver download

### v0.2.4

- Made general improvements
- Better error handling for selenium driver download

### v0.2.2

- Can now handle generalized metadata (metadata is now required field)
- Fixed issues with table upload
- Overall code optimization and handle streaming upload

### v0.1.9

- Changes to handle PyDL installation for Py2 and Py3
- Removed Planet uploader to make tool more generalized

### v0.1.8

- Multipart encoder using requests toolbelt for streaming upload
- Changed manifest upload methodology to match changes in earthengine-api

### v0.1.6

- Fixed issue with [module locations](https://github.com/samapriya/geeup/issues/2)

### v0.1.5

- Fixed issue with gecko driver paths
- Fixed issue with null uploads using task, switched to ee CLI upload

### v0.1.4

- OS based geckdriver path fix
- General improvements

### v0.1.3

- fixed issues with extra arguments
- Upload issue resolved
- General dependency

### v0.1.1

- fixed dependency issues
- Upload post issues resolved
- Removed dependency on poster for now

### v0.0.9

- fixed attribution and dependecy issues
- Included poster to improve streaming uploads
- All uploads now use selenium

### v0.0.8

- fixed issues with unused imports

### v0.0.7

- fixed issues with manifest lib

### v0.0.6

- Detailed quota readout
- Uses selenium based uploader to upload images
- Avoids issues with python auth for upload

### v0.0.5

- Removed unnecessary library imports
- Minor improvements and updated readme

### v0.0.4

- Improved valid table name check before upload
- Improvements to earth engine quota tool for more accurate quota and human readable
