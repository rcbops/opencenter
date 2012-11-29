#!/usr/bin/env python

import os
import re
import sys
from setuptools import setup, find_packages

requirements = ['flask', 'sqlalchemy', 'sqlalchemy-migrate', 'gevent',
                'python-daemon', 'pychef']
excludes = ['test_runner.py', 'tests', 'tests.*']


def find_json_files(matchlist):
    destfiles = {}

    for path, match in matchlist:
        if os.path.isdir(path):
            for d in os.walk(path):
                for filename in d[2]:
                    if re.match(match, filename):
                        if not d[0] in destfiles:
                            destfiles[d[0]] = []

                        destfiles[d[0]].append(os.path.join(d[0], filename))

    return [(k, destfiles[k]) for k in destfiles]

# print find_json_files([('roush/db/migrate_repo/versions', '.*\.criteria'),
#                        ('roush/db/migrate_repo/versions', '.*\.json'),
#                        ('roush/backends', '.*\.json')])
# sys.exit(0)


setup(name='roush',
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
      packages=['roush'],
      package_dir={'roush': 'roush'},
      install_requires=requirements,
      entry_points={'console_scripts': ['roush = roush:main']},
      )
