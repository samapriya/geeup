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

import fnmatch
import logging
import sys

import ee


def delete(asset_path):
    root = asset_path[:asset_path.rfind('/')]
    all_assets_names = [e['id'] for e in ee.data.getList({'id': root})]
    filtered_names = fnmatch.filter(all_assets_names, asset_path)
    if not filtered_names:
        logging.warning('Nothing to remove. Exiting.')
        sys.exit(1)
    else:
        for path in filtered_names:
            __delete_recursive(path)
            logging.info('Collection %s removed', path)


def __delete_recursive(asset_path):
    info = ee.data.getInfo(asset_path)
    if not info:
        logging.warning('Nothing to delete.')
        sys.exit(1)
    elif info['type'] == 'Image':
        pass
    elif info['type'] == 'Folder':
        items_in_destination = ee.data.getList({'id': asset_path})
        for item in items_in_destination:
            logging.info('Removing items in %s folder', item['id'])
            delete(item['id'])
    else:
        items_in_destination = ee.data.getList({'id': asset_path})
        for item in items_in_destination:
            ee.data.deleteAsset(item['id'])
    ee.data.deleteAsset(asset_path)
