pubmed_parser/
├── src/
│   ├── __init__.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── pubmed_parser.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   └── xml_extractors.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── pubmed_api.py
│   │   ├── citation_count.py
│   │   └── journal_ranking.py
│   └── utils/
│       ├── __init__.py
│       ├── article_splitter.py
│       └── detect_sentences.py
├── data/
│   ├── raw/
│   └── processed/
├── examples/
│   ├── example.ipynb
│   └── example_xml/
├── tests/
│   ├── __init__.py
│   ├── test_pubmed_parser.py
│   └── test_xml_extractors.py
├── .gitignore
├── requirements.txt
├── setup.py
└── README.md