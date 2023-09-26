#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from zipfile import ZipFile

from logzero import logger

overall = []


ex = [".shp", ".prj", ".dbf", ".shx"]

file_paths = []
i = 1


def zipshape(directory, export):
    for (root, directories, files) in os.walk(directory):
        for filename in files:
            if filename.endswith(".shp"):
                file_paths = []
                filebase = filename.split(".")[0]
                try:
                    for things in ex:
                        if os.path.exists(os.path.join(root, filebase + things)):
                            filepath = os.path.join(root, filebase + things)
                            # print(filepath)
                            file_paths.append(filepath)
                    if not os.path.exists(export):
                        os.makedirs(export)
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
                    logger.exception(e)


# get_all_file_paths(directory=r"C:\Users\samapriya\Downloads\nexgengrid",export=r'D:\Library')
