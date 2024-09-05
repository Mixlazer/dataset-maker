from setuptools import setup, find_packages
from dataset_maker.version import __version__

with open("requirements.txt") as f:
    requirements = f.readlines()

setup(name="dataset_maker",
      version=__version__,
      packages=find_packages(),
      install_requires=requirements,
      include_package_data=True, )
