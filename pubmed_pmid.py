"""This module contains the PubmedPMID class for generating a JSON object for a PubMed article.
The JSON object contains the abstract of the article and the meta information of the article such as the article
title, authors, journal info, etc. The JSON object also contains the article splits
which are the abstract split into paragraphs of max_split_token_length &
min_split_token_length tokens with an overlap of sentence_overlap sentences.

Example:
    >>> from pubmed_pmid import PubmedPMID
    >>> pubmed_pmid = PubmedPMID()
    >>> json_output = pubmed_pmid.build_pubmed_json(xml_path="data/36464825.xml")
    >>> print(json_output)

    or with large gz files:
    >>> from pubmed_pmid import PubmedPMID
    >>> pubmed_pmid = PubmedPMID()
    >>> dicts_out = pubmed.parse_pubmed_xml_iter("data/pubmed23n1166.xml.gz")

    >>> for article in dicts_out:
    >>>     if article is None:
    >>>         continue
    >>>     pmid = article["pmid"]
    >>>     with open(f"./data/pubmed/pubmed_{pmid}.json", "w") as f:
    >>>         json.dump(article, f)


Some codes are adapted from https://github.com/titipata/pubmed_parser
"""
import re
from urllib.parse import quote
from itertools import chain

import gzip

import requests
from lxml import etree

from bs4 import BeautifulSoup
import tiktoken


class PubmedPMID:
    """Class for generating a JSON object for a PubMed article. The JSON object contains
    the abstract of the article and the meta information of the article such as the article
    title, authors, journal info, etc. The JSON object also contains the article splits
    which are the abstract split into paragraphs of max_split_token_length & 
    min_split_token_length tokens with an overlap of sentence_overlap sentences.

    Args:
        max_split_token_length (int, optional): The maximum number of tokens in a split. Defaults to 500.
        min_split_token_length (int, optional): The minimum number of tokens in a split. Defaults to 100.
        sentence_overlap (int, optional): The number of sentences to overlap between splits. Defaults to 2.
        get_citation_count (bool, optional): Whether to get the citation count of the article. Defaults to False.
        get_journal_ranking (bool, optional): Whether to get the ranking of the journal. Defaults to False.


    Attributes:
        json_output (dict): The JSON object for the article
        max_split_token_length (int): The maximum number of tokens in a split
        min_split_token_length (int): The minimum number of tokens in a split
        sentence_overlap (int): The number of sentences to overlap between splits
        journal_ranking_dict (dict): A cache  dictionary of journal ranking info
        get_citation_count (bool): Whether to get the citation count of the article
        get_journal_ranking (bool): Whether to get the ranking of the journal
    """

    def __init__(
        self,
        max_split_token_length: int = 500,
        min_split_token_length: int = 100,
        sentence_overlap: int = 2,
        get_citation_count: bool = False,
        get_journal_ranking: bool = False,
    ):
        self.max_split_token_length = max_split_token_length
        self.sentence_overlap = sentence_overlap
        self.min_split_token_length = min_split_token_length
        self.citation_count_bool = get_citation_count
        self.journal_ranking_bool = get_journal_ranking
        self.journal_ranking_dict = {}

    def get_pubmed_article_xml(self, pmid=None):
        """Get the PubMed article XML from the PMID and return it as a string
        Args:
            pmid (str): The PMID of the article
        Returns:
            str: The XML of the article"""

        # check if the pmcid is valid
        if pmid in ["", None]:
            raise ValueError("PMCID is empty")

        params = {
            "db": "pubmed",
            "id": f"[{pmid}]",
            "rettype": "xml",
        }

        try:
            # Send the request to the NCBI
            response = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            xml_data = response.text
            return xml_data

        except requests.exceptions.RequestException as exception:
            print(f"An error occurred: {exception}")
            return None

    def __stringify_children(self, node):
        """
        Filters and removes possible Nones in texts and tails
        ref: http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
        """
        parts = (
            [node.text]
            + list(chain(*([c.text, c.tail] for c in node.getchildren())))
            + [node.tail]
        )
        return "".join(filter(None, parts)).strip()

    def get_abstract(self, xml_tree):
        """Get the abstract text from the XML tree of the article
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            dict: A dictionary containing the abstract text, section title and section type
        """

        article = xml_tree.find(".//MedlineCitation/Article")
        category = "Label"
        if article.find("Abstract/AbstractText") is not None:
            # parsing structured abstract
            if len(article.findall("Abstract/AbstractText")) > 1:
                abstract_list = list()
                for abstract in article.findall("Abstract/AbstractText"):
                    section = abstract.attrib.get(category, "")
                    if section != "UNASSIGNED":
                        abstract_list.append("\n")
                        abstract_list.append(abstract.attrib.get(category, "") + ":")

                    section_text = self.__stringify_children(abstract)
                    abstract_list.append(section_text)
                abstract = "\n".join(abstract_list)
            else:
                abstract = (
                    self.__stringify_children(article.find("Abstract/AbstractText"))
                    or ""
                )
        elif article.find("Abstract") is not None:
            abstract = self.__stringify_children(article.find("Abstract")) or ""
        else:
            abstract = ""

        if abstract.strip() == "":
            return None
        else:
            return {
                "text": abstract,
                "section_title": "Abstract",
                "section_type": "ABSTRACT",
            }

    def get_article_ids(self, xml_tree):
        """Get the article IDs from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            list: A list of dictionaries containing the article IDs and their id types
        """

        article_ids = []
        article_id_list = xml_tree.findall(".//PubmedData/ArticleIdList/ArticleId")
        if article_id_list is not None:
            for article_id in article_id_list:
                article_ids.append(
                    {
                        "idtype": article_id.attrib.get("IdType", ""),
                        "value": article_id.text,
                    }
                )
        return article_ids

    def get_keywords(self, xml_tree):
        """Get the keywords from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            str: A string of comma ``,`` separated keywords
        """
        keywords = []
        keyword_list = xml_tree.findall(".//KeywordList/Keyword")
        if keyword_list is not None:
            for keyword in keyword_list:
                keywords.append(keyword.text or "")

        return ", ".join(keywords)

    def get_dates_history(self, xml_tree):
        """Get the dates from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            list: A list of dictionaries containing the date type, year, month and day
        """
        dates = []
        date_list = xml_tree.findall(".//PubmedData/History/PubMedPubDate")
        if date_list is not None:
            for date in date_list:
                dates.append(
                    {
                        "date_type": date.attrib.get("PubStatus", ""),
                        "year": date.find("Year").text,
                        "month": date.find("Month").text,
                        "day": date.find("Day").text,
                    }
                )
        return dates

    def get_journal_info(self, xml_tree):
        """Get the journal info from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            dict: A dictionary containing the journal name, 
                  journal abbreviation, ISSN and publication date
        """
        journal_info = {}
        journal = xml_tree.find(".//MedlineCitation/Article/Journal")

        if journal is not None:
            # Get the journal full name
            title = journal.find("Title")
            if title is not None:
                journal_info["fulljournalname"] = title.text or ""

            # Get the journal abbreviation name
            abbrev = journal.find("ISOAbbreviation")
            if abbrev is not None:
                journal_info["journal_abbrev"] = abbrev.text or ""

            # Get the journal ISSN
            issn = journal.find("ISSN")
            if issn is not None:
                journal_info["issn"] = issn.text or ""

            # Get the journal publication date
            date = journal.find("JournalIssue/PubDate")
            if date is not None:
                year = date.find("Year")
                year_text = ""
                if year is not None:
                    year_text = year.text

                month = date.find("Month")
                month_text = ""
                if month is not None:
                    month_text = month.text

                day = date.find("Day")
                day_text = ""
                if day is not None:
                    day_text = day.text
                journal_info["pubdate"] = f"{year_text} {month_text} {day_text}".strip()

        return journal_info

    def get_article_info(self, xml_tree):
        """Get the article info from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            dict: A dictionary containing the article title, volume, issue and pages
        """

        article = xml_tree.find(".//MedlineCitation/Article")
        article_info = {}

        # Get the article title
        article_info["title"] = ""
        if article.find("ArticleTitle") is not None:
            article_info["title"] = (
                self.__stringify_children(article.find("ArticleTitle")) or ""
            )

        # Get the article language
        article_info["languages"] = ""
        if article.find("Language") is not None:
            article_info["languages"] = ";".join(
                [language.text for language in article.findall("Language")]
            )

        # Get the article volume
        volume = article.find("Journal/JournalIssue/Volume")
        article_info["volume"] = ""
        if volume is not None:
            article_info["volume"] = volume.text or ""

        # Get the article issue
        issue = article.find("Journal/JournalIssue/Issue")
        article_info["issue"] = ""
        if issue is not None:
            article_info["issue"] = issue.text or ""

        # Get the article pages
        pages = article.find("Pagination/MedlinePgn")
        article_info["pages"] = ""
        if pages is not None:
            article_info["pages"] = pages.text or ""

        # Get the article publication type
        type_infos = article.findall("PublicationTypeList/PublicationType")
        article_info["publication_type"] = ""
        if len(type_infos) > 0:
            article_info["publication_type"] = [( type_info.attrib.get('UI',None), type_info.text) for type_info in type_infos]
            

        return article_info

    def get_authors(self, xml_tree):
        """Get the authors from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            list: A list of dictionaries containing the first name, middle name, 
                  last name, suffix, initials, affiliation and email
        """

        authors = []
        author_list = xml_tree.findall(".//AuthorList/Author")
        if author_list is not None:
            for author in author_list:
                authors.append(
                    {
                        "first": author.find("ForeName").text
                        if author.find("ForeName") is not None
                        else "",
                        "middle": "",
                        "last": author.find("LastName").text
                        if author.find("LastName") is not None
                        else "",
                        "suffix": "",
                        "initials": author.find("Initials").text
                        if author.find("Initials") is not None
                        else "",
                        "affiliation": self.__stringify_children(
                            author.find("AffiliationInfo/Affiliation")
                        )
                        if author.find("AffiliationInfo/Affiliation") is not None
                        else "",
                        "email": "",
                    }
                )
        return authors

    def parse_mesh_terms_with_subs(self, xml_tree):
        """
        Parse the mesh terms with subheadings from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            str: A string of semicolon ``;`` separated mesh terms with subheadings
        """

        mesh = xml_tree.find(".//MedlineCitation/MeshHeadingList")
        if mesh is not None:
            mesh_terms_list = []
            for m in mesh.getchildren():
                descriptor_name = m.find("DescriptorName")
                term = descriptor_name.attrib.get("UI", "") + ":" + descriptor_name.text
                if descriptor_name.attrib.get("MajorTopicYN", "") == "Y":
                    term += "*"
                for q in m.findall("QualifierName"):
                    term += " / " + q.attrib.get("UI", "") + ":" + q.text
                    if q.attrib.get("MajorTopicYN", "") == "Y":
                        term += "*"
                mesh_terms_list.append(term)
            mesh_terms = "; ".join(mesh_terms_list)
        else:
            mesh_terms = ""
        return mesh_terms

    def get_article_citation_count(self, doi=None):
        """Get the citation count of an article based on the DOI using the crossref website
        https://api.crossref.org/works/{doi}

        Args:
            doi (str): The DOI of the article
        Returns:
            int: The citation count of the article
        """

        if doi in ["", None]:
            print("DOI is empty, cannot get citation count")
            return None
        params = {"mailto": "halil@johnsnowlabs.com"}
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        if (response.status_code == 200) and (
            "is-referenced-by-count" in data["message"]
        ):
            return data["message"]["is-referenced-by-count"]

        return None

    def get_journal_ranking(self, journal_name=None):
        """Get the ranking of a journal based on the journal name using the exaly website
        https://exaly.com/journals/if/1?q=

        Args:
            journal_name (str): The full name of the journal
        Returns:
            dict: A dictionary containing the journal ranking info
        """

        if journal_name in ["", None]:
            print("Journal name is empty, cannot get journal ranking")
            return {}

        if journal_name in self.journal_ranking_dict:
            return self.journal_ranking_dict[journal_name]

        query = quote(journal_name.replace("&", "and"))

        # URL of the webpage containing the table
        url = f"https://exaly.com/journals/if/1?q={query}"

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

                _ = ranking.pop("star")  # remove the star column

                # add the journal name to the dictionary
                self.journal_ranking_dict[journal_name] = ranking
            else:
                ranking = {}
        else:
            ranking = {}

        return ranking

    def get_sentences(self, content):
        """Get the sentences from the content and return them as a list"""

        formater = Formater()
        _UNPROTECTED_BREAK_INDICATOR = "(?![^]*)"

        content_modified = formater.generate_protecedContent(content)

        list_sentences = re.split(_UNPROTECTED_BREAK_INDICATOR, content_modified)

        list_sentences = [
            sentence.replace(BREAK_INDICATOR, "") for sentence in list_sentences
        ]
        list_sentences = [
            sentence.replace(BREAK_INDICATOR, "") for sentence in list_sentences
        ]

        def recover_senctence(sentence: str):
            wip_sentence = sentence
            for key, item in reverse_dict.items():
                wip_sentence = wip_sentence.replace(key, item)
            return wip_sentence

        list_sentences = [recover_senctence(sentence) for sentence in list_sentences]
        list_sentences = [
            sentence.strip() for sentence in list_sentences if sentence.strip() != ""
        ]

        return list_sentences

    def split_article_paragraphs(self, json_data):
        """Split the article into paragraphs of max_token_length & min_token_length tokens
        with an overlap of sentence_overlap sentences"""

        def group_sentences(sentences, max_tokens, overlap_length):
            """Group sentences into groups of max_tokens tokens 
            with an overlap of overlap_length sentences"""
            grouped_sentences = []
            current_group = []
            grouped_sentences_lengths = []
            token_count = 0
            tokenizer = tiktoken.get_encoding("p50k_base")

            for sentence in sentences:
                tokens = tokenizer.encode(sentence, disallowed_special=())
                sentence_length = len(tokens)

                if token_count + sentence_length <= max_tokens:
                    current_group.append(sentence)
                    token_count += sentence_length
                else:
                    grouped_sentences.append(current_group)
                    grouped_sentences_lengths.append(token_count)
                    current_group = current_group[
                        -overlap_length:
                    ]  # Start next group with the last overlap_length sentences
                    current_group.append(sentence)
                    token_count = sum(
                        len(tokenizer.encode(sent, disallowed_special=()))
                        for sent in current_group
                    )

            # Add the last group if it is not empty
            if current_group:
                grouped_sentences.append(current_group)
                grouped_sentences_lengths.append(token_count)

            return grouped_sentences, grouped_sentences_lengths

        abstract_text = json_data["abstract"][0].get("text", "")
        pmid = json_data["pmid"]

        if abstract_text != "" and pmid != "":
            sentences = self.get_sentences(abstract_text)
        else:
            return None

        article_splits = []

        # split the abstract
        if json_data["abstract"][0] is not None:
            split_id = 0
            splits, splits_lengths = group_sentences(
                sentences, self.max_split_token_length, self.sentence_overlap
            )

            #  add the splits to the splits list with the corresponding split_id and text
            split_list = []
            for i, split in enumerate(splits):
                # merge the split with previous split if it is less than min_split_token_length
                if (splits_lengths[i] > self.min_split_token_length) or (i == 0):
                    split_list.append(
                        {f"PMID{pmid}_abstract_split_{split_id}": " ".join(split)}
                    )
                    split_id += 1
                else:
                    # merge the split with previous split if it is less than min_split_token_length
                    # trim the split overlap_length sentences
                    previous_split = split_list[-1]
                    split_sentences = self.get_sentences(" ".join(split))
                    previous_split[list(previous_split.keys())[0]] += " ".join(split_sentences[self.sentence_overlap :])
            article_splits.extend(split_list)

        return article_splits

    def build_pubmed_json(self, xml_path=None, xml_tree=None):
        """Build the JSON object for the article
        Args:
            xml_path (str): The path to the XML file of the article
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            dict: A dictionary containing the JSON object for the article
        """

        # Get the XML tree for the article if path is provided
        if xml_path is not None:
            xml_tree = etree.parse(xml_path)
        # Get the abstract text
        abstract = self.get_abstract(xml_tree)

        # Return None if the abstract is empty
        if abstract is None:
            return None

        # Build the JSON object
        json_output = {
            "abstract": [abstract],
            "meta_info": {
                "articleids": self.get_article_ids(xml_tree),
                "kwd": self.get_keywords(xml_tree),
                "dates_history": self.get_dates_history(xml_tree),
                **self.get_journal_info(xml_tree),
                **self.get_article_info(xml_tree),
                "authors": self.get_authors(xml_tree),
                "mesh_terms": self.parse_mesh_terms_with_subs(xml_tree),
            },
        }

        journal_name = json_output["meta_info"].get("fulljournalname", "")

        doi = ""
        pmid = ""
        for id_item in json_output["meta_info"].get("articleids", []):
            if id_item["idtype"] == "doi":
                doi = id_item["value"]
            elif id_item["idtype"] == "pubmed":
                pmid = id_item["value"]

        json_output["pmid"] = pmid

        # Get the article splits
        json_output["article_splits"] = self.split_article_paragraphs(json_output)

        # Get the citation count of the article
        if self.citation_count_bool:
            json_output["meta_info"][
                "citation_count"
            ] = self.get_article_citation_count(doi)

        # # Get the journal ranking info
        if self.journal_ranking_bool:
            json_output["meta_info"]["journal_ranking"] = self.get_journal_ranking(
                journal_name
            )

        return json_output

    def parse_pubmed_xml_iter(self, path):
        """Parse the XML file of the article and yield the JSON object for the article
        Args:
            path (str): The path to the XML GZ file of the article
        Yields:
            dict: A dictionary containing the JSON object for the article
        """
        with gzip.open(path, "rb") as f:
            for _, element in etree.iterparse(f, events=("end",)):
                if element.tag == "PubmedArticle":
                    res = self.build_pubmed_json(xml_tree=element)
                    element.clear()
                    yield res


# Constants for the unicode characters used in sentence detection
PUNCT_INDICATOR = "╚"
ELLIPSIS_INDICATOR = "╦"
ABBREVIATOR = "╞"
NUM_INDICATOR = "╟"
MULT_PERIOD = "╔"
SPECIAL_PERIOD = "╩"
QUESTION_IN_QUOTE = "╤"
EXCLAMATION_INDICATOR = "╥"
BREAK_INDICATOR = "\uF050"
DOT = "\uF051"
COMMA = "\uF052"
SEMICOLON = "\uF053"
QUESTION = "\uF054"
EXCLAMATION = "\uF055"
PROTECTION_MARKER_OPEN = "\uF056"
PROTECTION_MARKER_CLOSE = "\uF057"
PROTECT_CHAR = "ↈ"
BREAK_CHAR = "ↇ"

reverse_dict = {
    DOT: ".",
    SEMICOLON: ";",
    QUESTION: "?",
    EXCLAMATION: "!",
    PROTECTION_MARKER_OPEN: "",
    PROTECTION_MARKER_CLOSE: "",
    ABBREVIATOR: ".",
    NUM_INDICATOR: ".",
    MULT_PERIOD: ".",
    QUESTION_IN_QUOTE: "?",
    EXCLAMATION_INDICATOR: "!",
    ELLIPSIS_INDICATOR: "...",
}


class Formater:
    """A class used for sentence detection."""

    _PREPOSITIVE_ABBREVIATIONS = ["dr", "mr", "ms", "mt", "st"]
    _NUMBER_ABBREVIATIONS = ["no", "px"]

    _pabb = "(?:" + "|".join(_PREPOSITIVE_ABBREVIATIONS) + ")"
    _nubb = "(?:" + "|".join(_NUMBER_ABBREVIATIONS) + ")"

    _number_rules = [
        "(?<=\d)\.(?=\d)",
        "\.(?=\d)",
        "(?<=\d)\.(?=\S)",
        "(?<=^\d)\.(?=(\s\S)|\))",
        "(?<=^\d\d)\.(?=(\s\S)|\))",
    ]

    _ditc_abbr_rules = [
        rf"(?i)(?<=\s{_pabb})\.(?=\s)|(?<=^{_pabb})\.(?=\d+)",
        rf"(?i)(?<=\s{_pabb})\.(?=\d+)|(?<=^{_pabb})\.(?=\d+)",
        rf"(?i)(?<=\s{_nubb})\.(?=s\\d)|(?<=^{_nubb})\.(?=s\\d)",
        rf"(?i)(?<=\s{_nubb})\.(?=:\s+\()|(?<=^{_nubb})\.(?=\s+\()",
    ]

    _std_abbre_rules = [
        "\.(?='s\s)|\.(?='s\$)|\.(?='s\Z)",
        "(?<=Co)\.(?=\sKG)",
        "(?<=^[A-Z])\.(?=\s)",
        "(?<=\s[A-Z])\.(?=\s)",
    ]

    _specials_abbr_rules = [
        r"\b[a-zA-Z](?:\.[a-zA-Z])+(?:\.(?!\s[A-Z]))*",
        r"(?i)p\.m\.*",
        r"(?i)a\.m\.",
    ]

    _punctuations_rules = ["(?<=\S)[!\?]+(?=\s|\Z|\$)"]

    _multiple_periods_rules = ["(?<=\w)\.(?=\w)"]

    _geolocations_rules = ["(?<=[a-zA-z]°)\.(?=\s*\d+)"]

    _ellipsis_rules = [
        "\.\.\.(?=\s+[A-Z])",
        "(?<=\S)\.{3}(?=\.\s[A-Z])",
    ]

    _between_punctuations_rules = [
        "(?<=\s|^)'[\w\s?!\.,|'\w]+'(?:\W)",
        '"[\w\s?!\.,]+"',
        "\[[\w\s?!\.,]+\]",
        "\([\w\s?!\.,]+\)",
    ]

    _queation_mark_inquation_rules = ["\?(?=('|\"))"]

    _exclamations_rules = ["\!(?=('|\"))", "\!(?=\,\s[a-z])", "\!(?=\s[a-z])"]

    _basic_rules = {DOT: "\.", SEMICOLON: ";"}

    def _replace_rules(self, content: str, simbol: str, rules: list):
        for rule in rules:
            content = re.sub(rule, simbol, content)
        return content

    def _replace_break_and_symbolic(self, content: str, rules: dict):
        for key, rule in rules.items():
            content = re.sub(rule, key + BREAK_INDICATOR, content)
        return content

    def _replace_with_all_simbols(self, content: str, simbol: str, rules: list):
        return self._replace_rules(content, simbol, rules)

    def _replace_with_all_simbols_and_breaks(
        self, content: str, simbol: str, rules: list
    ):
        return self._replace_rules(content, simbol + BREAK_INDICATOR, rules)

    def _replace_with_protect_breaks(self, content: str, rules: list):
        return self._replace_rules(
            content, PROTECTION_MARKER_OPEN + "\g<0>" + PROTECTION_MARKER_CLOSE, rules
        )

    def _replace_with_appendl(self, content: str, simbol: str, rules: list):
        return self._replace_rules(content, "\g<0>" + simbol, rules)

    def formatNumbers(self, text: str):
        return self._replace_with_all_simbols(
            text, NUM_INDICATOR, Formater._number_rules
        )

    def formatAbbreviations(self, text: str):
        # There are logic in open source that could be wrong
        replacement = self._replace_with_protect_breaks(
            text, Formater._specials_abbr_rules
        )
        replacement = self._replace_with_all_simbols(
            replacement, ABBREVIATOR, Formater._std_abbre_rules
        )
        return self._replace_with_all_simbols(
            replacement, ABBREVIATOR, Formater._ditc_abbr_rules
        )

    def formatPunctuations(self, text: str):
        return self._replace_with_appendl(
            text, BREAK_INDICATOR, Formater._punctuations_rules
        )

    def formatEllipsisRules(self, text):
        return self._replace_with_all_simbols_and_breaks(
            text, ELLIPSIS_INDICATOR, Formater._punctuations_rules
        )

    def formatMultiplePeriods(self, text: str):
        return self._replace_with_all_simbols(
            text, MULT_PERIOD, Formater._multiple_periods_rules
        )

    def formatGeoLocations(self, text: str):
        return self._replace_with_all_simbols(
            text, MULT_PERIOD, Formater._geolocations_rules
        )

    def formatBetweenPunctuations(self, text: str):
        # There are logic in open source that could be wrong
        return text

    def formatQuotationMarkInQuotation(self, text: str):
        return self._replace_with_all_simbols(
            text, QUESTION_IN_QUOTE, Formater._queation_mark_inquation_rules
        )

    def formatExclamationPoint(self, text: str):
        return self._replace_with_all_simbols(
            text, EXCLAMATION_INDICATOR, Formater._exclamations_rules
        )

    def formatBasicBreakers(self, text: str):
        return self._replace_break_and_symbolic(text, Formater._basic_rules)

    def generate_protecedContent(self, content):
        content_modified = self.formatNumbers(content)
        content_modified = self.formatAbbreviations(content_modified)
        content_modified = self.formatPunctuations(content_modified)
        content_modified = self.formatGeoLocations(content_modified)
        content_modified = self.formatMultiplePeriods(content_modified)
        content_modified = self.formatEllipsisRules(content_modified)
        content_modified = self.formatBetweenPunctuations(content_modified)
        content_modified = self.formatQuotationMarkInQuotation(content_modified)
        content_modified = self.formatExclamationPoint(content_modified)
        content_modified = self.formatBasicBreakers(content_modified)
        return content_modified
