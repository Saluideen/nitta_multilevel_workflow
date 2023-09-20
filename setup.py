from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in nitta_note_app/__init__.py
from nitta_note_app import __version__ as version

setup(
	name="nitta_note_app",
	version=version,
	description="Application for Nitta Note Approval Digitization",
	author="Sajith K",
	author_email="sajith@ideenkreisetech.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
