#!/usr/bin/env python

import glob
from setuptools import setup, find_packages, Command

install_requires = []

try:
    import argparse
except ImportError:
    install_requires.append('argparse')

class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys,subprocess
        errno = subprocess.call([sys.executable, '-m', 'pytest', 'test'])
        raise SystemExit(errno)

setup(
    name='argcomplete',
    version='0.5.7',
    url='https://github.com/kislyuk/argcomplete',
    license='Apache Software License',
    author='Andrey Kislyuk',
    author_email='kislyuk@gmail.com',
    description='Bash tab completion for argparse',
    long_description=open('README.rst').read(),
    install_requires=install_requires,
    packages = find_packages(),
    scripts = glob.glob('scripts/*'),
    package_data={'argcomplete': ['bash_completion.d/python-argcomplete.sh']},
    zip_safe=False,
    include_package_data=True,
    platforms=['MacOS X', 'Posix'],
    cmdclass = { 'test': PyTest },
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Unix Shell',
        'Development Status :: 4 - Beta',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
