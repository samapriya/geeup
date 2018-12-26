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
    source=requests.get("https://github.com/mozilla/geckodriver/releases").text
    soup=BeautifulSoup(source,'lxml')
    match=soup.find('ul',class_='release-downloads')
    i=0
    for article in soup.find_all('strong'):
        if str(comb) not in article.text:
            pass
        else:
            while i<1:
                vr=str(article.text).split("-")[1].split("-")[0]
                container="https://github.com/mozilla/geckodriver/releases/download/"+vr+"/"+str(article.text)
                print("Downloading from: "+str(container))
                try:
                    url = container
                    dest = directory
                    obj = SmartDL(url, dest)
                    obj.start()
                    path=obj.get_dest()
                    #print(article.text)
                    filepath=os.path.join(directory,article.text)
                    if (filepath.endswith("tar.gz")):
                        tar = tarfile.open(filepath,'r:*')
                        tar.extractall(directory)
                        tar.close()
                        #print "Extracted in Current Directory"
                        print("Use selenium driver path as "+os.path.join(directory,"geckodriver"))
                except Exception as e:
                    print(e)
                    
                i=i+1
    
geckodown(directory=directory)
