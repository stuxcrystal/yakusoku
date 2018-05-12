# -*- encoding: utf-8 -*-
#
# Copyright 2018 StuxCrystal <stuxcrystal@encode.moe>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from setuptools import setup, find_packages

setup(
    name='yakusoku',
    version='1.0.0',
    packages=find_packages(exclude='tests'),
    url='https://github.com/stuxcrystal/yakusoku',
    license='Apache License',
    author='stuxcrystal',
    author_email='stuxcrystal@encode.moe',
    description='A unified Future for Threading and AsyncIO',

    classifiers=[
        'Development Status :: 4 - Beta',

        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',

        'Framework :: AsyncIO',
        'Intended Audience :: Developers'
    ]
)
