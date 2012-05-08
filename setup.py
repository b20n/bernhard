# -*- coding: utf-8 -

import os
import sys

from setuptools import setup

setup(
    name = 'bernhard',
    version = '0.0.2',

    description = 'Python client for Riemann',
    long_description = file(
        os.path.join(
            os.path.dirname(__file__),
            'README.md'
        )
    ).read(),
    author = 'Benjamin Anderspn',
    author_email = 'b@banjiewen.net',
    license = 'ASF2.0',
    url = 'http://github.com/banjiewen/bernhard.git',

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Internet :: Log Analysis',
        'Topic :: Utilities',
        'Topic :: System :: Networking :: Monitoring'
    ],
    zip_safe = False,
    packages = ['bernhard'],
    include_package_data = True,
    install_requires=['protobuf']
)
