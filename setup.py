#!/usr/bin/env python

import os
from setuptools import setup, find_packages

setup(name='pyAstroRef',
      version='0.0',
      description='A gui',
      license="GPLv2+",
      author='Robert Farmer',
      author_email='r.j.farmer@uva.edu',
      url='https://github.com/rjfarmer/pyAstroRef',
      packages=find_packages(),
      scripts=["bin/pyastroref"],
      data_files=[('icons',['icons/Feed-icon.png']),('icons',['icons/Generic_Feed-icon.svg'])],
      classifiers=[
			"Development Status :: 1 - Planning",
			"Intended Audience :: Science/Research",
			"License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
			"Topic :: Scientific/Engineering :: Astronomy",
      ]
     )
