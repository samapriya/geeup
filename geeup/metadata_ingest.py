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

'''
Modifications to file:
- Uses selenium based upload instead of simple login
- Removed multipart upload
- Added poster for streaming upload
'''
import ast
import csv
import getpass
import glob
import logging
import os
import sys
import time
import subprocess
import json
import manifest_lib
import pandas as pd
import ee
import requests
import retrying
from google.cloud import storage
from metadata_loader import load_metadata_from_csv, validate_metadata_from_csv
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
os.chdir(os.path.dirname(os.path.realpath(__file__)))
lp=os.path.dirname(os.path.realpath(__file__))
sys.path.append(lp)
ee.Initialize()
def selupload(user, source_path, destination_path, manifest=None,metadata_path=None, nodata_value=None, bucket_name=None):
    submitted_tasks_id = {}

    __verify_path_for_upload(destination_path)

    path = os.path.join(os.path.expanduser(source_path), '*.tif')
    all_images_paths = glob.glob(path)
    if len(all_images_paths) == 0:
        print('%s does not contain any tif images.', path)
        sys.exit(1)

    metadata = load_metadata_from_csv(metadata_path) if metadata_path else None

    if user is not None:
        password = getpass.getpass()
        google_session = __get_google_auth_session(user, password)
    else:
        storage_client = storage.Client()

    __create_image_collection(destination_path)

    images_for_upload_path = __find_remaining_assets_for_upload(all_images_paths, destination_path)
    no_images = len(images_for_upload_path)

    if no_images == 0:
        print('No images found that match %s. Exiting...', path)
        sys.exit(1)

    failed_asset_writer = FailedAssetsWriter()

    for current_image_no, image_path in enumerate(images_for_upload_path):
        print('Processing image '+str(current_image_no+1)+' out of '+str(no_images)+': '+str(image_path))
        filename = __get_filename_from_path(path=image_path)

        asset_full_path = destination_path + '/' + filename

        if metadata and not filename in metadata:
            print("No metadata exists for image "+str(filename)+" : it will not be ingested")
            failed_asset_writer.writerow([filename, 0, 'Missing metadata'])
            continue

        properties = metadata[filename] if metadata else None
        if manifest=="PSO":
            data=manifest_lib.data_pso
        elif manifest=="PSO_DN":
            data=manifest_lib.data_psodn
        elif manifest=="PSO_V":
            data=manifest_lib.data_psov
        elif manifest=="PS4B":
            data=manifest_lib.data_ps4b
        elif manifest=="PS4B_SR":
            data=manifest_lib.data_ps4bsr
        elif manifest=="PS4B_DN":
            data=manifest_lib.data_ps4bdn
        elif manifest=="PS3B":
            data=manifest_lib.data_ps3b
        elif manifest=="PS3B_DN":
            data=manifest_lib.data_ps3bdn
        elif manifest=="PS3B_V":
            data=manifest_lib.data_ps3bv
        elif manifest=="REO":
            data=manifest_lib.data_reo
        elif manifest=="REO_V":
            data=manifest_lib.data_reov
        else:
            print("No Manifest Provided")
            sys.exit()
        try:
            if user is not None:
                gsid = __upload_file_gee(session=google_session,
                                                  file_path=image_path)
            else:
                gsid = __upload_file_gcs(storage_client, bucket_name, image_path)

            asset_request = __create_asset_request(asset_full_path, gsid, properties, nodata_value)

            df=pd.read_csv(metadata_path)
            stringcol = list(df.select_dtypes(include=['object']).columns)
            intcol= list(df.select_dtypes(include=['int64']).columns)
            floatcol = list(df.select_dtypes(include=['float64']).columns)
            with open(metadata_path, 'r') as f:
                reader = csv.DictReader(f,delimiter=",")
                for i, line in enumerate(reader):
                    if line["id_no"]==os.path.basename(image_path).split('.')[0]:
                        for key, value in data['properties'].items():
                            for integer in intcol:
                                try:
                                    data['properties'][integer]=int(line[integer])
                                except Exception as e:
                                    print(e)
                            for s in stringcol:
                                try:
                                    data['properties'][s]=str(line[s])
                                except Exception as e:
                                    print(e)
                            for f in floatcol:
                                try:
                                    data['properties'][f]=float(line[f])
                                except Exception as e:
                                    print(e)
                        data['id']=destination_path+'/'+line["id_no"]
                        data['tilesets'][0]['sources'][0]['primaryPath']=gsid
                        json_data = json.dumps(data)
                        with open(os.path.join(lp,'data.json'), 'w') as outfile:
                            json.dump(data, outfile)
                        subprocess.call("earthengine upload_manifest "+'"'+os.path.join(lp,'data.json')+'"',shell=True)
        except Exception as e:
            print('Upload of '+str(filename)+' has failed.')
            failed_asset_writer.writerow([filename, 0, str(e)])

        __check_for_failed_tasks_and_report(tasks=submitted_tasks_id, writer=failed_asset_writer)
        failed_asset_writer.close()

def __create_asset_request(asset_full_path, gsid, properties, nodata_value):
    return {"id": asset_full_path,
        "tilesets": [
            {"sources": [
                {"primaryPath": gsid,
                 "additionalPaths": []
                 }
            ]}
        ],
        "bands": [],
        "properties": properties,
        "missingData": {"value": nodata_value}
    }

def __verify_path_for_upload(path):
    folder = path[:path.rfind('/')]
    response = ee.data.getInfo(folder)
    if not response:
        print(str(path)+' is not a valid destination. Make sure full path is provided e.g. users/user/nameofcollection '
                      'or projects/myproject/myfolder/newcollection and that you have write access there.')
        sys.exit(1)


def __find_remaining_assets_for_upload(path_to_local_assets, path_remote):
    local_assets = [__get_filename_from_path(path) for path in path_to_local_assets]
    if __collection_exist(path_remote):
        remote_assets = __get_asset_names_from_collection(path_remote)
        if len(remote_assets) > 0:
            assets_left_for_upload = set(local_assets) - set(remote_assets)
            if len(assets_left_for_upload) == 0:
                print('Collection already exists and contains all assets provided for upload. Exiting ...')
                sys.exit(1)

            print('Collection already exists. '+str(len(assets_left_for_upload))+' assets left for upload to '+str(path_remote))
            assets_left_for_upload_full_path = [path for path in path_to_local_assets
                                                if __get_filename_from_path(path) in assets_left_for_upload]
            return assets_left_for_upload_full_path

    return path_to_local_assets


def retry_if_ee_error(exception):
    return isinstance(exception, ee.EEException)


@retrying.retry(retry_on_exception=retry_if_ee_error, wait_exponential_multiplier=1000, wait_exponential_max=4000, stop_max_attempt_number=3)
def __start_ingestion_task(asset_request):
    task_id = ee.data.newTaskId(1)[0]
    _ = ee.data.startIngestion(task_id, asset_request)
    return task_id


def __validate_metadata(path_for_upload, metadata_path):
    validation_result = validate_metadata_from_csv(metadata_path)
    keys_in_metadata = {result.keys for result in validation_result}
    images_paths = glob.glob(os.path.join(path_for_upload, '*.tif*'))
    keys_in_data = {__get_filename_from_path(path) for path in images_paths}
    missing_keys = keys_in_data - keys_in_metadata

    if missing_keys:
        print(str(len(missing_keys)+' images does not have a corresponding key in metadata'))
        print('\n'.join(e for e in missing_keys))
    else:
        print('All images have metadata available')

    if not validation_result.success:
        print('Validation finished with errors. Type "y" to continue, default NO: ')
        choice = input().lower()
        if choice not in ['y', 'yes']:
            print('Application will terminate')
            exit(1)


def __extract_metadata_for_image(filename, metadata):
    if filename in metadata:
        return metadata[filename]
    else:
        print('Metadata for '+str(filename)+' not found')
        return None


@retrying.retry(retry_on_exception=retry_if_ee_error, wait_exponential_multiplier=1000, wait_exponential_max=4000, stop_max_attempt_number=3)
def __get_google_auth_session(username, password):
    ee.Initialize()
    options = Options()
    options.add_argument('-headless')
    authorization_url="https://code.earthengine.google.com"
    uname=str(username)
    passw=str(password)
    if os.name=="nt":
        driver = Firefox(executable_path=os.path.join(lp,"geckodriver.exe"),firefox_options=options)
    elif os.name=="posix":
        driver = Firefox(executable_path=os.path.join(lp,"geckodriver"),firefox_options=options)
    driver.get(authorization_url)
    time.sleep(5)
    username = driver.find_element_by_xpath('//*[@id="identifierId"]')
    username.send_keys(uname)
    driver.find_element_by_id("identifierNext").click()
    time.sleep(5)
    #print('username')
    passw=driver.find_element_by_name("password").send_keys(passw)
    driver.find_element_by_id("passwordNext").click()
    time.sleep(5)
    #print('password')
    try:
        driver.find_element_by_xpath("//div[@id='view_container']/form/div[2]/div/div/div/ul/li/div/div[2]/p").click()
        time.sleep(5)
        driver.find_element_by_xpath("//div[@id='submit_approve_access']/content/span").click()
        time.sleep(5)
    except Exception as e:
        pass
    cookies = driver.get_cookies()
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    driver.close()
    return session

def __get_upload_url(session):
    r=session.get("https://code.earthengine.google.com/assets/upload/geturl")
    try:
        d = ast.literal_eval(r.text)
        return d['url']
    except Exception as e:
        print(e)

@retrying.retry(retry_on_exception=retry_if_ee_error, wait_exponential_multiplier=1000, wait_exponential_max=4000, stop_max_attempt_number=3)
def __upload_file_gee(session, file_path):
    with open(file_path, 'rb') as f:
        upload_url = __get_upload_url(session)
        files = {'file': f}
        resp = session.post(upload_url, files=files)
        gsid = resp.json()[0]
        return gsid

@retrying.retry(retry_on_exception=retry_if_ee_error, wait_exponential_multiplier=1000, wait_exponential_max=4000, stop_max_attempt_number=3)
def __upload_file_gcs(storage_client, bucket_name, image_path):
    bucket = storage_client.get_bucket(bucket_name)
    blob_name = __get_filename_from_path(path=image_path)
    blob = bucket.blob(blob_name)

    blob.upload_from_filename(image_path)

    url = 'gs://' + bucket_name + '/' + blob_name

    return url

def __periodic_check(current_image, period, tasks, writer):
    if (current_image + 1) % period == 0:
        print('Periodic check')
        __check_for_failed_tasks_and_report(tasks=tasks, writer=writer)
        # Time to check how many tasks are running!
        __wait_for_tasks_to_complete(waiting_time=10, no_allowed_tasks_running=20)


def __check_for_failed_tasks_and_report(tasks, writer):
    if len(tasks) == 0:
        return

    statuses = ee.data.getTaskStatus(tasks.keys())

    for status in statuses:
        if status['state'] == 'FAILED':
            task_id = status['id']
            filename = tasks[task_id]
            error_message = status['error_message']
            writer.writerow([filename, task_id, error_message])
            print('Ingestion of image '+str(filename)+' has failed with message '+str(error_message))

    tasks.clear()


def __get_filename_from_path(path):
    return os.path.splitext(os.path.basename(os.path.normpath(path)))[0]


def __get_number_of_running_tasks():
    return len([task for task in ee.data.getTaskList() if task['state'] == 'RUNNING'])


def __wait_for_tasks_to_complete(waiting_time, no_allowed_tasks_running):
    tasks_running = __get_number_of_running_tasks()
    while tasks_running > no_allowed_tasks_running:
        logging.info('Number of running tasks is %d. Sleeping for %d s until it goes down to %d',
                     tasks_running, waiting_time, no_allowed_tasks_running)
        time.sleep(waiting_time)
        tasks_running = __get_number_of_running_tasks()


def __collection_exist(path):
    return True if ee.data.getInfo(path) else False


def __create_image_collection(full_path_to_collection):
    if __collection_exist(full_path_to_collection):
        print('Collection '+str(full_path_to_collection)+' already exists')
    else:
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_IMAGE_COLL}, full_path_to_collection)
        print('New collection '+str(full_path_to_collection)+' created')


def __get_asset_names_from_collection(collection_path):
    assets_list = ee.data.getList(params={'id': collection_path})
    assets_names = [os.path.basename(asset['id']) for asset in assets_list]
    return assets_names


class FailedAssetsWriter(object):

    def __init__(self):
        self.initialized = False

    def writerow(self, row):
        if not self.initialized:
            if sys.version_info > (3, 0):
                self.failed_upload_file = open('failed_upload.csv', 'w')
            else:
                self.failed_upload_file = open('failed_upload.csv', 'wb')
            self.failed_upload_writer = csv.writer(self.failed_upload_file)
            self.failed_upload_writer.writerow(['filename', 'task_id', 'error_msg'])
            self.initialized = True
        self.failed_upload_writer.writerow(row)

    def close(self):
        if self.initialized:
            self.failed_upload_file.close()
            self.initialized = False
