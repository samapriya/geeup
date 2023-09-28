# Prerequisites and Installation
We assume Earth Engine Python API is installed and EE initialized as desribed [here](https://developers.google.com/earth-engine/python_install). From v0.3.4 onwards geeup will only run on Python 3. Also with the new changes to the Earth Engine API library, the tool was completely modified to work with earthengine-api v0.1.127 and higher. Authenticate your earth engine client by using the following in your command line or terminal setup.

<b>

```
earthengine authenticate
```

</b>

Quick installation

```
pip install geeup

pip install geeup --user
```


To get always fresh install using GitHub (**This could be a staging version and will include a pop up on top to remind you of that**)

<b>

```
pip install git+https://github.com/samapriya/geeup.git
```

</b>

The advantage of having it installed is being able to execute geeup as any command line tool. I recommend installation within virtual environment.
