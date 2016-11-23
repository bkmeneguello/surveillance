#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='surveillance',
      version='1.0',
      description='Surveillance System',
      author='Bruno Meneguello',
      author_email='bruno@meneguello.com',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['pyyaml', 'numpy', 'Pillow', 'Jinja2', 'statsd']
      )
