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
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time,os,getpass,subprocess


pathway=os.path.dirname(os.path.realpath(__file__))

def seltabup(dirc,uname,destination):
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
                r=s.get("https://code.earthengine.google.com/assets/upload/geturl")
                d = ast.literal_eval(r.text)
                upload_url = d['url']
                file_path=os.path.join(dirc,item)
                with open(file_path, 'rb') as f:
                    upload_url = d['url']
                    files = {'file': f}
                    resp = s.post(upload_url, files=files)
                    gsid = resp.json()[0]
                    asset_full_path=destination+'/'+item.split('.')[0]
                    #print(asset_full_path)
                    output=subprocess.check_output('earthengine upload table --asset_id '+str(asset_full_path)+' '+str(gsid),shell=True)
                    print('Ingesting '+str(i)+' of '+str(file_count)+' '+str(os.path.basename(asset_full_path))+' task ID: '+str(output).strip())
                    i=i+1
    except Exception as e:
        print(e)
#authenticate(dirc=r'C:\planet_demo\grid')
