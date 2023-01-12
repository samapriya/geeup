# Changelog

### 0.6.0
- Better error logging for GeoTiff uploads
- Fixed [Issue 52](https://github.com/samapriya/geeup/issues/52)

### 0.5.9
- Reduced dependency on pipwin and removed pipwin refresh checks
- Fixed python path issue for pip installation
- Allow for overwriting assets in folders or collections
- Created consistent output including task ID for both tables and images
- Overall improvements and modifications

### 0.5.8
- Adding dependency on GDAL again to handle custom geotiffs correctly.
- Added back rename tool and improvements made in v0.5.6
- Updated language to notify users of images in a collection or tables in a folder

### 0.5.7
- Getmeta tool now generates crs and bounding box

### 0.5.6
- Removed dependency on GDAL

### 0.5.5
- Made sure table and image upload use the term associated tasks
- geeup tasks now uses updateTime to prevent key error for RUNNING tasks
- zipshape tool can now create the export directory if it does not exist

### 0.5.4
- Major version improvements to performance and codebase
- Added rename tool to allow file renaming to EE rules
- Added natural sorting to sort filenames to be ingested
- Added capability for image and table upload to check for both existing assets and assets in task queue before retrying
- Added task check capability to avoid 3000 tasks in queue
- Updated and optimized failure checks and logging
- Added path and asset schema check for EE rulesets
- Updated docs and readme

### 0.5.3
- Major version removed selenium support as stable method
- Overall improvements to performance and codebase
- Updated docs and ReadMe

### 0.5.2
- Fixed GDAL check for package

### 0.5.1
- Now support both zipped shapefile as well as batch CSV upload
- General Improvements

### 0.5.0
- fixed typo in version check

### v0.4.9
- Improvements to redundancy in code
- Improvements to version check for tool
- General cleanup

### v0.4.8
- Fixed issue with epoch time conversion for 1970s and issue with second vs millisecond parsing

### v0.4.7
- Both table and image upload support using cookies and better error handling.
- Improved zipshape tool to avoid error handling
- Image upload to collection now support pyramiding policy
- Cookie setup tool now auto enables long string for Linux

### v0.4.6
- Now pass cookies for authentication and image and table uploaders.
- Added readme docs and feature to the tool
- Minor improvements to the overall tool.

### v0.4.5
- Replaced firefox_options with options for selenium 3.14 and higher related to [issue 24](https://github.com/samapriya/geeup/issues/24) for selsetup
- updated earthengine-api requirement to 0.1.238
- update tasks fetch from earthengine api

### v0.4.4
- Replaced firefox_options with options for selenium 3.14 and higher related to [issue 24](https://github.com/samapriya/geeup/issues/24)

### v0.4.3
- Updated quota tool to handle Google Cloud Projects in GEE

### v0.4.2
- Fixed issue with [geckodriver path](https://github.com/samapriya/geeup/issues/22) and better path parsing
- Added CI check for geckodriver

### v0.4.1
- Fixed selenium parser issue [Issue 19](https://github.com/samapriya/geeup/issues/19)
- Implemented Cloud API fix for table uploads
- Improved Cloud API fix for Imagery upload with improved manifest handling
- Improvement and code cleanup

### v0.4.0
- Updated earthengine API library requirements to 0.1.222
- Added version check tool for auto version check with PyPI

### v0.3.7
- Revisions to account for changes to API and client library 0.1.215
- Now checks vertex count for each shapefile and logs warning with those exceeding million vertices while zipping.
- Uses table manifest to perform table uploads designed to be more robust.
- Simpler recursive delete functionality.
- Overall General improvements.

### v0.3.5-v0.3.6
- Fixed downloader for pipwin for [release >= 0.4.8](https://github.com/lepisma/pipwin/pull/41)
- Improved overall package installation for windows
- Check pipwin import version to get release 0.4.9

### v0.3.4
- Supports python3 only since v0.3.4
- Added stackoverflow based auth fix for some users [Issue 13](https://github.com/samapriya/geeup/issues/13) and [Issue 16](https://github.com/samapriya/geeup/issues/16).
- General improvements.

### v0.3.3
- Added fix for handling no data in manifests while uploading.

### v0.3.2
- Fixed issue with selsetup.

### v0.3.1
- Fixed issue with raw_input and input for selsetup.
- Fixed selenium path for windows and other platforms.
- General improvements to ReadMe

### v0.3.0
- Fixed (issue 13)[https://github.com/samapriya/geeup/issues/13] non relative import.
- Fixed issues with package import.

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
