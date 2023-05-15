#!/usr/bin/env python

import glob

from setuptools import find_packages, setup

setup(
    version="3.0.8",
    url="https://github.com/kislyuk/argcomplete",
    packages=find_packages(exclude=["test", "test.*"]),
    scripts=glob.glob("scripts/*"),
    package_data={"argcomplete": ["bash_completion.d/python-argcomplete", "py.typed"]},
    zip_safe=False,
    include_package_data=True,
    platforms=["MacOS X", "Posix"],
 )
