from __future__ import print_function

__copyright__ = """

    Copyright 2016 Lukasz Tracewski

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

__Modifications_copyright__ = """

    Copyright 2019 Samapriya Roy

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

"""
Modifications to file:
- Uses selenium based upload instead of simple login
- Removed multipart upload
- Uses polling
"""

import ast
import csv
import getpass
import glob
import logging
import os
import sys
import platform
import time
import json
import requests
import ee
import pandas as pd
import subprocess
import retrying
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from requests_toolbelt import MultipartEncoder
from .metadata_loader import load_metadata_from_csv, validate_metadata_from_csv

os.chdir(os.path.dirname(os.path.realpath(__file__)))
lp = os.path.dirname(os.path.realpath(__file__))
sys.path.append(lp)


slist = []


def upload(
    user,
    source_path,
    method,
    pyramiding,
    destination_path,
    metadata_path=None,
    nodata_value=None,
    bucket_name=None,
):

    ee.Initialize()

    __verify_path_for_upload(destination_path)

    path = os.path.join(os.path.expanduser(source_path), "*.tif")
    all_images_paths = glob.glob(path)
    if len(all_images_paths) == 0:
        print("%s does not contain any tif images.", path)
        sys.exit(1)

    metadata = load_metadata_from_csv(metadata_path) if metadata_path else None

    if user and method is not None:
        password = None
        google_session = __get_google_auth_session(user, password, method)
    elif user is not None and method is None:
        password = getpass.getpass()
        google_session = __get_google_auth_session(user, password, method)

    __create_image_collection(destination_path)

    images_for_upload_path = __find_remaining_assets_for_upload(
        all_images_paths, destination_path
    )
    no_images = len(images_for_upload_path)

    if no_images == 0:
        print("No images found that match %s. Exiting...", path)
        sys.exit(1)

    for current_image_no, image_path in enumerate(images_for_upload_path):
        print(
            "Processing image "
            + str(current_image_no + 1)
            + " out of "
            + str(no_images)
            + ": "
            + str(image_path)
        )
        filename = __get_filename_from_path(path=image_path)

        destination_path = ee.data.getAsset(destination_path + "/")["name"]
        asset_full_path = destination_path + "/" + filename

        if metadata and not filename in metadata:
            print(
                "No metadata exists for image "
                + str(filename)
                + " : it will not be ingested"
            )
            continue

        properties = metadata[filename] if metadata else None
        try:
            if user is not None:
                gsid = __upload_file_gee(session=google_session, file_path=image_path)

            df = pd.read_csv(metadata_path)
            dd = (df.applymap(type) == str).all(0)
            for ind, val in dd.iteritems():
                if val == True:
                    slist.append(ind)
            intcol = list(df.select_dtypes(include=["int64"]).columns)
            floatcol = list(df.select_dtypes(include=["float64"]).columns)
            with open(metadata_path, "r") as f:
                reader = csv.DictReader(f, delimiter=",")
                for i, line in enumerate(reader):
                    if line["id_no"] == os.path.basename(image_path).split(".")[0]:
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
                            if len(start)==12:
                                start=int(round(int(start)*0.001))
                            else:
                                start = int(str(start)[:10])
                            j.pop("system:time_start")
                        elif "system:time_start" not in j:
                            start = None
                        if "system:time_end" in j:
                            end = str(j["system:time_end"])
                            if len(end)==12:
                                end=int(round(int(end)*0.001))
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
                        # print(json.dumps(main_payload))
                        with open(os.path.join(lp, "data.json"), "w") as outfile:
                            json.dump(main_payload, outfile)
                        subprocess.call(
                            "earthengine upload image --manifest "
                            + '"'
                            + os.path.join(lp, "data.json")
                            + '"',
                            shell=True,
                            stdout=subprocess.PIPE,
                        )
        except Exception as e:
            print(e)
            print("Upload of " + str(filename) + " has failed.")


def __verify_path_for_upload(path):
    folder = path[: path.rfind("/")]
    response = ee.data.getInfo(folder)
    if not response:
        print(
            str(path)
            + " is not a valid destination. Make sure full path is provided e.g. users/user/nameofcollection "
            "or projects/myproject/myfolder/newcollection and that you have write access there."
        )
        sys.exit(1)


def __find_remaining_assets_for_upload(path_to_local_assets, path_remote):
    local_assets = [__get_filename_from_path(path) for path in path_to_local_assets]
    if __collection_exist(path_remote):
        remote_assets = __get_asset_names_from_collection(path_remote)
        if len(remote_assets) > 0:
            assets_left_for_upload = set(local_assets) - set(remote_assets)
            if len(assets_left_for_upload) == 0:
                print(
                    "Collection already exists and contains all assets provided for upload. Exiting ..."
                )
                sys.exit(1)

            print(
                "Collection already exists. "
                + str(len(assets_left_for_upload))
                + " assets left for upload to "
                + str(path_remote)
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


@retrying.retry(
    retry_on_exception=retry_if_ee_error,
    wait_exponential_multiplier=1000,
    wait_exponential_max=4000,
    stop_max_attempt_number=3,
)
def __start_ingestion_task(asset_request):
    task_id = ee.data.newTaskId(1)[0]
    _ = ee.data.startIngestion(task_id, asset_request)
    return task_id


def __validate_metadata(path_for_upload, metadata_path):
    validation_result = validate_metadata_from_csv(metadata_path)
    keys_in_metadata = {result.keys for result in validation_result}
    images_paths = glob.glob(os.path.join(path_for_upload, "*.tif*"))
    keys_in_data = {__get_filename_from_path(path) for path in images_paths}
    missing_keys = keys_in_data - keys_in_metadata

    if missing_keys:
        print(
            str(
                len(missing_keys)
                + " images does not have a corresponding key in metadata"
            )
        )
        print("\n".join(e for e in missing_keys))
    else:
        print("All images have metadata available")

    if not validation_result.success:
        print('Validation finished with errors. Type "y" to continue, default NO: ')
        choice = input().lower()
        if choice not in ["y", "yes"]:
            print("Application will terminate")
            exit(1)


def __extract_metadata_for_image(filename, metadata):
    if filename in metadata:
        return metadata[filename]
    else:
        print("Metadata for " + str(filename) + " not found")
        return None


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


def __get_google_auth_session(username, password, method):
    ee.Initialize()
    if method is not None and method == "cookies":
        platform_info = platform.system().lower()
        if str(platform.system().lower()) == "linux":
            subprocess.check_call(["stty", "-icanon"])
        if not os.path.exists("cookie_jar.json"):
            try:
                cookie_list = raw_input("Enter your Cookie List:  ")
            except Exception as e:
                cookie_list = input("Enter your Cookie List:  ")
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
                        "Cookies Expired | Enter your Cookie List:  "
                    )
                except Exception as e:
                    cookie_list = input("Cookies Expired | Enter your Cookie List:  ")
                with open("cookie_jar.json", "w") as outfile:
                    json.dump(json.loads(cookie_list), outfile)
                    cookie_list = json.loads(cookie_list)
        time.sleep(5)
        if str(platform.system().lower()) == "windows":
            os.system("cls")
        elif str(platform.system().lower()) == "linux":
            os.system("clear")
        elif str(platform.system().lower()) == "darwin":
            os.system("clear")
        else:
            pass
        session = requests.Session()
        for cookies in cookie_list:
            session.cookies.set(cookies["name"], cookies["value"])
        response = session.get(
            "https://code.earthengine.google.com/assets/upload/geturl"
        )
        if (
            response.status_code == 200
            and ast.literal_eval(response.text)["url"] is not None
        ):
            return session
        else:
            print(response.status_code, response.text)
    else:
        options = Options()
        options.add_argument("-headless")
        uname = str(username)
        passw = str(password)
        if os.name == "nt":
            driver = Firefox(
                executable_path=os.path.join(lp, "geckodriver.exe"), options=options
            )
        else:
            driver = Firefox(
                executable_path=os.path.join(lp, "geckodriver"), options=options
            )
        try:
            # Using stackoverflow for third-party login & redirect
            driver.get(
                "https://stackoverflow.com/users/signup?ssrc=head&returnurl=%2fusers%2fstory%2fcurrent%27"
            )
            time.sleep(5)
            driver.find_element_by_xpath('//*[@id="openid-buttons"]/button[1]').click()
            time.sleep(5)
            driver.find_element_by_xpath('//input[@type="email"]').send_keys(uname)
            driver.find_element_by_xpath("//div[@id='identifierNext']").click()
            time.sleep(5)
            driver.find_element_by_xpath('//input[@type="password"]').send_keys(passw)
            driver.find_element_by_xpath('//*[@id="passwordNext"]').click()
            time.sleep(5)
            driver.get("https://code.earthengine.google.com")
            time.sleep(8)
        except Exception as e:
            print(e)
            driver.close()
            sys.exit("Failed to setup & use selenium")
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])
        driver.close()
        return session


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
def __upload_file_gcs(storage_client, bucket_name, image_path):
    bucket = storage_client.get_bucket(bucket_name)
    blob_name = __get_filename_from_path(path=image_path)
    blob = bucket.blob(blob_name)

    blob.upload_from_filename(image_path)

    url = "gs://" + bucket_name + "/" + blob_name

    return url


def __get_filename_from_path(path):
    return os.path.splitext(os.path.basename(os.path.normpath(path)))[0]


def __get_number_of_running_tasks():
    return len([task for task in ee.data.getTaskList() if task["state"] == "RUNNING"])


def __wait_for_tasks_to_complete(waiting_time, no_allowed_tasks_running):
    tasks_running = __get_number_of_running_tasks()
    while tasks_running > no_allowed_tasks_running:
        logging.info(
            "Number of running tasks is %d. Sleeping for %d s until it goes down to %d",
            tasks_running,
            waiting_time,
            no_allowed_tasks_running,
        )
        time.sleep(waiting_time)
        tasks_running = __get_number_of_running_tasks()


def __collection_exist(path):
    return True if ee.data.getInfo(path) else False


def __create_image_collection(full_path_to_collection):
    if __collection_exist(full_path_to_collection):
        print("Collection " + str(full_path_to_collection) + " already exists")
    else:
        ee.data.createAsset(
            {"type": ee.data.ASSET_TYPE_IMAGE_COLL}, full_path_to_collection
        )
        print("New collection " + str(full_path_to_collection) + " created")


def __get_asset_names_from_collection(collection_path):
    assets_list = ee.data.getList(params={"id": collection_path})
    assets_names = [os.path.basename(asset["id"]) for asset in assets_list]
    return assets_names
