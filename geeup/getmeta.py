from __future__ import print_function
import os
import csv


def getmeta(indir, mfile):
    try:
        from osgeo import gdal
    except ImportError:
        import gdal
    i = 1
    flength = len([name for name in os.listdir(indir) if name.endswith(".tif")])
    with open(mfile, "w") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["id_no", "xsize", "ysize", "num_bands"],
            delimiter=",",
            lineterminator="\n",
        )
        writer.writeheader()
    for filename in os.listdir(indir):
        if filename.endswith(".tif"):
            gtif = gdal.Open(os.path.join(indir, filename))
            try:
                print("Processed: " + str(i) + " of " + str(flength), end="\r")
                fname = os.path.basename(gtif.GetDescription()).split(".")[0]
                xsize = gtif.RasterXSize
                ysize = gtif.RasterYSize
                bsize = gtif.RasterCount
                with open(mfile, "a") as csvfile:
                    writer = csv.writer(csvfile, delimiter=",", lineterminator="\n")
                    writer.writerow([fname, xsize, ysize, bsize])
                csvfile.close()
                i = i + 1
            except Exception as e:
                print(e)
                i = i + 1


##getmeta(indir=r'C:\planet_demo\dbwater\water_mask_2017_v1',
##    mfile=r'C:\planet_demo\rmeta.csv')
