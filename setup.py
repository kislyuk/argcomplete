# -*- coding: utf-8 -*-
"""
argcomplete
~~~~

Argcomplete provides easy and extensible automatic tab completion of arguments and options for your Python script.

It makes two assumptions:

- You're using bash as your shell
- You're using argparse to manage your command line options

See https://github.com/kislyuk/argcomplete for more info.

"""

import os
from setuptools import setup, find_packages

setup(
    name='argcomplete',
    version='0.1.2',
    url='https://github.com/kislyuk/argcomplete',
    license='GPL',
    author='Andrey Kislyuk',
    author_email='kislyuk@gmail.com',
    description='Bash tab completion for argparse',
    long_description=__doc__,
    packages = find_packages(),
    scripts = ['scripts/register-python-argcomplete'],
    zip_safe=False,
    include_package_data=True,
    platforms=['MacOS X', 'Posix'],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Unix Shell',
        'Development Status :: 4 - Beta',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
