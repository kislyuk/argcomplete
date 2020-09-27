#!/usr/bin/env python

import glob
from setuptools import setup, find_packages

install_requires = []
tests_require = ["coverage", "flake8", "pexpect", "wheel"]
importlib_backport_requires = ["importlib-metadata >= 0.23, < 3"]

setup(
    name='argcomplete',
    version='1.12.1',
    url='https://github.com/kislyuk/argcomplete',
    project_urls={
        "Documentation": "https://kislyuk.github.io/argcomplete",
        "Source Code": "https://github.com/kislyuk/argcomplete",
        "Issue Tracker": "https://github.com/kislyuk/argcomplete/issues"
    },
    license='Apache Software License',
    author='Andrey Kislyuk',
    author_email='kislyuk@gmail.com',
    description='Bash tab completion for argparse',
    long_description=open('README.rst').read(),
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        "test": tests_require,
        ':python_version == "2.7"': importlib_backport_requires,
        ':python_version == "3.5"': importlib_backport_requires,
        ':python_version == "3.6"': importlib_backport_requires,
        ':python_version == "3.7"': importlib_backport_requires
    },
    packages=find_packages(exclude=['test']),
    scripts=glob.glob('scripts/*'),
    package_data={'argcomplete': ['bash_completion.d/python-argcomplete']},
    zip_safe=False,
    include_package_data=True,
    platforms=['MacOS X', 'Posix'],
    test_suite='test',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Development Status :: 5 - Production/Stable',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Shells',
        'Topic :: Terminals'
    ]
)
