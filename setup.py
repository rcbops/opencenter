#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

from setuptools import setup, find_packages

requirements = ['flask', 'sqlalchemy>=0.7.4', 'sqlalchemy-migrate', 'gevent',
                'python-daemon', 'pychef']
excludes = ['test_runner.py', 'tests', 'tests.*']


setup(name='python-opencenter',
      version='1.0.0',
      description='OpenCenter Orchestration server',
      author='rcbops',
      author_email='rcb-deploy@lists.rackspace.com',
      url='https://github.com/rcbops/opencenter',
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
      entry_points={'console_scripts': ['opencenter = opencenter:main']},
      )
