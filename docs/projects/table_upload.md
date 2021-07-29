# Table Upload

This tool allows you to batch download tables/shapefiles/CSVs to a folder. It uses a modified version of the image upload and a wrapper around the earthengine upload cli to achieve this while creating folders if they don't exist and reporting on assets and checking on uploads. This only requires a source, destination and your ee authenticated email address. This tool also uses selenium to upload the tables. The table upload tool now allows the user to copy cookie list from your browser and bypass selenium based authentication. It saves the cookie temporarily and uses it automatically till it expires when it asks you for cookie list again. Just use the ```--method cookies``` argument.

```
usage: geeup tabup [-h] --source SOURCE --dest DEST [-u USER]
                   [--method METHOD] [--x X] [--y Y]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments.:
  --source SOURCE       Path to the directory with zipped files or CSV files
                        for upload.
  --dest DEST           Destination. Full path for upload to Google Earth
                        Engine folder, e.g. users/pinkiepie/myfolder
  -u USER, --user USER  Google account name (gmail address).
  --method METHOD       Choose method <cookies> to use cookies to authenticate

Optional named arguments:
  --x X                 Column with longitude value
  --y Y                 Column with latitude value
```

If you are using cookies for table upload setup would be

```
geeup tabup --source "full path to folder with Zipped Shapefiles/CSV files" --dest "Full path for upload to Google Earth Engine, e.g. users/pinkiepie/folder" --user "email@domain.com authenticated and used with GEE" --method "cookies"
```
