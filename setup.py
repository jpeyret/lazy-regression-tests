#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["timeout-decorator"]

setup_requirements = []

test_requirements = ["requests", "responses", "Jinja2", "jsonschema", "beautifulsoup4"]

setup(
    version="0.5.3",
    author="JL Peyret",
    author_email="jpeyret@gmail.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        # 2.x could come back, valuable for migrations,
        # but concentrating on 3.x for now
        # "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        # No 3.5, uses f-strings:
        #'Programming Language :: Python :: 3.5',
        "Programming Language :: Python :: 3.6",
        # should work, not tested:
        "Programming Language :: Python :: 3.7",
        # should work, not tested:
        "Programming Language :: Python :: 3.8",
    ],
    description="Easier automatic validation and regression testing",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="lazy_regression_tests",
    long_description_content_type="text/markdown",
    name="lazy_regression_tests",
    packages=find_packages(
        include=["lazy_regression_tests", "lazy_regression_tests.*"]
    ),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/jpeyret/lazy-regression-tests",
    zip_safe=False,
)
