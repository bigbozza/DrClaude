"""Setup script for Dr. Claude application."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="dr-claude",
    version="0.1.0",
    author="Dr. Claude Team",
    author_email="your.email@example.com",
    description="A therapeutic journaling application with LLM integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dr-claude",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dr-claude=src.main:main",
        ],
    },
)