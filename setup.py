#!/usr/bin/env python

from setuptools import setup

required_modules = ['lettuce', 'pexpect']

setup(name='openstack-core-test',
      version='0.0.1',
      description='Grid Dynamics OpenStack Core test suite',
      author=u'Grid Dynamics',
      author_email='skosyrev@griddynamics.com',
      url='http://github.com/TODO',
      packages=['openstack_core_test', 'openstack_core_test.utils'],
      install_requires=required_modules
      )


