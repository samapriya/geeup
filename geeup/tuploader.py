__copyright__ = """

    Copyright 2022 Samapriya Roy

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
import json
import logging
import os
import platform
import subprocess
import sys
import time

import ee
import requests
from cerberus import Validator
from cerberus.errors import BasicErrorHandler
from natsort import natsorted
from requests_toolbelt import MultipartEncoder

lp = os.path.dirname(os.path.realpath(__file__))
sys.path.append(lp)

table_exists = []
gee_table_exists = []

logging.basicConfig(
    format="%(asctime)s %(levelname)-4s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class CustomErrorHandler(BasicErrorHandler):
    def __init__(self, schema):
        self.custom_defined_schema = schema

    def _format_message(self, field, error):
        print("")
        return "GEE file name & path cannot have spaces & can only have letters, numbers, hiphens and underscores"


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


def get_auth_session(uname):
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
        pass
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


def tabup(dirc, uname, destination, x, y):
    ee.Initialize()
    schema = {"folder_path": {
        "type": "string", "regex": "^[a-zA-Z0-9/_-]+$"}}
    folder_validate = {"folder_path": destination}
    v = Validator(schema, error_handler=CustomErrorHandler(schema))
    if v.validate(folder_validate, schema) is False:
        sys.exit(v.errors)

    session = get_auth_session(uname)
    for (root, directories, files) in os.walk(dirc):
        for filename in files:
            if filename.endswith(".zip"):
                table_exists.append(filename.split(".zip")[0])
                base_ext = ".zip"
            elif filename.endswith(".csv"):
                table_exists.append(filename.split(".csv")[0])
                base_ext = ".csv"
    try:
        destination_info = ee.data.getAsset(destination + "/")
        full_path_to_collection = destination_info["name"]
        if destination_info["name"] and destination_info["type"].lower() == "folder":
            print("Folder exists: {}".format(destination_info["id"]))
            children = ee.data.listAssets({"parent": full_path_to_collection})
            for child in children["assets"]:
                gee_table_exists.append(child["id"].split("/")[-1])
    except Exception:
        full_path_to_collection = (
            destination.rsplit("/", 1)[0] + "/" + destination.split("/")[-1]
        )
        print("Creating a folder {}".format(full_path_to_collection))
        try:
            ee.data.createAsset(
                {"type": ee.data.ASSET_TYPE_FOLDER_CLOUD}, full_path_to_collection
            )
        except Exception:
            ee.data.createAsset(
                {"type": ee.data.ASSET_TYPE_FOLDER}, full_path_to_collection
            )
        destination_info = ee.data.getAsset(destination + "/")
        full_path_to_collection = destination_info["name"]

    tasked_assets = []
    status = ["RUNNING", "PENDING"]
    for task in ee.data.listOperations():
        if (
            task["metadata"]["type"] == "INGEST_TABLE"
            and task["metadata"]["state"] in status
        ):
            tasked_assets.append(
                task["metadata"]["description"]
                .split(":")[-1]
                .split("/")[-1]
                .replace('"', "")
            )
    diff_set = set(table_exists).difference(
        set(gee_table_exists), set(tasked_assets))
    if len(diff_set) > 0:
        print(
            f"Total of {len(diff_set)} assets remaining : {len(set(gee_table_exists))} assets with {len(set(tasked_assets))} tasks running or submitted"
        )
        status = ["RUNNING", "PENDING"]
        task_count = len(
            [
                task
                for task in ee.data.listOperations()
                if task["metadata"]["state"] in status
            ]
        )
        while task_count >= 2500:
            logging.info(
                f"Total tasks running or submitted {task_count}: waiting for 5 minutes"
            )
            time.sleep(300)
        auth_check = session.get(
            "https://code.earthengine.google.com/assets/upload/geturl"
        )
        if (
            auth_check.status_code == 200
            and auth_check.headers.get("content-type").split(";")[0]
            == "application/json"
        ):
            try:
                file_count = len(diff_set)
                for i, item in enumerate(natsorted(diff_set)):
                    full_path_to_table = os.path.join(root, item + base_ext)
                    file_name = item + base_ext
                    file_name = bytes(
                        file_name, "utf-8").decode("utf-8", "ignore")
                    r = session.get(
                        "https://code.earthengine.google.com/assets/upload/geturl"
                    )
                    d = ast.literal_eval(r.text)
                    upload_url = d["url"]
                    with open(full_path_to_table, "rb") as f:
                        try:
                            if base_ext == ".zip":
                                m = MultipartEncoder(
                                    fields={"zip_file": (file_name, f)}
                                )
                                resp = session.post(
                                    upload_url,
                                    data=m,
                                    headers={"Content-Type": m.content_type},
                                )
                                gsid = resp.json()[0]
                                asset_full_path = (
                                    full_path_to_collection
                                    + "/"
                                    + bytes(item, "utf-8")
                                    .decode("utf-8", "ignore")
                                    .split(".")[0]
                                )
                                main_payload = {
                                    "name": asset_full_path,
                                    "sources": [
                                        {
                                            "charset": "UTF-8",
                                            "maxErrorMeters": 1,
                                            "maxVertices": 1000000,
                                            "uris": [gsid],
                                        }
                                    ],
                                }
                                schema = {
                                    "asset_path": {
                                        "type": "string",
                                        "regex": "^[a-zA-Z0-9/_-]+$",
                                    }
                                }
                                asset_validate = {
                                    "asset_path": asset_full_path}
                                v = Validator(
                                    schema, error_handler=CustomErrorHandler(schema))
                                if v.validate(asset_validate, schema) is False:
                                    print(v.errors)
                                    raise Exception
                                with open(
                                    os.path.join(lp, "data.json"), "w"
                                ) as outfile:
                                    json.dump(main_payload, outfile)
                                output = subprocess.check_output(
                                    "earthengine upload table --manifest "
                                    + '"'
                                    + os.path.join(lp, "data.json")
                                    + '"',
                                    shell=True,
                                )
                                logging.info(
                                    f"Ingesting {i+1} of {file_count} {str(os.path.basename(asset_full_path))} with Task Id: {output.decode('ascii').strip().split(' ')[-1]}"
                                )
                            elif base_ext == ".csv":
                                m = MultipartEncoder(
                                    fields={"csv_file": (file_name, f)}
                                )
                                resp = session.post(
                                    upload_url,
                                    data=m,
                                    headers={"Content-Type": m.content_type},
                                )
                                gsid = resp.json()[0]
                                asset_full_path = (
                                    full_path_to_collection +
                                    "/" + item.split(".")[0]
                                )
                                if x and y is not None:
                                    main_payload = {
                                        "name": asset_full_path,
                                        "sources": [
                                            {
                                                "charset": "UTF-8",
                                                "maxErrorMeters": 1,
                                                "uris": [gsid],
                                                "xColumn": x,
                                                "yColumn": y,
                                            }
                                        ],
                                    }
                                else:
                                    main_payload = {
                                        "name": asset_full_path,
                                        "sources": [
                                            {
                                                "charset": "UTF-8",
                                                "maxErrorMeters": 1,
                                                "uris": [gsid],
                                            }
                                        ],
                                    }
                                schema = {
                                    "asset_path": {
                                        "type": "string",
                                        "regex": "^[a-zA-Z0-9/_-]+$",
                                    }
                                }
                                asset_validate = {
                                    "asset_path": asset_full_path}
                                v = Validator(
                                    schema, error_handler=CustomErrorHandler(schema))
                                if v.validate(asset_validate, schema) is False:
                                    print(v.errors)
                                    raise Exception
                                with open(
                                    os.path.join(lp, "data.json"), "w"
                                ) as outfile:
                                    json.dump(main_payload, outfile)
                                manifest_file = os.path.join(lp, "data.json")
                                output = subprocess.check_output(
                                    f"earthengine upload table --manifest {manifest_file}",
                                    shell=True,
                                )
                                logging.info(
                                    f"Ingesting {i+1} of {file_count} {str(os.path.basename(asset_full_path))} with Task Id: {output.decode('ascii').strip().split(' ')[-1]}"
                                )
                        except Exception as error:
                            print(error)
                            print(f"Failed to ingest {asset_full_path}")
            except Exception as error:
                print(error)
            except (KeyboardInterrupt, SystemExit) as e:
                sys.exit("Program escaped by User")
        else:
            print("Authentication Failed for GEE account")
    elif len(diff_set) == 0:
        print(
            f"All assets already ingested or running : {len(set(gee_table_exists))} assets with {len(set(tasked_assets))} tasks running or submitted"
        )


# authenticate(dirc=r'C:\planet_demo\grid')
