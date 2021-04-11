#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from logzero import logger
from zipfile import ZipFile
import geopandas as gp

overall = []


def vcount(shpfile):
    df = gp.read_file(shpfile)
    if not df.size == 0:
        for i, row in df.iterrows():
            # It's better to check if multigeometry
            multi = row.geometry.type.startswith("Multi")
            if multi:
                n = 0
                # iterate over all parts of multigeometry
                for part in row.geometry:
                    n += len(part.exterior.coords)
            else:  # if single geometry like point, linestring or polygon
                n = len(row.geometry.exterior.coords)

            # print('Total vertices: {:,}'.format(n))
            overall.append(n)
        if all(i < 1000000 for i in overall) == True:
            return sum(overall)
        else:
            logger.warning(
                shpfile
                + " has overall max vertex of "
                + str(max(overall))
                + " with max allowed 1000000 ingest might fail"
            )
            return sum(overall)
            # print('Total vertices per feature exceeded max. Overall vertices: {}'.format(sum(overall)))
            # return sum(overall)
    else:
        return df.size


ex = [".shp", ".prj", ".dbf", ".shx"]

file_paths = []
i = 1


def zipshape(directory, export):
    for (root, directories, files) in os.walk(directory):
        for filename in files:
            if filename.endswith(".shp"):
                # print(os.path.join(directory,filename))
                # print(vcount(os.path.join(directory,filename)))
                if vcount(os.path.join(directory, filename)) > 0:
                    file_paths = []
                    filebase = filename.split(".")[0]
                    try:
                        for things in ex:
                            if os.path.exists(os.path.join(root, filebase + things)):
                                filepath = os.path.join(root, filebase + things)
                                # print(filepath)
                                file_paths.append(filepath)
                        os.chdir(export)
                        if not os.path.exists(filebase + ".zip") and int(
                            len(file_paths)
                        ) == int(4):
                            with ZipFile(filebase + ".zip", "w") as zip:
                                print(
                                    "Creating zipped folder "
                                    + str(filebase)
                                    + ".zip"
                                    + " at "
                                    + str(export)
                                )
                                # writing each file one by one
                                for file in file_paths:
                                    fname = os.path.basename(file)
                                    zip.write(file, fname)
                        else:
                            print(
                                "File already exists: "
                                + str(filebase + ".zip")
                                + " SKIPPING"
                            )
                    except:
                        pass


# get_all_file_paths(directory=r"C:\Users\samapriya\Downloads\nexgengrid",export=r'D:\Library')
