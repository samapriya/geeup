from __future__ import print_function

import csv
import os

from geotiff import GeoTiff


def getmeta(indir, mfile):
    i = 1
    flength = len([name for name in os.listdir(
        indir) if name.endswith(".tif")])
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
            gtif = GeoTiff(os.path.join(indir, filename))
            try:
                print("Processed: " + str(i) + " of " + str(flength), end="\r")
                fname = os.path.basename(filename).split(".tif")[0]
                xsize = gtif.tif_shape[1]
                ysize = gtif.tif_shape[2]
                bsize = gtif.tif_shape[0]
                with open(mfile, "a") as csvfile:
                    writer = csv.writer(
                        csvfile, delimiter=",", lineterminator="\n")
                    writer.writerow([fname, xsize, ysize, bsize])
                csvfile.close()
                i = i + 1
            except Exception as error:
                print(error)
                i = i + 1


# getmeta(indir=r'C:\planet_demo\dbwater\water_mask_2017_v1',
# mfile=r'C:\planet_demo\rmeta.csv')
