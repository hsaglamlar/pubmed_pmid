"""This module contains the get_journal_ranking function for getting the journal ranking
of a journal based on the journal name using the exaly website https://exaly.com/journals/
"""

import logging
from urllib.parse import quote
from functools import lru_cache
from typing import Dict, Optional, Any, List

import requests
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

# Constants
EXALY_URL = "https://exaly.com/journals/"
SEARCH_URL = f"{EXALY_URL}?q="
DEFAULT_TIMEOUT = 15
DEFAULT_PARSER = "html.parser"  # Alternative: "lxml" if installed


@lru_cache(maxsize=128)
def get_journal_ranking(
    journal_name: Optional[str] = None, pmid: Optional[str] = None
) -> Dict[str, Any]:
    """Get the ranking of a journal based on the journal name using the exaly website.

    Args:
        journal_name: The full name of the journal
        pmid: PubMed ID (used for logging purposes)

    Returns:
        Dictionary containing the journal ranking info

    Examples:
        >>> get_journal_ranking("Nature")
        {'Journal': 'Nature', 'Impact Factor': '49.9', 'Citations': '4.2M', 'Articles': '8.9K'}

        >>> get_journal_ranking("")
        {}
    """
    # Validate input
    if not journal_name:
        logger.warning(
            "Journal name is empty, cannot get journal ranking for PMID %s", pmid
        )
        return {}

    logger.debug("Getting journal ranking for %s", journal_name)

    try:
        # Normalize journal name and prepare query
        normalized_name = journal_name.replace("&", "and")
        query = quote(normalized_name)
        url = f"{SEARCH_URL}{query}"

        # Send request
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)

        if response.status_code != 200:
            logger.warning(
                "Failed to get journal ranking for %s. Status code: %s",
                journal_name,
                response.status_code,
            )
            return {}

        # Parse response
        soup = BeautifulSoup(response.content, DEFAULT_PARSER)
        table = soup.find("table")

        if not table:
            logger.warning("No ranking table found for journal %s", journal_name)
            return {}

        # Extract table data
        table_data = _extract_table_data(table)

        if not table_data or len(table_data) < 2:
            logger.warning("Empty or invalid table data for journal %s", journal_name)
            return {}

        # Find exact match or use first result
        ranking = _find_journal_match(table_data, normalized_name)

        # Clean up ranking data
        if ranking:
            _clean_ranking_data(ranking)

        # convert K and M to numbers
        for key, value in ranking.items():
            if "K" in value:
                ranking[key] = int(float(value.replace("K", "")) * 1000)
            elif "M" in value:
                ranking[key] = int(float(value.replace("M", "")) * 1000000)
            
            if key == "Impact Factor":
                ranking[key] = float(value)

        return ranking

    except requests.exceptions.Timeout:
        logger.warning("Request timed out for journal %s", journal_name)
        return {}
    except requests.exceptions.RequestException as e:
        logger.warning("Request failed for journal %s: %s", journal_name, str(e))
        return {}
    except Exception as e:
        logger.warning("Unexpected error for journal %s: %s", journal_name, str(e))
        return {}


def _extract_table_data(table) -> List[List[str]]:
    """Extract data from HTML table.

    Args:
        table: BeautifulSoup table element

    Returns:
        List of rows, where each row is a list of cell values
    """
    table_data = []

    try:
        for row in table.find_all("tr"):
            row_data = []
            for cell in row.find_all(["th", "td"]):
                row_data.append(cell.get_text(strip=True))
            if row_data:
                table_data.append(row_data)
    except Exception as e:
        logger.error("Error extracting table data: %s", str(e))

    return table_data


def _find_journal_match(table_data, journal_name):
    """Find the best matching journal in the table data.

    Args:
        table_data: List of rows from the table
        journal_name: Journal name to match

    Returns:
        Dictionary with journal ranking data
    """
    if not table_data or len(table_data) < 2:
        return {}

    headers = table_data[0]

    # Try to find exact match
    for row in table_data[1:]:
        if row and len(row) >= len(headers):
            row_journal_name = row[0].replace("&", "and").lower()
            if row_journal_name == journal_name.lower():
                return dict(zip(headers, row))

    # If no exact match, use first result
    if len(table_data) > 1:
        return dict(zip(headers, table_data[1]))

    return {}


def _clean_ranking_data(ranking):
    """Clean up ranking data by removing unwanted characters.

    Args:
        ranking: Dictionary with journal ranking data

    Note:
        Modifies the dictionary in place
    """
    # Remove unnecessary columns
    for key in ["star", "#"]:
        if key in ranking:
            ranking.pop(key)
