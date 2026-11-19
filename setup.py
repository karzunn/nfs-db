from setuptools import setup, find_packages
from runpy import run_path

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

version = run_path("nfs_db/_version.py")["__version__"]

setup(
    name = 'nfs-db',
    version = version,
    author = "Carson O'Ffill",
    author_email = 'offillcarson@gmail.com',
    license = 'MIT',
    description = 'A database-like interface for your NFS',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/karzunn/nfs-db',
    packages = find_packages(exclude=("tests", "tests.*")),
    install_requires = requirements,
    python_requires='>=3.9',
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ]
)