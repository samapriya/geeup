from bs4 import BeautifulSoup
import requests,csv,zipfile,os,platform,tarfile
from pathlib import Path
from pySmartDL import SmartDL
sysinfo=platform.machine()[-2:]
#comb="win"+str(sysinfo)+".zip"
comb="linux"+str("64")+".tar.gz"
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
        print(os.path.join(directory,'geckodriver-'+vr+'-linux64.zip'))
        filepath=os.path.join(directory,'geckodriver-'+vr+'-'+comb)
        if (filepath.endswith("tar.gz")):
            tar = tarfile.open(filepath,'r:*')
            tar.extractall(directory)
            tar.close()
            #print "Extracted in Current Directory"
            print("Use selenium driver path as "+os.path.join(directory,"geckodriver"))
    except Exception as e:
        print('Issues updating with error '+str(e))

geckodown(directory=directory)
