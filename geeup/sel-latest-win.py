from bs4 import BeautifulSoup
import requests,csv,zipfile,os,platform
from pathlib import Path
from pySmartDL import SmartDL
sysinfo=platform.machine()[-2:]
comb="win"+str(sysinfo)+".zip"
directory=os.path.dirname(os.path.realpath(__file__))
os.chdir(os.path.dirname(os.path.realpath(__file__)))
def geckodown(directory):
    source=requests.get("https://github.com/mozilla/geckodriver/releases/latest").text
    soup=BeautifulSoup(source.encode("utf-8"),'lxml')
    vr=str(soup.title.text.encode("utf-8")).split(' ')[1]
    container="https://github.com/mozilla/geckodriver/releases/download/"+vr+"/geckodriver-"+vr+'-'+comb
    print("Downloading from: "+str(container))
    try:
        url = container
        dest = directory
        obj = SmartDL(url, dest)
        obj.start()
        path=obj.get_dest()
        print(os.path.join(directory,'geckodriver-'+vr+'-win64.zip'))
        archive=zipfile.ZipFile(os.path.join(directory,'geckodriver-'+vr+'-'+comb))
        for files in archive.namelist():
            archive.extractall(directory)
        print("Use selenium driver path as "+str(directory))
    except Exception as e:
        print('Issues updating with error '+str(e))

geckodown(directory=directory)
#print(match.li.strong)

#print(match.find('li',class_='strong'))
