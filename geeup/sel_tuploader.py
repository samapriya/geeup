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

import requests
import ast
import ee
import sys
import json
import platform
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from requests_toolbelt import MultipartEncoder
import time
import os
import getpass
import subprocess

lp = os.path.dirname(os.path.realpath(__file__))
sys.path.append(lp)

table_exists = []
gee_table_exists = []


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


def get_auth_session(method, uname):
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
        passw = getpass.getpass()
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


def seltabup(dirc, uname, destination, method, x, y):
    ee.Initialize()
    session = get_auth_session(method, uname)
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
    except Exception as e:
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
    diff_set = set(table_exists) - set(gee_table_exists)
    if len(diff_set) != 0:
        auth_check = session.get(
            "https://code.earthengine.google.com/assets/upload/geturl"
        )
        if (
            auth_check.status_code == 200
            and auth_check.headers.get("content-type").split(";")[0]
            == "application/json"
        ):
            try:
                i = 1
                file_count = len(diff_set)
                for item in list(diff_set):
                    full_path_to_table = os.path.join(root, item + base_ext)
                    file_name = item + base_ext
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
                                    full_path_to_collection + "/" + item.split(".")[0]
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
                                print(
                                    "Ingesting "
                                    + str(i)
                                    + " of "
                                    + str(file_count)
                                    + " "
                                    + str(os.path.basename(asset_full_path))
                                    + " Task Id: "
                                    + output.decode("ascii").strip().split(" ")[-1]
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
                                    full_path_to_collection + "/" + item.split(".")[0]
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
                                print(
                                    "Ingesting "
                                    + str(i)
                                    + " of "
                                    + str(file_count)
                                    + " "
                                    + str(os.path.basename(asset_full_path))
                                    + " Task Id: "
                                    + output.decode("ascii").strip().split(" ")[-1]
                                )
                        except Exception as e:
                            print(e)
                        i = i + 1
            except Exception as e:
                print(e)
            except (KeyboardInterrupt, SystemExit) as e:
                sys.exit("Program escaped by User")
        else:
            print("Authentication Failed for GEE account")
    elif len(diff_set) == 0:
        print("All assets already copied")


# authenticate(dirc=r'C:\planet_demo\grid')
