import ast
import csv
import getpass
import glob
import logging
import os
import sys
import time

if sys.version_info > (3, 0):
    from urllib.parse import unquote
else:
    from urllib import unquote

import ee
import requests
import retrying
from requests_toolbelt.multipart import encoder
from bs4 import BeautifulSoup

from google.cloud import storage

from metadata_loader import load_metadata_from_csv, validate_metadata_from_csv


def upload(user, source_path, destination_path, metadata_path=None, multipart_upload=False, nodata_value=None, bucket_name=None, band_names=[]):
    """
    Uploads content of a given directory to GEE. The function first uploads an asset to Google Cloud Storage (GCS)
    and then uses ee.data.startIngestion to put it into GEE, Due to GCS intermediate step, users is asked for
    Google's account name and password.

    In case any exception happens during the upload, the function will repeat the call a given number of times, after
    which the error will be propagated further.

    :param user: name of a Google account
    :param source_path: path to a directory
    :param destination_path: where to upload (absolute path)
    :param metadata_path: (optional) path to file with metadata
    :param multipart_upload: (optional) alternative mode op upload - use if the other one fails
    :param nodata_value: (optinal) value to burn into raster for missind data in the image
    :return:
    """
    submitted_tasks_id = {}

    __verify_path_for_upload(destination_path)

    path = os.path.join(os.path.expanduser(source_path), '*.tif')
    all_images_paths = glob.glob(path)

    if len(all_images_paths) == 0:
        logging.error('%s does not contain any tif images.', path)
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
        logging.error('No images found that match %s. Exiting...', path)
        sys.exit(1)

    failed_asset_writer = FailedAssetsWriter()

    for current_image_no, image_path in enumerate(images_for_upload_path):
        logging.info('Processing image %d out of %d: %s', current_image_no+1, no_images, image_path)
        filename = __get_filename_from_path(path=image_path)

        asset_full_path = destination_path + '/' + filename

        if metadata and not filename in metadata:
            logging.warning("No metadata exists for image %s: it will not be ingested", filename)
            failed_asset_writer.writerow([filename, 0, 'Missing metadata'])
            continue

        properties = metadata[filename] if metadata else None

        try:
            if user is not None:
                gsid = __upload_file_gee(session=google_session,
                                                  file_path=image_path,
                                                  use_multipart=multipart_upload)
            else:
                gsid = __upload_file_gcs(storage_client, bucket_name, image_path)

            asset_request = __create_asset_request(asset_full_path, gsid, properties, nodata_value, band_names)

            task_id = __start_ingestion_task(asset_request)
            submitted_tasks_id[task_id] = filename
            __periodic_check(current_image=current_image_no, period=20, tasks=submitted_tasks_id, writer=failed_asset_writer)
        except Exception as e:
            logging.exception('Upload of %s has failed.', filename)
            failed_asset_writer.writerow([filename, 0, str(e)])

    __check_for_failed_tasks_and_report(tasks=submitted_tasks_id, writer=failed_asset_writer)
    failed_asset_writer.close()

def __create_asset_request(asset_full_path, gsid, properties, nodata_value, band_names):
    if band_names:
        band_names = [{'id': name} for name in band_names]

    return {"id": asset_full_path,
        "tilesets": [
            {"sources": [
                {"primaryPath": gsid,
                 "additionalPaths": []
                 }
            ]}
        ],
        "bands": band_names,
        "properties": properties,
        "missingData": {"value": nodata_value}
    }

def __verify_path_for_upload(path):
    folder = path[:path.rfind('/')]
    response = ee.data.getInfo(folder)
    if not response:
        logging.error('%s is not a valid destination. Make sure full path is provided e.g. users/user/nameofcollection '
                      'or projects/myproject/myfolder/newcollection and that you have write access there.', path)
        sys.exit(1)


def __find_remaining_assets_for_upload(path_to_local_assets, path_remote):
    local_assets = [__get_filename_from_path(path) for path in path_to_local_assets]
    if __collection_exist(path_remote):
        remote_assets = __get_asset_names_from_collection(path_remote)
        if len(remote_assets) > 0:
            assets_left_for_upload = set(local_assets) - set(remote_assets)
            if len(assets_left_for_upload) == 0:
                logging.warning('Collection already exists and contains all assets provided for upload. Exiting ...')
                sys.exit(1)

            logging.info('Collection already exists. %d assets left for upload to %s.', len(assets_left_for_upload), path_remote)
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
        logging.warning('%d images does not have a corresponding key in metadata', len(missing_keys))
        print('\n'.join(e for e in missing_keys))
    else:
        logging.info('All images have metadata available')

    if not validation_result.success:
        print('Validation finished with errors. Type "y" to continue, default NO: ')
        choice = input().lower()
        if choice not in ['y', 'yes']:
            logging.info('Application will terminate')
            exit(1)


def __extract_metadata_for_image(filename, metadata):
    if filename in metadata:
        return metadata[filename]
    else:
        logging.warning('Metadata for %s not found', filename)
        return None


def __get_google_auth_session(username, password):
    google_accounts_url = 'https://accounts.google.com'
    authentication_url = 'https://accounts.google.com/ServiceLoginAuth'

    session = requests.session()

    login_html = session.get(google_accounts_url)
    soup_login = BeautifulSoup(login_html.content, 'html.parser').find('form').find_all('input')
    payload = {}
    for u in soup_login:
        if u.has_attr('value'):
            payload[u['name']] = u['value']

    payload['Email'] = username
    payload['Passwd'] = password

    auto = login_html.headers.get('X-Auto-Login')
    follow_up = unquote(unquote(auto)).split('continue=')[-1]

    payload['continue'] = follow_up

    session.post(authentication_url, data=payload)
    return session


def __get_upload_url(session):
    # get url and discard; somehow it does not work for the first time
    _ = session.get('https://ee-api.appspot.com/assets/upload/geturl?')
    r = session.get('https://ee-api.appspot.com/assets/upload/geturl?')
    if r.text.startswith('\n<!DOCTYPE html>'):
        logging.error('Incorrect credentials. Probably. If you are sure the credentials are OK, refresh the authentication token. '
                      'If it did not work report a problem. They might have changed something in the Matrix.')
        sys.exit(1)
    d = ast.literal_eval(r.text)
    return d['url']

@retrying.retry(retry_on_exception=retry_if_ee_error, wait_exponential_multiplier=1000, wait_exponential_max=4000, stop_max_attempt_number=3)
def __upload_file_gee(session, file_path, use_multipart):
    with open(file_path, 'rb') as f:
        upload_url = __get_upload_url(session)

        if use_multipart:
            form = encoder.MultipartEncoder({
                "documents": (file_path, f, "application/octet-stream"),
                "composite": "NONE",
            })
            headers = {"Prefer": "respond-async", "Content-Type": form.content_type}
            resp = session.post(upload_url, headers=headers, data=form)
        else:
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
        logging.info('Periodic check')
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
            logging.error('Ingestion of image %s has failed with message %s', filename, error_message)

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
        logging.warning("Collection %s already exists", full_path_to_collection)
    else:
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_IMAGE_COLL}, full_path_to_collection)
        logging.info('New collection %s created', full_path_to_collection)


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
