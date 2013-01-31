#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import re
import sys
from setuptools import setup, find_packages

requirements = ['flask', 'sqlalchemy==0.7.4', 'sqlalchemy-migrate', 'gevent',
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
      packages=find_packages(exclude=excludes),
      install_requires=requirements,
      entry_points={'console_scripts': ['roush = roush:main']},
      )
