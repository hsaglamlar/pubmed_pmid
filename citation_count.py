"""This module contains the get_article_citation_count function for getting the citation count
of an article based on the DOI using the crossref website https://api.crossref.org/works/{doi}
"""

import requests

URL = "https://api.crossref.org/works/"


def get_article_citation_count(doi=None, pmid=None):
    """Get the citation count of an article based on the DOI using the crossref website
    https://api.crossref.org/works/{doi}

    Args:
        doi (str): The DOI of the article
    Returns:
        int: The citation count of the article
    """

    if doi in ["", None]:
        print(f"DOI is empty, cannot get citation count for PMID {pmid}")
        return None
    params = {"mailto": "halil@johnsnowlabs.com"}
    url = f"{URL}{doi}"
    response = requests.get(url, params=params, timeout=15)
    data = response.json()

    if (response.status_code == 200) and ("is-referenced-by-count" in data["message"]):
        return data["message"]["is-referenced-by-count"]

    return None
