from .batch_uploader import upload
from .getmeta import getmeta
from .tuploader import tabup
from .zipfiles import zipshape

__copyright__ = """

    Copyright 2021 Samapriya Roy

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
__license__ = "Apache 2.0"

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
import webbrowser
from datetime import datetime

import ee
import pkg_resources
import requests
from logzero import logger

os.chdir(os.path.dirname(os.path.realpath(__file__)))


class Solution:
    def compareVersion(self, version1, version2):
        versions1 = [int(v) for v in version1.split(".")]
        versions2 = [int(v) for v in version2.split(".")]
        for i in range(max(len(versions1), len(versions2))):
            v1 = versions1[i] if i < len(versions1) else 0
            v2 = versions2[i] if i < len(versions2) else 0
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0


ob1 = Solution()

if str(platform.system().lower()) == "windows":
    version = sys.version_info[0]
    try:
        import pipgeo
        response = requests.get('https://pypi.org/pypi/pipgeo/json')
        latest_version = response.json()['info']['version']
        vcheck = ob1.compareVersion(
            latest_version,
            pkg_resources.get_distribution("pipgeo").version,
        )
        if vcheck == 1:
            subprocess.call(
                f"{sys.executable}" + " -m pip install pipgeo --upgrade", shell=True
            )
    except ImportError:
        subprocess.call(
            f"{sys.executable}" + " -m pip install pipgeo", shell=True
        )
    except Exception as e:
        logger.exception(e)
    try:
        import gdal
    except ImportError:
        try:
            from osgeo import gdal
        except ModuleNotFoundError:
            subprocess.call("pipgeo fetch --lib gdal", shell=True)
    except ModuleNotFoundError or ImportError:
        subprocess.call("pipgeo fetch --lib gdal", shell=True)
    except Exception as e:
        logger.exception(e)
    try:
        import pandas
    except ImportError:
        subprocess.call(
            f"{sys.executable}" + " -m pip install pandas", shell=True
        )
    except Exception as e:
        logger.exception(e)

lpath = os.path.dirname(os.path.realpath(__file__))
sys.path.append(lpath)

# Get package version


def version_latest(package):
    response = requests.get(f'https://pypi.org/pypi/{package}/json')
    latest_version = response.json()['info']['version']
    return latest_version


def geeup_version():
    vcheck = ob1.compareVersion(
        version_latest('geeup'),
        pkg_resources.get_distribution("geeup").version,
    )
    if vcheck == 1:
        print(
            "\n"
            + "========================================================================="
        )
        print(
            "Current version of geeup is {} upgrade to lastest version: {}".format(
                pkg_resources.get_distribution("geeup").version,
                version_latest('geeup'),
            )
        )
        print(
            "========================================================================="
        )
    elif vcheck == -1:
        print(
            "\n"
            + "========================================================================="
        )
        print(
            "Possibly running staging code {} compared to pypi release {}".format(
                pkg_resources.get_distribution("geeup").version,
                version_latest('geeup'),
            )
        )
        print(
            "========================================================================="
        )


geeup_version()

# Go to the readMe


def readme():
    try:
        a = webbrowser.open("https://samapriya.github.io/geeup/", new=2)
        if a == False:
            print("Your setup does not have a monitor to display the webpage")
            print(" Go to {}".format("https://samapriya.github.io/geeup/"))
    except Exception as e:
        logger.exception(e)


def read_from_parser(args):
    readme()


def rename(directory):
    file_list = [file for file in os.listdir(directory)]
    for i, file_original in enumerate(file_list):
        file_name, file_extension = os.path.splitext(file_original)
        string = re.sub(r'[^a-zA-Z0-9 _-]', r'', file_name)
        string = re.sub(r"\s+", "_", string)
        if file_original != string:
            print(f'Renaming {file_original} to {string}{file_extension}')
            os.rename(os.path.join(directory, file_original),
                      os.path.join(directory, f'{string}{file_extension}'))


def rename_from_parser(args):
    rename(directory=args.input)

# cookie setup


def cookie_setup():
    platform_info = platform.system().lower()
    if str(platform_info) == "linux" or str(platform_info) == "darwin":
        subprocess.check_call(["stty", "-icanon"])
    try:
        cookie_list = raw_input("Enter your Cookie List:  ")
    except Exception:
        cookie_list = input("Enter your Cookie List:  ")
    finally:
        with open("cookie_jar.json", "w") as outfile:
            json.dump(json.loads(cookie_list), outfile)
    time.sleep(3)
    if str(platform_info) == "windows":
        os.system("cls")
    elif str(platform_info) == "linux":
        os.system("clear")
        subprocess.check_call(["stty", "icanon"])
    elif str(platform_info) == "darwin":
        os.system("clear")
        subprocess.check_call(["stty", "icanon"])
    else:
        sys.exit('Operating system not supported')
    print("\n" + "Cookie Setup completed")


def cookie_setup_from_parser(args):
    cookie_setup()


suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]


def humansize(nbytes):
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = ("%.2f" % nbytes).rstrip("0").rstrip(".")
    return "%s %s" % (f, suffixes[i])


def quota(project):
    ee.Initialize()
    if project is not None:
        try:
            if not project.endswith("/"):
                project = project + "/"
            else:
                project = project
            project_detail = ee.data.getAsset(project)
            print("")
            if "sizeBytes" in project_detail["quota"]:
                print(
                    "Used {} of {}".format(
                        humansize(int(project_detail["quota"]["sizeBytes"])),
                        (humansize(
                            int(project_detail["quota"]["maxSizeBytes"]))),
                    )
                )
            else:
                print(
                    "Used 0 of {}".format(
                        humansize(int(project_detail["quota"]["maxSizeBytes"]))
                    )
                )
            if "assetCount" in project_detail["quota"]:
                print(
                    "Used {:,} assets of {:,} total".format(
                        int(project_detail["quota"]["assetCount"]),
                        int(project_detail["quota"]["maxAssetCount"]),
                    )
                )
            else:
                print(
                    "Used 0 assets of {:,} total".format(
                        int(project_detail["quota"]["maxAssetCount"])
                    )
                )
        except Exception as e:
            logger.exception(e)
    else:
        for roots in ee.data.getAssetRoots():
            quota = ee.data.getAssetRootQuota(roots["id"])
            print("")
            print(
                "Root assets path: {}".format(
                    roots["id"].replace(
                        "projects/earthengine-legacy/assets/", "")
                )
            )
            print(
                "Used {} of {}".format(
                    humansize(quota["asset_size"]["usage"]),
                    humansize(quota["asset_size"]["limit"]),
                )
            )
            print(
                "Used {:,} assets of {:,} total".format(
                    quota["asset_count"]["usage"], quota["asset_count"]["limit"]
                )
            )


def quota_from_parser(args):
    quota(project=args.project)


def zipshape_from_parser(args):
    zipshape(directory=args.input, export=args.output)


def getmeta_from_parser(args):
    getmeta(indir=args.input, mfile=args.metadata)


def upload_from_parser(args):
    upload(
        user=args.user,
        source_path=args.source,
        destination_path=args.dest,
        metadata_path=args.metadata,
        nodata_value=args.nodata,
        mask=args.mask,
        pyramiding=args.pyramids,
        overwrite=args.overwrite
    )


def tabup_from_parser(args):
    tabup(
        uname=args.user,
        dirc=args.source,
        destination=args.dest,
        x=args.x,
        y=args.y,
        overwrite=args.overwrite
    )


def tasks(state):
    ee.Initialize()
    if state is not None:
        task_bundle = []
        operations = [status
                      for status in ee.data.listOperations() if status["metadata"]["state"] == state]
        for operation in operations:
            task_id = operation['name'].split('/')[-1]
            description = operation['metadata']['description'].split(
                ':')[-1].strip().replace('"', '')
            op_type = operation['metadata']['type']
            attempt_count = str(operation['metadata']['attempt'])
            start = datetime.strptime(
                operation['metadata']["startTime"], "%Y-%m-%dT%H:%M:%S.%fZ")
            end = datetime.strptime(
                operation['metadata']["updateTime"], "%Y-%m-%dT%H:%M:%S.%fZ")
            time_difference = end-start
            item = {
                "task_id": task_id,
                "operation_type": op_type,
                "description/path": description,
                "time_difference": str(time_difference),
                "attempt": attempt_count
            }
            task_bundle.append(item)
        print(json.dumps(task_bundle, indent=2))
    else:
        statuses = ee.data.listOperations()
        st = []
        for status in statuses:
            st.append(status["metadata"]["state"])
        print(f"Tasks Running: {st.count('RUNNING')}")
        print(f"Tasks Pending: {st.count('PENDING')}")
        print(f"Tasks Completed: {st.count('SUCCEEDED')}")
        print(f"Tasks Failed: {st.count('FAILED')}")
        print(
            f"Tasks Cancelled: {st.count('CANCELLED') + st.count('CANCELLING')}")


def tasks_from_parser(args):
    tasks(state=args.state)


def cancel_tasks(tasks):
    ee.Initialize()
    if tasks == "all":
        try:
            print("Attempting to cancel all tasks")
            all_tasks = [
                task
                for task in ee.data.listOperations()
                if task["metadata"]["state"] == "RUNNING"
                or task["metadata"]["state"] == "PENDING"
            ]
            if len(all_tasks) > 0:
                for task in all_tasks:
                    ee.data.cancelOperation(task["name"])
                print(
                    "Request completed task ID or task type {} cancelled".format(
                        tasks)
                )
            elif len(all_tasks) == 0:
                print("No Running or Pending tasks found")
        except Exception as e:
            logger.exception(e)
    elif tasks == "running":
        try:
            print("Attempting to cancel running tasks")
            running_tasks = [
                task
                for task in ee.data.listOperations()
                if task["metadata"]["state"] == "RUNNING"
            ]
            if len(running_tasks) > 0:
                for task in running_tasks:
                    ee.data.cancelOperation(task["name"])
                print(
                    "Request completed task ID or task type: {} cancelled".format(
                        tasks)
                )
            elif len(running_tasks) == 0:
                print("No Running tasks found")
        except Exception as e:
            logger.exception(e)
    elif tasks == "pending":
        try:
            print("Attempting to cancel queued tasks or pending tasks")
            ready_tasks = [
                task
                for task in ee.data.listOperations()
                if task["metadata"]["state"] == "PENDING"
            ]
            if len(ready_tasks) > 0:
                for task in ready_tasks:
                    ee.data.cancelOperation(task["name"])
                print(
                    "Request completed task ID or task type: {} cancelled".format(
                        tasks)
                )
            elif len(ready_tasks) == 0:
                print("No Pending tasks found")
        except Exception as e:
            logger.exception(e)
    elif tasks is not None:
        try:
            print("Attempting to cancel task with given task ID {}".format(tasks))
            get_status = ee.data.getOperation(
                "projects/earthengine-legacy/operations/{}".format(tasks)
            )
            if (
                get_status["metadata"]["state"] == "RUNNING"
                or get_status["metadata"]["state"] == "PENDING"
            ):
                ee.data.cancelTask(task["id"])
                print(
                    "Request completed task ID or task type: {} cancelled".format(
                        tasks)
                )
            else:
                print("Task in status {}".format(
                    get_status["metadata"]["state"]))
        except Exception as e:
            print("No task found with given task ID {}".format(tasks))


def cancel_tasks_from_parser(args):
    cancel_tasks(tasks=args.tasks)


def delete(ids):
    try:
        print("Recursively deleting path: {}".format(ids))
        subprocess.call("earthengine rm -r " + ids)
    except Exception as e:
        logger.exception(e)


def delete_collection_from_parser(args):
    delete(args.id)


spacing = "                               "


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Simple Client for Earth Engine Uploads"
    )

    subparsers = parser.add_subparsers()

    parser_read = subparsers.add_parser(
        "readme", help="Go the web based geeup readme page"
    )
    parser_read.set_defaults(func=read_from_parser)

    parser_quota = subparsers.add_parser(
        "quota", help="Print Earth Engine storage and asset count quota"
    )
    optional_named = parser_quota.add_argument_group(
        "Optional named arguments")
    optional_named.add_argument(
        "--project",
        help="Project Name usually in format projects/project-name/assets/",
        default=None,
    )
    parser_quota.set_defaults(func=quota_from_parser)

    parser_rename = subparsers.add_parser(
        "rename",
        help="Renames filename to adhere to EE naming rules: Caution this is in place renaming",
    )
    required_named = parser_rename.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--input",
        help="Path to the input directory with all files to be uploaded",
        required=True,
    )
    parser_rename.set_defaults(func=rename_from_parser)

    parser_zipshape = subparsers.add_parser(
        "zipshape",
        help="Zips all shapefiles and subsidary files in folder into individual zip files",
    )
    required_named = parser_zipshape.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--input",
        help="Path to the input directory with all shape files",
        required=True,
    )
    required_named.add_argument(
        "--output",
        help="Destination folder Full path where shp, shx, prj and dbf files if present will be zipped and stored",
        required=True,
    )
    parser_zipshape.set_defaults(func=zipshape_from_parser)

    parser_getmeta = subparsers.add_parser(
        "getmeta", help="Creates a generalized metadata for rasters in folder"
    )
    required_named = parser_getmeta.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--input",
        help="Path to the input directory with all raster files",
        required=True,
    )
    required_named.add_argument(
        "--metadata", help="Full path to export metadata.csv file", required=True
    )
    parser_getmeta.set_defaults(func=getmeta_from_parser)

    parser_cookie_setup = subparsers.add_parser(
        "cookie_setup",
        help="Setup cookies to be used for upload",
    )
    parser_cookie_setup.set_defaults(func=cookie_setup_from_parser)

    parser_upload = subparsers.add_parser(
        "upload", help="Batch Image Uploader for uploading tif files to a GEE collection"
    )
    required_named = parser_upload.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--source", help="Path to the directory with images for upload.", required=True
    )
    required_named.add_argument(
        "--dest",
        help="Destination. Full path for upload to Google Earth Engine image collection, e.g. users/pinkiepie/myponycollection",
        required=True,
    )
    required_named.add_argument(
        "-m", "--metadata", help="Path to CSV with metadata.", required=True
    )
    optional_named = parser_upload.add_argument_group(
        "Optional named arguments")
    optional_named.add_argument(
        "--nodata",
        type=int,
        help="The value to burn into the raster as NoData (missing data)",
    )
    optional_named.add_argument(
        "--mask",
        default=False,
        choices=('True', 'False', 't', 'f'),
        help="Binary to use last band for mask True or False",
    )
    optional_named.add_argument(
        "--pyramids",
        help="Pyramiding Policy, MEAN, MODE, MIN, MAX, SAMPLE",
    )
    optional_named.add_argument(
        "--overwrite",
        help="Default is No but you can pass yes or y",
    )
    required_named.add_argument(
        "-u", "--user", help="Google account name (gmail address)."
    )

    parser_upload.set_defaults(func=upload_from_parser)

    parser_tabup = subparsers.add_parser(
        "tabup", help="Batch Table Uploader for uploading shapefiles/CSVs to a GEE folder"
    )
    required_named = parser_tabup.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--source",
        help="Path to the directory with zipped files or CSV files for upload.",
        required=True,
    )
    required_named.add_argument(
        "--dest",
        help="Destination. Full path for upload to Google Earth Engine folder, e.g. users/pinkiepie/myfolder",
        required=True,
    )
    required_named.add_argument(
        "-u", "--user", help="Google account name (gmail address)."
    )
    optional_named = parser_tabup.add_argument_group(
        "Optional named arguments")
    optional_named.add_argument(
        "--x",
        help="Column with longitude value",
    )
    optional_named.add_argument(
        "--y",
        help="Column with latitude value",
    )
    optional_named.add_argument(
        "--overwrite",
        help="Default is No but you can pass yes or y",
    )
    parser_tabup.set_defaults(func=tabup_from_parser)

    parser_tasks = subparsers.add_parser(
        "tasks",
        help="Queries current task status [completed,running,ready,failed,cancelled]",
    )
    optional_named = parser_tasks.add_argument_group(
        "Optional named arguments")
    optional_named.add_argument(
        "--state",
        help="Query by state type SUCCEEDED|PENDING|RUNNING|FAILED",
    )
    parser_tasks.set_defaults(func=tasks_from_parser)

    parser_cancel = subparsers.add_parser(
        "cancel", help="Cancel all, running or ready tasks or task ID"
    )
    required_named = parser_cancel.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--tasks",
        help="You can provide tasks as running or pending or all or even a single task id",
        required=True,
        default=None,
    )
    parser_cancel.set_defaults(func=cancel_tasks_from_parser)

    parser_delete = subparsers.add_parser(
        "delete",
        help="Deletes collection and all items inside. Supports Unix-like wildcards.",
    )
    parser_delete.add_argument(
        "id",
        help="Full path to asset for deletion. Recursively removes all folders, collections and images.",
    )
    parser_delete.set_defaults(func=delete_collection_from_parser)

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.error("too few arguments")
    func(args)


if __name__ == "__main__":
    main()
