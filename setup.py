# -*- coding: utf-8 -*-

from distutils.core import setup
from distutils.extension import Extension

setup(
    name='hamly',
    version='0.1',
    author='Victor Kotseruba',
    author_email='barbuzaster@gmail.com',
    license='MIT',
    packages=['hamly'],
    include_package_data=True,
    zip_safe=False,
    ext_modules=[Extension('hamly.escape_fast', ['hamly/escape_fast.c'])]
)
