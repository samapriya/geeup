import os
import sys
from distutils.version import StrictVersion

import setuptools
from setuptools import __version__ as setuptools_version
from setuptools import find_packages
from setuptools.command.test import test as TestCommand


def readme():
    with open("README.md") as f:
        return f.read()


setuptools.setup(
    name="geeup",
    version="0.6.5",
    packages=find_packages(),
    url="https://github.com/samapriya/geeup",
    install_requires=[
        "wheel",
        "earthengine_api>=0.1.370",
        "logzero>=1.5.0",
        "requests >= 2.10.0",
        "retrying >= 1.3.3",
        "natsort >= 8.1.0",
        "pandas",
        "psutil>=5.4.5",
        "cerberus>=1.3.4",
        "requests_toolbelt >= 0.7.0",
        "pytest >= 3.0.0",
        "pathlib>=1.0.1",
        "lxml>=4.1.1",
        "oauth2client>=4.1.3",
    ],
    license="Apache 2.0",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    author="Samapriya Roy",
    author_email="samapriya.roy@gmail.com",
    description="Simple Client for Earth Engine Uploads",
    entry_points={"console_scripts": ["geeup=geeup.geeup:main"]},
)
