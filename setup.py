#!/usr/bin/env python

import os
import re
import sys
from setuptools import setup, find_packages

requirements = ['flask', 'sqlalchemy', 'sqlalchemy-migrate', 'gevent',
                'python-daemon', 'pychef']
excludes = ['test_runner.py', 'tests', 'tests.*']


setup(name='python-roush',
      version='1.0.0',
      description='Roush Orchestration server',
      author='rcbops',
      author_email='rcb-deploy@lists.rackspace.com',
      url='https://github.com/rcbops/roush',
      license='Apache',
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',
                   'Intended Audience :: Developers',
                   'Intented Audience :: Information Technology',
                   'License :: OSI Approved :: Apache Software License',
                   'Operating System :: OS Independant',
                   'Programming Language :: Python',
                   ],
      include_package_data=True,
      packages=find_packages(),
      install_requires=requirements,
      entry_points={'console_scripts': ['roush = roush:main']},
      )
