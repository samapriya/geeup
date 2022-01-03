# Image Upload

The script creates an Image Collection from GeoTIFFs in your local directory. By default, the image name in the collection is the same as the local directory name. The upload tool now allows only supports using cookies from your browser for uploads. It saves the cookie temporarily and uses it automatically till it expires when it asks you for cookie list again. For more details on [cookie setup go here](https://samapriya.github.io/geeup/projects/cookies_setup/). Optional arguments now includes passing both Pyramiding strategy (default is set to Mean) as well as no data value.


```
geeup upload -h
usage: geeup upload [-h] --source SOURCE --dest DEST -m METADATA [--nodata NODATA] [--pyramids PYRAMIDS] [-u USER]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments.:
  --source SOURCE       Path to the directory with images for upload.
  --dest DEST           Destination. Full path for upload to Google Earth Engine image collection, e.g. users/pinkiepie/myponycollection
  -m METADATA, --metadata METADATA
                        Path to CSV with metadata.
  -u USER, --user USER  Google account name (gmail address).

Optional named arguments:
  --nodata NODATA       The value to burn into the raster as NoData (missing data)
  --pyramids PYRAMIDS   Pyramiding Policy, MEAN, MODE, MIN, MAX, SAMPLE
```

Example setup would be

![gee_upload](https://user-images.githubusercontent.com/6677629/147895638-3d542ea5-2c72-43b7-8052-c5edef0ab717.gif)

If you are using cookies for image upload setup would be

```
geeup upload --source "full path to folder with GeoTIFFs" --dest "Full path for upload to Google Earth Engine, e.g. users/pinkiepie/myponycollection" --metadata "Full path for metadata file.csv" --user "email@domain.com authenticated and used with GEE" --nodata 0 --pyramids MODE
```
