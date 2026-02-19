# Build requires setuptools[core]
from setuptools import setup, find_packages

setup(
    name="bindecoder-colinhogben",
    version="0.1",
    description="Framework for decoding binary files",
    author="Colin Hogben",
    author_email="pypi@colinhogben.com",
    url="https://github.com/colinhogben/bindecoder/",
    packages=["bindecoder"],
    package_dir={"": "src"},
    )
