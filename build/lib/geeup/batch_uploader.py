from __future__ import print_function

__copyright__ = """

    Copyright 2023 Samapriya Roy

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

import ast
import csv
import glob
import json
import logging
import os
import platform
import subprocess
import sys
import time

import ee
import pandas as pd
import requests
import retrying
from cerberus import Validator
from cerberus.errors import BasicErrorHandler
from natsort import natsorted
from requests_toolbelt import MultipartEncoder

from .metadata_loader import load_metadata_from_csv

os.chdir(os.path.dirname(os.path.realpath(__file__)))
lp = os.path.dirname(os.path.realpath(__file__))
sys.path.append(lp)


slist = []


class CustomErrorHandler(BasicErrorHandler):
    def __init__(self, schema):
        self.custom_defined_schema = schema

    def _format_message(self, field, error):
        print("")
        return "GEE file name & path cannot have spaces & can only have letters, numbers, hyphens and underscores"


def task_counter():
    ee.Initialize()
    status = ["RUNNING", "PENDING"]
    task_count = len(
        [
            task
            for task in ee.data.listOperations()
            if task["metadata"]["state"] in status
        ]
    )
    return task_count


def upload(
    user,
    source_path,
    pyramiding,
    mask,
    destination_path,
    metadata_path=None,
    nodata_value=None,
    overwrite=None,
):
    schema = {"collection_path": {
        "type": "string", "regex": "^[a-zA-Z0-9/_-]+$"}}
    collection_validate = {"collection_path": destination_path}
    v = Validator(schema, error_handler=CustomErrorHandler(schema))
    if v.validate(collection_validate, schema) is False:
        sys.exit(v.errors)

    ee.Initialize()

    logging.basicConfig(
        format="%(asctime)s %(levelname)-4s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    path = os.path.join(os.path.expanduser(source_path), "*.tif")
    all_images_paths = glob.glob(path)
    if len(all_images_paths) == 0:
        print("%s does not contain any tif images.", path)
        sys.exit(1)

    metadata = load_metadata_from_csv(metadata_path) if metadata_path else None

    google_session = __get_google_auth_session(user)

    __create_image_collection(destination_path)

    images_for_upload_path = __find_remaining_assets_for_upload(
        all_images_paths, destination_path, overwrite
    )
    no_images = len(images_for_upload_path)

    if no_images == 0:
        print("No images found that match %s. Exiting...", path)
        sys.exit(1)
    file_count = len(images_for_upload_path)
    for current_image_no, image_path in enumerate(natsorted(images_for_upload_path)):
        # logging.info(
        #     f"Processing image {current_image_no + 1} out of {no_images} : {image_path}"
        # )
        task_count = task_counter()
        while task_count >= 2800:
            logging.info(
                f"Total tasks running or submitted {task_count}: waiting for 5 minutes"
            )
            time.sleep(300)
            task_count = task_counter()
        filename = __get_filename_from_path(path=image_path)

        destination_path = ee.data.getAsset(destination_path + "/")["name"]
        asset_full_path = destination_path + "/" + filename

        if metadata and not filename in metadata:
            print(
                f"No metadata exists for image: {filename} ==>it will not be ingested"
            )
            continue

        properties = metadata[filename] if metadata else None
        try:
            if user is not None:
                gsid = __upload_file_gee(
                    session=google_session, file_path=image_path)

            df = pd.read_csv(metadata_path)
            dd = (df.applymap(type) == str).all(0)
            for ind, val in dd.items():
                if val == True:
                    slist.append(ind)
            intcol = list(df.select_dtypes(include=["int64"]).columns)
            floatcol = list(df.select_dtypes(include=["float64"]).columns)
            with open(metadata_path, "r") as f:
                reader = csv.DictReader(f, delimiter=",")
                for i, line in enumerate(reader):
                    if line["id_no"] == os.path.basename(image_path).split(".tif")[0]:
                        j = {}
                        for integer in intcol:
                            value = integer
                            j[value] = int(line[integer])
                        for s in slist:
                            value = s
                            j[value] = str(line[s])
                        for f in floatcol:
                            value = f
                            j[value] = float(line[f])
                        # j['id']=destination_path+'/'+line["id_no"]
                        # j['tilesets'][0]['sources'][0]['primaryPath']=gsid
                        if "system:time_start" in j:
                            start = str(j["system:time_start"])
                            if len(start) == 12:
                                start = int(round(int(start) * 0.001))
                            else:
                                start = int(str(start)[:10])
                            j.pop("system:time_start")
                        elif "system:time_start" not in j:
                            start = None
                        if "system:time_end" in j:
                            end = str(j["system:time_end"])
                            if len(end) == 12:
                                end = int(round(int(end) * 0.001))
                            else:
                                end = int(str(end)[:10])
                            j.pop("system:time_end")
                        elif "system:time_end" not in j:
                            end = None
                        if pyramiding is not None:
                            pyramidingPolicy = pyramiding.upper()
                        else:
                            pyramidingPolicy = "MEAN"
                        json_data = json.dumps(j)
                        main_payload = {
                            "name": asset_full_path,
                            "pyramidingPolicy": pyramidingPolicy,
                            "tilesets": [{"sources": [{"uris": gsid}]}],
                            "start_time": {"seconds": ""},
                            "end_time": {"seconds": ""},
                            "properties": j,
                            "missing_data": {"values": [nodata_value]},
                            "maskBands": {"bandIds": [], "tilesetId": ''}
                        }
                        if start is not None:
                            main_payload["start_time"]["seconds"] = start
                        else:
                            main_payload.pop("start_time")
                        if end is not None:
                            main_payload["end_time"]["seconds"] = end
                        else:
                            main_payload.pop("end_time")
                        if nodata_value is None:
                            main_payload.pop("missing_data")
                        if bool(mask) is False:
                            main_payload.pop("maskBands")

                        # print(json.dumps(main_payload, indent=2))
                        schema = {
                            "asset_path": {
                                "type": "string",
                                "regex": "^[a-zA-Z0-9/_-]+$",
                            }
                        }
                        asset_validate = {"asset_path": asset_full_path}
                        v = Validator(
                            schema, error_handler=CustomErrorHandler(schema))
                        if v.validate(asset_validate, schema) is False:
                            print(v.errors)
                            raise Exception
                        request_id = ee.data.newTaskId()[0]
                        check_list = ['yes', 'y']
                        if overwrite is not None and overwrite.lower() in check_list:
                            output = ee.data.startIngestion(
                                request_id, main_payload, allow_overwrite=True)
                        else:
                            output = ee.data.startIngestion(
                                request_id, main_payload, allow_overwrite=False)
                        logging.info(
                            f"Ingesting {current_image_no+1} of {file_count} {str(os.path.basename(asset_full_path))} with Task Id: {output['id']} & status {output['started']}"
                        )
        except Exception as error:
            print(error)
            print("Upload of " + str(filename) + " has failed.")
        except (KeyboardInterrupt, SystemExit) as error:
            sys.exit("Program escaped by User")


def __find_remaining_assets_for_upload(path_to_local_assets, path_remote, overwrite):
    local_assets = [__get_filename_from_path(
        path) for path in path_to_local_assets]
    if __collection_exist(path_remote):
        check_list = ['yes', 'y']
        if overwrite is not None and overwrite.lower() in check_list:
            return path_to_local_assets
        else:
            remote_assets = __get_asset_names_from_collection(path_remote)
            tasked_assets = []
            status = ["RUNNING", "PENDING"]
            for task in ee.data.listOperations():
                if (
                    task["metadata"]["type"] == "INGEST_IMAGE"
                    and task["metadata"]["state"] in status
                ):
                    tasked_assets.append(
                        task["metadata"]["description"]
                        .split(":")[-1]
                        .split("/")[-1]
                        .replace('"', "")
                    )
            if len(remote_assets) >= 0:
                assets_left_for_upload = set(local_assets).difference(
                    set(remote_assets), set(tasked_assets)
                )
                if len(assets_left_for_upload) == 0:
                    print(
                        f"All assets already ingested or running : {len(set(remote_assets))} assets ingested with {len(set(tasked_assets))} tasks running or submitted"
                    )
                    sys.exit(1)
                elif len(assets_left_for_upload) > 0:
                    print(
                        f"Total of {len(assets_left_for_upload)} assets remaining : Total of {len(set(remote_assets))} already in collection with {len(set(tasked_assets))} associated tasks running or submitted"
                    )

                assets_left_for_upload_full_path = [
                    path
                    for path in path_to_local_assets
                    if __get_filename_from_path(path) in assets_left_for_upload
                ]
                return assets_left_for_upload_full_path

    return path_to_local_assets


def retry_if_ee_error(exception):
    return isinstance(exception, ee.EEException)


def cookie_check(cookie_list):
    cook_list = []
    for items in cookie_list:
        cook_list.append("{}={}".format(items["name"], items["value"]))
    cookie = "; ".join(cook_list)
    headers = {"cookie": cookie}
    response = requests.get(
        "https://code.earthengine.google.com/assets/upload/geturl", headers=headers
    )
    if (
        response.status_code == 200
        and response.headers.get("content-type").split(";")[0] == "application/json"
    ):
        return True
    else:
        return False


def __get_google_auth_session(username):
    ee.Initialize()
    platform_info = platform.system().lower()
    if str(platform_info) == "linux" or str(platform_info) == "darwin":
        subprocess.check_call(["stty", "-icanon"])
    if not os.path.exists("cookie_jar.json"):
        try:
            cookie_list = raw_input("Enter your Cookie List:  ")
        except Exception:
            cookie_list = input("Enter your Cookie List:  ")
        finally:
            with open("cookie_jar.json", "w") as outfile:
                json.dump(json.loads(cookie_list), outfile)
        cookie_list = json.loads(cookie_list)
    elif os.path.exists("cookie_jar.json"):
        with open("cookie_jar.json") as json_file:
            cookie_list = json.load(json_file)
        if cookie_check(cookie_list) is True:
            print("Using saved Cookies")
            cookie_list = cookie_list
        elif cookie_check(cookie_list) is False:
            try:
                cookie_list = raw_input(
                    "Cookies Expired | Enter your Cookie List:  ")
            except Exception:
                cookie_list = input(
                    "Cookies Expired | Enter your Cookie List:  ")
            finally:
                with open("cookie_jar.json", "w") as outfile:
                    json.dump(json.loads(cookie_list), outfile)
                    cookie_list = json.loads(cookie_list)
    time.sleep(5)
    if str(platform.system().lower()) == "windows":
        os.system("cls")
    elif str(platform.system().lower()) == "linux":
        os.system("clear")
        subprocess.check_call(["stty", "icanon"])
    elif str(platform.system().lower()) == "darwin":
        os.system("clear")
        subprocess.check_call(["stty", "icanon"])
    else:
        sys.exit(f"Operating system is not supported")
    session = requests.Session()
    for cookies in cookie_list:
        session.cookies.set(cookies["name"], cookies["value"])
    response = session.get(
        "https://code.earthengine.google.com/assets/upload/geturl")
    if (
        response.status_code == 200
        and ast.literal_eval(response.text)["url"] is not None
    ):
        return session
    else:
        print(response.status_code, response.text)


def __get_upload_url(session):
    r = session.get("https://code.earthengine.google.com/assets/upload/geturl")
    try:
        d = ast.literal_eval(r.text)
        return d["url"]
    except Exception as e:
        print(e)


@retrying.retry(
    retry_on_exception=retry_if_ee_error,
    wait_exponential_multiplier=1000,
    wait_exponential_max=4000,
    stop_max_attempt_number=3,
)
def __upload_file_gee(session, file_path):
    with open(file_path, "rb") as f:
        file_name = os.path.basename(file_path)
        upload_url = __get_upload_url(session)
        files = {"file": f}
        m = MultipartEncoder(fields={"image_file": (file_name, f)})
        try:
            resp = session.post(
                upload_url, data=m, headers={"Content-Type": m.content_type}
            )
            gsid = resp.json()[0]
            return gsid
        except Exception as e:
            print(e)


@retrying.retry(
    retry_on_exception=retry_if_ee_error,
    wait_exponential_multiplier=1000,
    wait_exponential_max=4000,
    stop_max_attempt_number=3,
)
def __get_filename_from_path(path):
    return os.path.splitext(os.path.basename(os.path.normpath(path)))[0]


def __get_number_of_running_tasks():
    return len([task for task in ee.data.getTaskList() if task["state"] == "RUNNING"])


def __collection_exist(path):
    return True if ee.data.getInfo(path) else False


def __create_image_collection(full_path_to_collection):
    if __collection_exist(full_path_to_collection):
        print("Collection " + str(full_path_to_collection) + " already exists")
    else:
        print("Collection does not exist: Creating {}".format(
            full_path_to_collection))
        try:
            ee.data.createAsset(
                {"type": ee.data.ASSET_TYPE_IMAGE_COLL_CLOUD}, full_path_to_collection
            )
        except Exception:
            ee.data.createAsset(
                {"type": ee.data.ASSET_TYPE_IMAGE_COLL}, full_path_to_collection
            )


def __get_asset_names_from_collection(collection_path):
    assets_list = ee.data.getList(params={"id": collection_path})
    assets_names = [os.path.basename(asset["id"]) for asset in assets_list]
    return assets_names
