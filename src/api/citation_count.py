"""This module contains the get_article_citation_count function for getting the citation count
of an article based on the DOI using the Crossref API (https://api.crossref.org/works/{doi}).
"""

from typing import Optional
from loguru import logger
import requests


# Constants
CROSSREF_API_URL = "https://api.crossref.org/works/"
DEFAULT_TIMEOUT = 15
DEFAULT_EMAIL = "mailto@mailto"  # Contact email for API requests


def get_article_citation_count(
    doi: str = None, pmid: Optional[str] = None
) -> Optional[int]:
    """Get the citation count of an article based on the DOI using the Crossref API.

    Args:
        doi: The DOI (Digital Object Identifier) of the article
        pmid: The PubMed ID of the article (used for logging if DOI is missing)

    Returns:
        The citation count of the article as an integer, or None if the count couldn't be retrieved

    Examples:
        >>> get_article_citation_count("10.1038/s41586-020-2649-2")
        42
        >>> get_article_citation_count(doi=None, pmid="32698345")
        None
    """
    # Validate DOI
    if not doi:
        logger.warning(f"DOI is empty, cannot get citation count for PMID {pmid}")
        return None

    # Prepare request parameters
    params = {"mailto": DEFAULT_EMAIL}
    url = f"{CROSSREF_API_URL}{doi}"
    
    logger.debug(f"Requesting citation count for DOI {doi} (PMID {pmid})")

    try:
        # Make API request with timeout
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)

        # Check if request was successful
        if response.status_code != 200:
            logger.warning(
                f"Failed to get citation count for DOI {doi} (PMID {pmid}). Status code: {response.status_code}"
            )
            return None

        # Parse response data
        data = response.json()

        # Extract citation count from response
        if "message" in data and "is-referenced-by-count" in data["message"]:
            citation_count = data["message"]["is-referenced-by-count"]
            logger.debug(f"Retrieved citation count for DOI {doi}: {citation_count}")
            return citation_count
        else:
            logger.warning(f"Citation count not found in response for DOI {doi} (PMID {pmid})")
            return None

    except requests.exceptions.Timeout:
        logger.warning(f"Request timed out for DOI {doi} (PMID {pmid})")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed for DOI {doi} (PMID {pmid}): {str(e)}")
        return None
    except ValueError as e:
        logger.warning(f"Failed to parse JSON response for DOI {doi} (PMID {pmid}): {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error for DOI {doi} (PMID {pmid}): {str(e)}")
        return None
