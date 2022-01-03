# Table Upload

This tool allows you to batch download tables/shapefiles/CSVs to a folder. It uses a modified version of the image upload and a wrapper around the earthengine upload cli to achieve this while creating folders if they don't exist and reporting on assets and checking on uploads. This only requires a source, destination and your ee authenticated email address. The table upload tool now allows only supports using cookies from your browser for uploads. It saves the cookie temporarily and uses it automatically till it expires when it asks you for cookie list again. For more details on [cookie setup go here](https://samapriya.github.io/geeup/projects/cookies_setup/).

```
geeup tabup -h
usage: geeup tabup [-h] --source SOURCE --dest DEST [-u USER] [--x X] [--y Y]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments.:
  --source SOURCE       Path to the directory with zipped files or CSV files for upload.
  --dest DEST           Destination. Full path for upload to Google Earth Engine folder, e.g. users/pinkiepie/myfolder
  -u USER, --user USER  Google account name (gmail address).

Optional named arguments:
  --x X                 Column with longitude value
  --y Y                 Column with latitude value
```
Example setup

![gee_tabup](https://user-images.githubusercontent.com/6677629/147895900-4e4a14c4-ed89-4d3d-8572-b96198703ade.gif)

If you are using cookies for table upload setup would be

```
geeup tabup --source "full path to folder with Zipped Shapefiles/CSV files" --dest "Full path for upload to Google Earth Engine, e.g. users/pinkiepie/folder" --user "email@domain.com authenticated and used with GEE"
```
