import requests
import time
import os
import getpass
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
    authorization_url="https://code.earthengine.google.com"
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
    driver.get(authorization_url)
    time.sleep(2)
    try:
        username = driver.find_element_by_xpath('//*[@id="identifierId"]')
        username.send_keys(uname)
        driver.find_element_by_id("identifierNext").click()
        time.sleep(5)
        passw=driver.find_element_by_name("password").send_keys(passw)
        driver.find_element_by_id("passwordNext").click()
        time.sleep(5)
        driver.find_element_by_xpath("//div[@id='view_container']/form/div[2]/div/div/div/ul/li/div/div[2]/p").click()
        time.sleep(5)
        driver.find_element_by_xpath("//div[@id='submit_approve_access']/content/span").click()
        time.sleep(5)
        driver.find_element_by_xpath("(.//*[normalize-space(text()) and normalize-space(.)='terms of service'])[1]/following::span[2]").click()
        time.sleep(3)
        driver.find_element_by_id("profileIdentifier").click()
        time.sleep(2)
        driver.find_element_by_xpath("(.//*[normalize-space(text()) and normalize-space(.)='Earth Engine Code Editor'])[1]/following::div[13]").click()
    except Exception as e:
        pass
    cookies = driver.get_cookies()
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])
    print('\n'+'Selenium Setup complete with Google Profile')
    driver.close()
authenticate()
