# PubMed Parser

A Python package for parsing and processing PubMed articles from XML files.

## Overview

This package provides tools to extract structured data from PubMed XML articles, including metadata, abstracts, author information, and more. It can process individual articles or large batches of articles from the PubMed database.

## Features

- Extract comprehensive article metadata from PubMed XML
- Process individual articles or large gzipped XML files with multiple articles
- Split abstracts into configurable token-length chunks for NLP processing
- Optional retrieval of citation counts via Crossref API
- Optional retrieval of journal ranking information
- Export articles as structured JSON

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pubmed-parser.git
cd pubmed-parser

# Install dependencies
pip install -r requirements.txt

```

## Usage Examples

### Parse a Single Article by PMID

```python
from src.parsers.pubmed_parser import PubmedParser

# Initialize the parser
pubmed = PubmedParser()

# Get article data by PMID
article = pubmed.build_pubmed_json_from_pmid("36464825")
print(article["meta_info"]["title"])
```

### Process a Large XML File

```python
from src.parsers.pubmed_parser import PubmedParser
import json
import os

# Initialize the parser
pubmed = PubmedParser()

# Process articles from a large gzipped XML file
articles = pubmed.parse_pubmed_xml_iter("data/pubmed23n1181.xml.gz")

# Save each article as a separate JSON file
for article in articles:
    if article is None:
        continue
    
    pmid = article["pmid"]
    with open(f"data/processed/pubmed_{pmid}.json", "w") as f:
        json.dump(article, f)
```

### Command Line Interface

The package includes a command-line script for processing large XML files:

```bash
python examples/parse_pubmed_gzip_xml.py data/pubmed23n1181.xml.gz data/output_dir
```

## Documentation

For more detailed information, see the docstrings in the code or run the example notebook:

```bash
jupyter notebook examples/example.ipynb
```

## Project Structure

```
pubmed_parser/
├── src/
│   ├── parsers/       # Main parser implementation
│   ├── extractors/    # XML data extraction classes
│   ├── api/           # External API integrations
│   └── utils/         # Utility functions
├── examples/          # Example scripts and notebooks
├── tests/             # Unit tests
├── requirements.txt   # Dependencies
└── README.md          # This file
```

## Dependencies

- requests: For API interactions
- lxml: For XML parsing
- beautifulsoup4: For HTML parsing (journal rankings)
- tiktoken: For token counting
- spacy: For sentence detection
- loguru: For logging
- tqdm: For progress bars

## License

[MIT License](LICENSE)

