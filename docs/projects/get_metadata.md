# Get Metadata

This script generates a generalized metadata using information parsed from gdalinfo and metadata properties. For now it generates metadata with image name, x and y dimension of images, and the number of bands.

```
usage: geeup getmeta [-h] --input INPUT --metadata METADATA

optional arguments:
  -h, --help       show this help message and exit

Required named arguments.:
  --input INPUT        Path to the input directory with all raster files
  --metadata METADATA  Full path to export metadata.csv file

```

Example setup would be

![geeup_getmeta](https://user-images.githubusercontent.com/6677629/114294172-56488d80-9a62-11eb-8b18-540bf8e8a39a.gif)
