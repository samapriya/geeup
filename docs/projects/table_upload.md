# Table Upload tool

geeup's `tabup` command simplifies the process of batch uploading tables, shapefiles, and CSV files to Google Earth Engine. This versatile tool uses a modified version of the image upload and acts as a wrapper around the `earthengine` upload CLI, ensuring a seamless experience for users. It can create folders if they don't exist and provides asset reporting while checking on uploads.

#### Key Features

- **Batch Upload**: Easily upload multiple tables, shapefiles, or CSV files to Google Earth Engine in a single operation, saving you time and effort.

- **Folder Creation**: geeup's `tabup` command can automatically create folders if they do not exist at the specified destination.

- **Asset Reporting**: Get detailed reports on the status of your assets during the upload process, ensuring transparency and accountability.

- **Cookie Authentication**: For added convenience, this tool supports cookie-based authentication, temporarily saving and automatically using your browser's cookies until they expire. For more details on cookie setup, visit [cookie setup guide](https://samapriya.github.io/geeup/projects/cookies_setup/).

#### Usage

```bash
geeup tabup -h

usage: geeup tabup [-h] --source SOURCE --dest DEST [-u USER] [--x X] [--y Y] [--overwrite OVERWRITE]

optional arguments:
  -h, --help            show this help message and exit

Required named arguments:
  --source SOURCE       Path to the directory with zipped files or CSV files for upload.
  --dest DEST           Destination. Full path for upload to Google Earth Engine folder, e.g., users/pinkiepie/myfolder
  -u USER, --user USER  Google account name (Gmail address).

Optional named arguments:
  --x X                 Column with longitude value.
  --y Y                 Column with latitude value.
  --overwrite OVERWRITE Default is No, but you can pass yes or y to overwrite existing data.
```

#### Example

Here's an example of how to set up and use the `tabup` command with geeup:

![geeup Table Upload Example](https://user-images.githubusercontent.com/6677629/147895900-4e4a14c4-ed89-4d3d-8572-b96198703ade.gif)

If you are using cookies for table upload, the setup would be as follows:

```bash
geeup tabup --source "full path to folder with Zipped Shapefiles/CSV files" --dest "Full path for upload to Google Earth Engine, e.g., users/pinkiepie/folder" --user "email@domain.com authenticated and used with GEE"
```
