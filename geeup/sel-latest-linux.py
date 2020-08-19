from bs4 import BeautifulSoup
import requests,csv,zipfile,os,platform,tarfile,re
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
    for link in soup.findAll('a', attrs={'href': re.compile("/mozilla/geckodriver/releases/")}):
        if vr+'-'+comb in link.get('href') and link.get('href').endswith('.tar.gz'):
            container = 'https://github.com/{}'.format(link.get('href'))
            #container="https://github.com/mozilla/geckodriver/releases/download/"+vr+"/geckodriver-"+vr+'-'+comb
            print("Downloading from: "+str(container))
            try:
                url = container
                dest = directory
                obj = SmartDL(url, dest)
                obj.start()
                path=obj.get_dest()
                archive=tarfile.open(os.path.join(directory,'geckodriver-v'+vr+'-'+comb))
                archive.extractall(directory)
                print("Use selenium driver path as "+str(directory))
            except Exception as e:
                print('Issues updating with error '+str(e))

geckodown(directory=directory)
