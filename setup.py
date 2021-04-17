#!/usr/bin/env python

import os
from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='pyAstroRef',
      version='0.0',
      description="The astronomer's reference manager.",
      license="GPLv2+",
      author='Robert Farmer',
      author_email='r.j.farmer@uva.edu',
      url='https://github.com/rjfarmer/pyAstroRef',
      packages=find_packages(),
      scripts=["bin/pyastroref"],
      data_files = [
              ('share/applications', ['data/pyastroref.desktop']),
          ],
      include_package_data=True,
      long_description=readme(),
      classifiers=[
			"Development Status :: 3 - Alpha",
			"Intended Audience :: Science/Research",
			"License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
			"Topic :: Scientific/Engineering :: Astronomy",
      ]
     )
