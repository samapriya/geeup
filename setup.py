import os

from setuptools import find_packages, setup


def readme():
    with open("README.md") as f:
        return f.read()

setup(
    name="geeup",
    version="1.0.1",
    python_requires=">=3.6",
    packages=find_packages(),
    url="https://github.com/samapriya/geeup",
    install_requires=[
        "pandas==2.0.3",
        "earthengine-api>=0.1.370",
        "requests>=2.10.0",
        "retrying>=1.3.3",
        "natsort>=8.1.0",
        "psutil>=5.4.5",
        "cerberus>=1.3.4",
        "requests-toolbelt>=0.7.0",
        "pytest>=3.0.0",
        "pathlib>=1.0.1",
        "lxml>=4.1.1",
        "oauth2client>=4.1.3",
    ],
    license="Apache 2.0",
    long_description=readme(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    author="Samapriya Roy",
    author_email="samapriya.roy@gmail.com",
    description="Simple Client for Earth Engine Uploads",
    entry_points={"console_scripts": ["geeup=geeup.geeup:main"]},
)
