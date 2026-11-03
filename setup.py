from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name = 'nfs-db',
    version = '1.0.0',
    author = "Carson O'Ffill",
    author_email = 'offillcarson@gmail.com',
    license = 'MIT',
    description = 'A database-like interface for your NFS',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/karzunn/nfs-db',
    py_modules = ['nfs_db'],
    packages = find_packages(),
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