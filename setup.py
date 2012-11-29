#!/usr/bin/env python

from setuptools import setup, find_packages

requirements = ['flask', 'sqlalchemy', 'sqlalchemy-migrate', 'gevent']


setup(name='roush',
      version='1.0.0',
      description='Roush API server',
      author='Justin Shepherd',
      author_email='jshephar@rackspace.com',
      url='',
      license='Apache',
      packages=find_packages(exclude=['tests', 'tests.*']),
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intented Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independant',
        'Programming Language :: Python',
        ],
      install_requires=requirements,
      entry_points={
        'console_scripts': ['roush = roush:main']
        }
      )
