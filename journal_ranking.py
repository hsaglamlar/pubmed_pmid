"""This module contains the get_journal_ranking function for getting the journal ranking
of a journal based on the journal name using the exaly website https://exaly.com/journals/
"""

from urllib.parse import quote
import requests

from bs4 import BeautifulSoup

URL = "https://exaly.com/journals/?q="


def get_journal_ranking(journal_name=None, pmid=None):
    """Get the ranking of a journal based on the journal name using the exaly website
    https://exaly.com/journals/if/1?q=

    Args:
        journal_name (str): The full name of the journal
    Returns:
        dict: A dictionary containing the journal ranking info
    """

    if journal_name in ["", None]:
        print(f"Journal name is empty, cannot get journal ranking for PMID {pmid}")
        return {}

    print(f"Getting journal ranking for {journal_name}")

    query = quote(journal_name.replace("&", "and"))

    # URL of the webpage containing the table
    url = f"{URL}{query}"

    # Send a GET request to the webpage
    response = requests.get(url, timeout=15)

    if response.status_code == 200:
        # Create a BeautifulSoup object to parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the table element on the webpage
        table = soup.find("table")
        ranking = None

        if table:
            # Extract the data from the table
            table_data = []
            for row in table.find_all("tr"):
                row_data = []
                for cell in row.find_all(["th", "td"]):
                    row_data.append(cell.get_text(strip=True))
                if row_data:
                    table_data.append(row_data)

            for row in table_data:
                if (
                    row[0].replace("&", "and").lower()
                    == journal_name.replace("&", "and").lower()
                ):
                    ranking = dict(zip(table_data[0], row))
                    break

            if ranking is None:
                # Create a dictionary from the first two rows of the table
                ranking = dict(zip(table_data[0], table_data[1]))

            if "star" in ranking:
                _ = ranking.pop("star")  # remove the star column

        else:
            ranking = {}
    else:
        ranking = {}

    return ranking
