#!/usr/bin/env python
"""
Sample script demonstrating how to use the PubmedParser to process large XML files.

This script:
1. Parses a PubMed XML file (gzipped)
2. Extracts article data
3. Saves each article as a separate JSON file
4. Provides progress tracking and error handling

Usage:
    python parse_pubmed_xml.py <input_xml_gz_file> <output_directory>

Example:
    python parse_pubmed_xml.py data/pubmed23n1181.xml.gz data/pubmed_json
"""
import logging
import os
import sys
import json
import time
import argparse
from tqdm import tqdm


# Add the parent directory to the path so we can import the src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.logging_config import configure_logging
from src.parsers.pubmed_parser import PubmedParser


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse PubMed XML files and save articles as JSON"
    )
    parser.add_argument(
        "input_file", help="Path to the input PubMed XML file (gzipped)"
    )
    parser.add_argument("output_dir", help="Directory to save the output JSON files")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=500,
        help="Maximum number of tokens in a split (default: 500)",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=100,
        help="Minimum number of tokens in a split (default: 100)",
    )
    parser.add_argument(
        "--sentence-overlap",
        type=int,
        default=2,
        help="Number of sentences to overlap between splits (default: 2)",
    )
    parser.add_argument(
        "--get-citations",
        action="store_true",
        help="Retrieve citation counts for articles (slower)",
    )
    parser.add_argument(
        "--get-journal-ranking",
        action="store_true",
        help="Retrieve journal ranking information (slower)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )
    parser.add_argument("--log-file", help="Path to log file (optional)")
    return parser.parse_args()


def main():
    """Main function to parse PubMed XML and save as JSON."""
    args = parse_arguments()

    # Configure logging
    configure_logging(level=args.log_level, log_file=args.log_file)
    logger = logging.getLogger(__name__)

    # Check if input file exists
    if not os.path.exists(args.input_file):
        logger.error("Input file '%s' does not exist", args.input_file)
        return 1

    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info("Created output directory: %s", args.output_dir)

    # Initialize the PubmedParser
    logger.info("Initializing PubmedParser...")
    pubmed = PubmedParser(
        max_split_token_length=args.max_tokens,
        min_split_token_length=args.min_tokens,
        sentence_overlap=args.sentence_overlap,
        get_citation_count_bool=args.get_citations,
        get_journal_ranking_bool=args.get_journal_ranking,
        log_level=args.log_level,
    )

    # Start parsing
    logger.info("Parsing %s...", args.input_file)
    start_time = time.time()

    # Get an iterator for the articles
    articles_iter = pubmed.parse_pubmed_xml_iter(args.input_file)

    # Process articles with progress tracking
    article_count = 0
    error_count = 0

    for article in tqdm(articles_iter, desc="Processing articles"):
        if article is None:
            error_count += 1
            continue

        # Get PMID and save as JSON
        pmid = article.get("pmid", f"unknown_{article_count}")
        output_file = os.path.join(args.output_dir, f"pubmed_{pmid}.json")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(article, f, ensure_ascii=False, indent=2)
            article_count += 1
        except Exception as e:
            logger.error("Error saving article %s: %s", pmid, e)
            error_count += 1

    # Print summary
    elapsed_time = time.time() - start_time
    logger.info("Processing complete in %.2f seconds", elapsed_time)
    logger.info("Successfully processed %d articles", article_count)
    if error_count > 0:
        logger.warning("Encountered errors with %d articles", error_count)

    return 0


if __name__ == "__main__":
    sys.exit(main())
