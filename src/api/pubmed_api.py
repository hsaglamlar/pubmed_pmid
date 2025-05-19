"""Module for interacting with the PubMed API."""

import logging
import requests

# Configure logging
logger = logging.getLogger(__name__)

PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def get_pubmed_article_xml(pmid: str, timeout: int = 15):
    """Get the PubMed article XML from the PMID.

    Args:
        pmid: The PubMed ID of the article
        timeout: Timeout for HTTP requests in seconds

    Returns:
        The XML of the article as a string, or None if retrieval failed

    Raises:
        ValueError: If PMID is empty
    """
    if not pmid:
        raise ValueError("PubMed ID is empty")

    params = {
        "db": "pubmed",
        "id": f"[{pmid}]",
        "rettype": "xml",
    }

    logger.debug("Requesting PubMed article XML for PMID %s", pmid)

    try:
        response = requests.get(
            PUBMED_API_URL,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        logger.debug("Successfully retrieved XML for PMID %s", pmid)
        return response.text

    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error retrieving PubMed article %s: %s", pmid, e)
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error("Connection error retrieving PubMed article %s: %s", pmid, e)
        return None
    except requests.exceptions.Timeout as e:
        logger.error("Timeout retrieving PubMed article %s: %s", pmid, e)
        return None
    except requests.exceptions.RequestException as e:
        logger.error("Error retrieving PubMed article %s: %s", pmid, e)
        return None
