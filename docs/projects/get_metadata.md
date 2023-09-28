# Get Metadata tool

geeup's `getmeta` command is a powerful tool designed to generate generalized metadata for raster images using information parsed from `gdalinfo` and metadata properties. With this feature, you can quickly obtain essential details about your raster images, such as the image name, dimensions (x and y), and the number of bands. This metadata can be invaluable for organizing and managing your geospatial data effectively.

#### Key Features

- **Metadata Generation**: Automatically generate metadata for raster images in your dataset, providing crucial information about each file.

- **Effortless Setup**: geeup's `getmeta` command is easy to use, requiring just a few simple arguments to start generating metadata.

- **Comprehensive Information**: Obtain image name, x and y dimensions, and the number of bands, giving you a clear overview of your raster assets.

- **CSV Export**: Export the generated metadata to a CSV file, making it accessible for further analysis or integration into your geospatial workflows.

#### Usage

```bash
usage: geeup getmeta [-h] --input INPUT --metadata METADATA

optional arguments:
  -h, --help             show this help message and exit

Required named arguments:
  --input INPUT          Path to the input directory with all raster files
  --metadata METADATA    Full path to export metadata.csv file
```

## Example

Here's an example of how to set up and use the `getmeta` command with geeup:

![geeup GetMeta Example](https://user-images.githubusercontent.com/6677629/114294172-56488d80-9a62-11eb-8b18-540bf8e8a39a.gif)

Simply provide the path to your input directory containing the raster files, specify the full path for the exported `metadata.csv` file, and let geeup do the rest. It will generate a metadata file with the crucial information you need for your raster images, making your geospatial data management more efficient.

