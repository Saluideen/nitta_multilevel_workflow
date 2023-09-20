from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in nitta_multilevel_workflow/__init__.py
from nitta_multilevel_workflow import __version__ as version

setup(
	name="nitta_multilevel_workflow",
	version=version,
	description="fsf",
	author="dfds",
	author_email="sf",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
