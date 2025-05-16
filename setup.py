#!/usr/bin/env python3

"""
Setup script for Condor-Shirley-Bridge
Installs the condor_shirley_bridge package and its dependencies.

Part of the Condor-Shirley-Bridge project.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="condor-shirley-bridge",
    version="1.0.0",
    author="Juan Luis Gabriel",
    author_email="",
    description="A bridge between Condor Soaring Simulator and FlyShirley",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jlgabriel/ForeFlight-Shirley-Bridge",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyserial>=3.5",
        "websockets>=10.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Games/Entertainment :: Simulation",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "condor-shirley-bridge=condor_shirley_bridge.main:main",
        ],
    },
)
