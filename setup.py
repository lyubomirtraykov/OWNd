#!/usr/bin/env python3

"""PyPi setup file for OWNd."""

import setuptools

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="OWNd",
    version="1.0.11b1",
    author="fedem95",
    url="https://github.com/fedem95/OWNd",
    author_email="tbd@gmail.com",
    description="Python interface for the OpenWebNet protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    install_requires=["aiohttp", "python-dateutil", "defusedxml"],
    python_requires=">=3.14",
)
