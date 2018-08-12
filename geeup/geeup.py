#! /usr/bin/env python

import argparse,os,ee
os.chdir(os.path.dirname(os.path.realpath(__file__)))
from hurry import filesize
from ee import oauth
from batch_uploader import upload
from batch_tuploader import tabup
from batch_remover import delete
from zipfiles import zipshape
from hurry import filesize
from os.path import expanduser
from planet.api.utils import write_planet_json
lpath=os.path.dirname(os.path.realpath(__file__))

def quota():
    quota=ee.data.getAssetRootQuota(ee.data.getAssetRoots()[0]['id'])
    print('')
    print("Total Quota: "+filesize.size(quota['asset_size']['limit']))
    print("Used Quota: "+filesize.size(quota['asset_size']['usage']))

def quota_from_parser(args):
    quota()

def zipshape_from_parser(args):
    zipshape(directory=args.input,export=args.output)

def _comma_separated_strings(string):
  """Parses an input consisting of comma-separated strings.
     Slightly modified version of: https://pypkg.com/pypi/earthengine-api/f/ee/cli/commands.py
  """
  error_msg = 'Argument should be a comma-separated list of alphanumeric strings (no spaces or other' \
              'special characters): {}'
  values = string.split(',')
  for name in values:
      if not name.isalnum():
          raise argparse.ArgumentTypeError(error_msg.format(string))
  return values

def upload_from_parser(args):
    upload(user=args.user,
           source_path=args.source,
           destination_path=args.dest,
           metadata_path=args.metadata,
           multipart_upload=args.large,
           nodata_value=args.nodata,
           bucket_name=args.bucket,
           band_names=args.bands)

def tabup_from_parser(args):
    tabup(user=args.user,
           source_path=args.source,
           destination_path=args.dest)
def tasks():
    statuses=ee.data.getTaskList()
    st=[]
    for status in statuses:
        st.append(status['state'])
    print("Tasks Running: "+str(st.count('RUNNING')))
    print("Tasks Ready: "+str(st.count('READY')))
    print("Tasks Completed: "+str(st.count('COMPLETED')))
    print("Tasks Failed: "+str(st.count('FAILED')))
    print("Tasks Cancelled: "+str(st.count('CANCELLED')))

def tasks_from_parser(args):
    tasks()

def delete_collection_from_parser(args):
    delete(args.id)

spacing="                               "
def main(args=None):
    parser = argparse.ArgumentParser(description='Simple Client for Earth Engine Uploads')

    subparsers = parser.add_subparsers()

    parser_quota = subparsers.add_parser('quota', help='Print Earth Engine total quota and used quota')
    parser_quota.set_defaults(func=quota_from_parser)

    parser_zipshape = subparsers.add_parser('zipshape', help='Zips all shapefiles and subsidary files into individual zip files')
    required_named = parser_zipshape.add_argument_group('Required named arguments.')
    required_named.add_argument('--input', help='Path to the input directory with all shape files', required=True)
    required_named.add_argument('--output', help='Destination folder Full path where shp, shx, prj and dbf files if present in input will be zipped and stored', required=True)
    parser_zipshape.set_defaults(func=zipshape_from_parser)

    parser_upload = subparsers.add_parser('upload', help='Batch Asset Uploader.')
    required_named = parser_upload.add_argument_group('Required named arguments.')
    required_named.add_argument('--source', help='Path to the directory with images for upload.', required=True)
    required_named.add_argument('--dest', help='Destination. Full path for upload to Google Earth Engine, e.g. users/pinkiepie/myponycollection', required=True)
    optional_named = parser_upload.add_argument_group('Optional named arguments')
    optional_named.add_argument('-m', '--metadata', help='Path to CSV with metadata.')
    optional_named.add_argument('--large', action='store_true', help='(Advanced) Use multipart upload. Might help if upload of large '
                                                                     'files is failing on some systems. Might cause other issues.')
    optional_named.add_argument('--nodata', type=int, help='The value to burn into the raster as NoData (missing data)')
    optional_named.add_argument('--bands', type=_comma_separated_strings, help='Comma-separated list of names to use for the image bands. Spaces'
                                                                               'or other special characters are not allowed.')

    required_named.add_argument('-u', '--user', help='Google account name (gmail address).')
    optional_named.add_argument('-b', '--bucket', help='Google Cloud Storage bucket name.')

    parser_upload.set_defaults(func=upload_from_parser)

    parser_tabup = subparsers.add_parser('tabup', help='Batch Table Uploader.')
    required_named = parser_tabup.add_argument_group('Required named arguments.')
    required_named.add_argument('--source', help='Path to the directory with zipped folder for upload.', required=True)
    required_named.add_argument('--dest', help='Destination. Full path for upload to Google Earth Engine, e.g. users/pinkiepie/myponycollection', required=True)
    required_named.add_argument('-u', '--user', help='Google account name (gmail address).')
    parser_tabup.set_defaults(func=tabup_from_parser)

    parser_tasks=subparsers.add_parser('tasks',help='Queries current task status [completed,running,ready,failed,cancelled]')
    parser_tasks.set_defaults(func=tasks_from_parser)

    parser_delete = subparsers.add_parser('delete', help='Deletes collection and all items inside. Supports Unix-like wildcards.')
    parser_delete.add_argument('id', help='Full path to asset for deletion. Recursively removes all folders, collections and images.')
    parser_delete.set_defaults(func=delete_collection_from_parser)

    args = parser.parse_args()

    #ee.Initialize()
    args.func(args)

if __name__ == '__main__':
    main()
