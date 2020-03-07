import requests
import time
import os
import ast
import getpass
import sys
from selenium import webdriver
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

pathway=os.path.dirname(os.path.realpath(__file__))
def authenticate():
    try:
        uname=str(raw_input("Enter your Username:  "))
    except Exception as e:
        uname=str(input("Enter your Username:  "))
    passw=str(getpass.getpass("Enter your Password:  "))
    options=Options()
    if os.name=="nt":
        driver = Firefox(executable_path=os.path.join(pathway,"geckodriver.exe"),firefox_options=options)
    else:
        driver = Firefox(executable_path=os.path.join(pathway,"geckodriver"),firefox_options=options)
    try:
        # Using stackoverflow for third-party login & redirect
        driver.get('https://stackoverflow.com/users/signup?ssrc=head&returnurl=%2fusers%2fstory%2fcurrent%27')
        time.sleep(5)
        driver.find_element_by_xpath('//*[@id="openid-buttons"]/button[1]').click()
        time.sleep(5)
        driver.find_element_by_xpath('//input[@type="email"]').send_keys(uname)
        driver.find_element_by_xpath("//div[@id='identifierNext']/span/span").click()
        time.sleep(5)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(passw)
        driver.find_element_by_xpath('//*[@id="passwordNext"]').click()
        time.sleep(5)
        driver.get('https://code.earthengine.google.com')
        time.sleep(8)
    except Exception as e:
        print(e)
        driver.close()
        sys.exit('Failed to setup Selenium profile')
    cookies = driver.get_cookies()
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])
    r=s.get("https://code.earthengine.google.com/assets/upload/geturl")
    try:
        d = ast.literal_eval(r.text)
        if d['url']:
            print('\n'+'Selenium Setup complete with Google Profile')
    except Exception as e:
        print(e)
    driver.close()
authenticate()
