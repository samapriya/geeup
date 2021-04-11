# Prerequisites and Installation
This assumes that you have native python & pip installed in your system, you can test this by going to the terminal (or windows command prompt) and trying

```python``` and then ```pip list```

**geeup now only support Python v3.4 or higher from geeup version 0.3.3**


**This command line tool is dependent on functionality from GDAL**
For installing GDAL in Ubuntu
```
sudo add-apt-repository ppa:ubuntugis/ppa && sudo apt-get update
sudo apt-get install gdal-bin
sudo apt-get install python-gdal
```
## Windows Setup
Shapely and a few other libraries are notoriously difficult to install on windows machines so follow the steps mentioned here **before installing porder**. You can download and install shapely and other libraries from the [Unofficial Wheel files from here](https://www.lfd.uci.edu/~gohlke/pythonlibs) download depending on the python version you have. **Do this only once you have install GDAL**. I would recommend the steps mentioned above to get the GDAL properly installed. However I am including instructions to using a precompiled version of GDAL similar to the other libraries on windows. You can test to see if you have gdal by simply running

```gdalinfo```

in your command prompt. If you get a read out and not an error message you are good to go. If you don't have gdal try Option 1,2 or 3 in that order and that will install gdal along with the other libraries

#### Option 1:
Starting from geeup v0.3.4 onwards:

Simply run ```geeup -h``` after installation. This should go fetch the extra libraries you need and install them. Once installation is complete, the porder help page will show up. This should save you from the few steps below.

#### Option 2:
If this does not work or you get an unexpected error try the following commands. You can also use these commands if you simply want to update these libraries.

```
pipwin refresh
pipwin install gdal
```

#### Option 3
For Windows I also found this [guide](https://webcache.googleusercontent.com/search?q=cache:UZWc-pnCgwsJ:https://sandbox.idre.ucla.edu/sandbox/tutorials/installing-gdal-for-windows+&cd=4&hl=en&ct=clnk&gl=us) from UCLA

Also for Ubuntu Linux I saw that this is necessary before the install

```sudo apt install libcurl4-openssl-dev libssl-dev```

**This also needs earthengine cli to be [installed and authenticated on your system](https://developers.google.com/earth-engine/python_install_manual) and earthengine to be callable in your command line or terminal**

To install **geeup: Simple CLI for Earth Engine Uploads** you can install using two methods.

```pip install geeup```

or you can also try

```
git clone https://github.com/samapriya/geeup.git
cd geeup
python setup.py install
```
For Linux use sudo or try ```pip install geeup --user```.

I recommend installation within a virtual environment. Find more information on [creating virtual environments here](https://docs.python.org/3/library/venv.html).
