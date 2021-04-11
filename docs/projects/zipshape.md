# Zip Shapefiles

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

Example setup would be the following

![geeup_zipshape](https://user-images.githubusercontent.com/6677629/114293099-f8637800-9a58-11eb-9873-b36df8bb4245.gif)
