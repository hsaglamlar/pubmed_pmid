"""Setup file for the PubMed Parser package."""

from setuptools import setup, find_packages

setup(
    name="pubmed_parser",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "lxml>=4.9.0",
        "beautifulsoup4>=4.11.0",
        "tiktoken>=0.3.0",
        "pandas>=1.5.0",
        "tqdm>=4.64.0",
        "spacy>=3.0.0",
    ],
    python_requires=">=3.7",
)
