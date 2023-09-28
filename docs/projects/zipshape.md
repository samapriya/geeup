# Zip Shapefiles tool

Uploading shapefiles to Google Earth Engine can be done in two ways: you can either upload the component files (shp, shx, prj, and dbf) individually, or you can zip these files together into a single archive for more efficient uploading. The latter approach offers advantages, such as reducing the overall size of the shapefile and conserving bandwidth, especially when dealing with limited upload speeds.

geeup's `zipshape` command is designed to streamline the process of zipping shapefiles for Google Earth Engine uploads. It automatically locates the primary `.shp` file and identifies and zips the associated subsidiary files (shx, prj, and dbf) to create a single, ready-to-upload archive. This tool also eliminates the need for manually arranging files and ensures that your shapefiles are efficiently prepared for ingestion into Google Earth Engine.

#### Key Features

- **Effortless Zipping**: geeup's `zipshape` command simplifies the process of zipping shapefiles by automatically identifying and compressing the necessary files.

- **Size Reduction**: Compressing shapefiles reduces their overall size, making the uploading process more efficient.

- **Bandwidth Conservation**: Zipping files together conserves bandwidth, making it ideal for users with limited upload speeds.

- **Automated Organization**: This tool auto-arranges your files, saving you the hassle of manually searching for and organizing each additional file.

#### Usage

```markdown
usage: geeup zipshape [-h] --input INPUT --output OUTPUT

optional arguments:
  -h, --help             show this help message and exit

Required named arguments:
  --input INPUT          Path to the input directory with all shape files
  --output OUTPUT        Destination folder Full path where shp, shx, prj, and dbf files if present in input will be zipped and stored
```

#### Example

Here's an example of how to use the `zipshape` command with geeup:

![geeup Zip Shapefiles Example](https://user-images.githubusercontent.com/6677629/114293099-f8637800-9a58-11eb-9873-b36df8bb4245.gif)

Simply provide the path to the directory containing your shapefiles, specify the destination folder for the zipped files, and geeup will handle the rest. It automatically identifies and compresses the necessary files, saving you time and ensuring your shapefiles are efficiently prepared for Google Earth Engine uploads.

Streamline your shapefile uploads to Google Earth Engine and conserve bandwidth with geeup's `zipshape` command.
