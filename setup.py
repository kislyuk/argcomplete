#!/usr/bin/env python

import glob

from setuptools import setup

setup(
    url="https://github.com/kislyuk/argcomplete",
    scripts=glob.glob("scripts/*"),
)
