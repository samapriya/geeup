__copyright__ = """

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

import requests
import ast
import ee
import sys
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from requests_toolbelt import MultipartEncoder
import time,os,getpass,subprocess
lp=os.path.dirname(os.path.realpath(__file__))
sys.path.append(lp)

def table_exist(path):
    return True if ee.data.getInfo(path) else False

def folder_exist(path):
    if ee.data.getInfo(path) and ee.data.getInfo(path)['type']=='Folder':
        return True
    else:
        return False


def create_image_collection(full_path_to_collection):
    if folder_exist(full_path_to_collection):
        print("Folder "+str(full_path_to_collection)+" already exists")
    else:
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, full_path_to_collection)
        print('New folder '+str(full_path_to_collection)+' created')

def seltabup(dirc,uname,destination):
    ee.Initialize()
    options = Options()
    options.add_argument('-headless')
    authorization_url="https://code.earthengine.google.com"
    passw=getpass.getpass()
    create_image_collection(destination)
    if os.name=="nt":
        driver = Firefox(executable_path=os.path.join(lp,"geckodriver.exe"),firefox_options=options)
    else:
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
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])
    driver.close()
    try:
        i=1
        path, dirs, files = next(os.walk(dirc))
        file_count = len(files)
        #print(file_count)
        for item in os.listdir(dirc):
            if item.endswith('.zip'):
                fpath=os.path.basename(item).split('.')[0]
                full_path_to_table=str(destination)+'/'+str(fpath)
                if table_exist(full_path_to_table)==True:
                    print('Table already exists Skipping: '+str(fpath))
                    i=i+1
                else:
                    r=s.get("https://code.earthengine.google.com/assets/upload/geturl")
                    d = ast.literal_eval(r.text)
                    upload_url = d['url']
                    file_path=os.path.join(dirc,item)
                    file_name=os.path.basename(file_path)
                    with open(file_path, 'rb') as f:
                        upload_url = d['url']
                        try:
                            m=MultipartEncoder( fields={'zip_file':(file_name, f)})
                            resp = s.post(upload_url, data=m, headers={'Content-Type': m.content_type})
                            gsid = resp.json()[0]
                            asset_full_path=destination+'/'+item.split('.')[0]
                            output=subprocess.check_output('earthengine --no-use_cloud_api upload table --asset_id '+str(asset_full_path)+' '+str(gsid),shell=True)
                            print('Ingesting '+str(i)+' of '+str(file_count)+' '+str(os.path.basename(asset_full_path))+' task ID: '+str(output).strip())
                        except Exception as e:
                            print(e)
                    i=i+1
    except Exception as e:
        print(e)
#authenticate(dirc=r'C:\planet_demo\grid')
