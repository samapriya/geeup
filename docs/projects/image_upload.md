# Image Upload tool

geeup's `upload` command empowers you to effortlessly create an Image Collection from GeoTIFFs stored in your local directory. With this tool, you can streamline the process of uploading GeoTIFFs to Google Earth Engine, simplifying your geospatial data management tasks.

#### Key Features

- **GeoTIFF Collection**: geeup's `upload` command allows you to create an Image Collection directly from GeoTIFFs stored in your local directory.

- **Custom Image Names**: By default, the script assigns the image name in the collection based on the local directory name, giving you flexibility in naming.

- **Cookie Authentication**: The tool now supports cookie-based authentication for uploads. It temporarily saves and automatically uses your browser's cookies until they expire, eliminating the need for constant reauthentication. For more details on cookie setup, visit [cookie setup guide](https://samapriya.github.io/geeup/projects/cookies_setup/).

- **Advanced Options**: Customize your upload process by specifying optional arguments, including Pyramiding strategy (default is set to Mean), NoData value, and an option to overwrite existing data.

#### Usage

```markdown
geeup upload -h

usage: geeup upload [-h] --source SOURCE --dest DEST -m METADATA [--nodata NODATA] [--pyramids PYRAMIDS] [--overwrite OVERWRITE] [-u USER]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments:
  --source SOURCE       Path to the directory with images for upload.
  --dest DEST           Destination. Full path for upload to Google Earth Engine image collection, e.g., users/pinkiepie/myponycollection
  -m METADATA, --metadata METADATA
                        Path to CSV with metadata.
  -u USER, --user USER  Google account name (gmail address).

Optional named arguments:
  --nodata NODATA       The value to burn into the raster as NoData (missing data).
  --pyramids PYRAMIDS   Pyramiding Policy (default: Mean), options: MEAN, MODE, MIN, MAX, SAMPLE.
  --overwrite OVERWRITE
                        Default is No, but you can pass yes or y to overwrite existing data.
```

#### Example

Here's an example of how to set up and use the `upload` command with geeup:

![geeup Image Upload Example](https://user-images.githubusercontent.com/6677629/147895638-3d542ea5-2c72-43b7-8052-c5edef0ab717.gif)

If you are using cookies for image upload, the setup would be as follows:

```bash
geeup upload --source "full path to folder with GeoTIFFs" --dest "Full path for upload to Google Earth Engine, e.g., users/pinkiepie/myponycollection" --metadata "Full path for metadata file.csv" --user "email@domain.com authenticated and used with GEE" --nodata 0 --pyramids MODE
```
