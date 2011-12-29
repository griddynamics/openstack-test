#!/usr/bin/env python

import os
import sys
from setuptools import setup

version = '0.0.1'
name = os.path.basename(os.path.abspath('.'))


def get_packages():
    packages = []
    for root, dirnames, filenames in os.walk('bunch'):
        if '__init__.py' in filenames:
            packages.append(".".join(os.path.split(root)).strip("."))

    return packages

required_modules = ['lettuce', 'lettuce-bunch', 'pexpect']

setup(name=name,
      version=version,
      description='Grid Dynamics OpenStack Core test suite',
      author=u'Grid Dynamics',
      author_email='skosyrev@griddynamics.com',
      url='http://github.com/TODO',
      packages=get_packages(),
      install_requires=required_modules
      )
