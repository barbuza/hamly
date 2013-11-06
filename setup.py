# -*- coding: utf-8 -*-

import sys
from setuptools import setup, Extension

if sys.version_info[0] < 3:
    requires = ['pyparsing==1.5.7', 'pydot', 'astmonkey', 'six']
else:
    requires = ['codegen', 'six']

setup(
    name='hamly',
    description='fast haml for python',
    keywords='web template haml',
    version='0.1.1',
    author='Victor Kotseruba',
    author_email='barbuzaster@gmail.com',
    license='MIT',
    packages=['hamly'],
    install_requires=requires,
    include_package_data=True,
    zip_safe=False,
    ext_modules=[Extension('hamly.escape_fast', ['hamly/escape_fast.c'])]
)
