#!/usr/bin/env python

import glob

from setuptools import find_packages, setup

setup(
    url="https://github.com/kislyuk/argcomplete",
    packages=find_packages(exclude=["test", "test.*"]),
    package_data={"argcomplete": ["bash_completion.d/_python-argcomplete", "py.typed"]},
    zip_safe=False,
    include_package_data=True,
    platforms=["MacOS X", "Posix"],
)
