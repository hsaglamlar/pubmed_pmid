"""This module contains the PubmedParser class for generating a JSON object for a PubMed article.
The JSON object contains the abstract of the article and the meta information of the article
such as the article title, authors, journal info, etc. The JSON object also contains
the article splits which are the abstract split into paragraphs of max_split_token_length &
min_split_token_length tokens with an overlap of sentence_overlap sentences.

Example:
    >>> from pubmed_parser import PubmedParser
    >>> pubmed = PubmedParser()
    >>> json_output = pubmed.build_pubmed_json(xml_path="data/36464825.xml")
    >>> print(json_output)

    or with large gz files:
    >>> from pubmed_parser import PubmedParser
    >>> pubmed = PubmedParser()
    >>> dicts_out = pubmed.parse_pubmed_xml_iter("data/pubmed23n1166.xml.gz")

    >>> for article in dicts_out:
    >>>     if article is None:
    >>>         continue
    >>>     pmid = article["pmid"]
    >>>     with open(f"./data/pubmed/pubmed_{pmid}.json", "w") as f:
    >>>         json.dump(article, f)

Some code adapted from https://github.com/titipata/pubmed_parser
"""

import gzip
from typing import Dict, Optional, Any
from loguru import logger
from lxml import etree  # pylint: disable=import-error
import tiktoken  # pylint: disable=import-error

# Import from new modules
from src.api.pubmed_api import get_pubmed_article_xml
from src.extractors.xml_extractors import (
    AbstractExtractor,
    ArticleInfoExtractor,
    JournalInfoExtractor,
    AuthorExtractor,
    MeshTermsExtractor,
)
from src.utils.article_splitter import split_article_paragraphs
from src.api.citation_count import get_article_citation_count
from src.api.journal_ranking import get_journal_ranking


class PubmedParser:
    """Parser for PubMed articles.

    This class provides methods to parse PubMed articles from XML files or PMIDs.
    It can extract article metadata, abstract, and other information.

    Attributes:
        max_split_token_length: Maximum number of tokens in a split
        min_split_token_length: Minimum number of tokens in a split
        sentence_overlap: Number of sentences to overlap between splits
        citation_count_bool: Whether to get citation count
        journal_ranking_bool: Whether to get journal ranking
        journal_ranking_dict: Cache dictionary of journal ranking info
        timeout: Timeout for HTTP requests in seconds
    """

    PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        max_split_token_length: int = 500,
        min_split_token_length: int = 100,
        sentence_overlap: int = 2,
        get_citation_count_bool: bool = False,
        get_journal_ranking_bool: bool = False,
        timeout: int = 15,
    ):
        """Initialize the PubmedParser.

        Args:
            max_split_token_length: Maximum number of tokens in a split. Defaults to 500.
            min_split_token_length: Minimum number of tokens in a split. Defaults to 100.
            sentence_overlap: Number of sentences to overlap between splits. Defaults to 2.
            get_citation_count_bool: Whether to get citation count. Defaults to False.
            get_journal_ranking_bool: Whether to get journal ranking. Defaults to False.
            timeout: Timeout for HTTP requests in seconds. Defaults to 15.
        """
        self.max_split_token_length = max_split_token_length
        self.min_split_token_length = min_split_token_length
        self.sentence_overlap = sentence_overlap
        self.citation_count_bool = get_citation_count_bool
        self.journal_ranking_bool = get_journal_ranking_bool
        self.journal_ranking_dict = {}
        self.timeout = timeout
        self._tokenizer = tiktoken.get_encoding("p50k_base")

        # Initialize extractors
        self.abstract_extractor = AbstractExtractor()
        self.article_info_extractor = ArticleInfoExtractor()
        self.journal_info_extractor = JournalInfoExtractor()
        self.author_extractor = AuthorExtractor()
        self.mesh_terms_extractor = MeshTermsExtractor()

    def get_pubmed_article_xml(self, pmid: str) -> Optional[str]:
        """Get the PubMed article XML from the PMID.

        Args:
            pmid: The PubMed ID of the article

        Returns:
            The XML of the article as a string, or None if retrieval failed

        Raises:
            ValueError: If PMID is empty
        """
        return get_pubmed_article_xml(pmid, self.timeout)

    def build_pubmed_json(
        self, xml_path: Optional[str] = None, xml_tree=None
    ) -> Optional[Dict[str, Any]]:
        """Build JSON object for a PubMed article.

        Args:
            xml_path: Path to XML file (optional)
            xml_tree: XML tree object (optional)

        Returns:
            Dictionary containing article data, or None if no abstract

        Note:
            Either xml_path or xml_tree must be provided
        """

        # Parse XML if path is provided
        if xml_path is not None:
            try:
                xml_tree = etree.parse(xml_path)  # type: ignore
            except Exception as e:  # type: ignore
                logger.error(f"Error parsing XML file {xml_path}: {e}")
                return None

        if xml_tree is None:
            logger.error("No XML data provided")
            return None

        try:
            # Get abstract
            abstract = self.abstract_extractor.get_abstract(xml_tree)
            if abstract is None:
                logger.debug("No abstract found in XML")
                # Continue processing even without abstract
                abstract = {
                    "text": "",
                    "section_title": "Abstract",
                    "section_type": "ABSTRACT",
                }

            # Extract article IDs first to get PMID for better error messages
            article_ids = self.article_info_extractor.get_article_ids(xml_tree)
            pmid = ""
            doi = ""
            for id_item in article_ids:
                if id_item["idtype"] == "doi":
                    doi = id_item["value"]
                elif id_item["idtype"] == "pubmed":
                    pmid = id_item["value"]

            # Build JSON object with error handling for each component
            json_output = {
                "abstract": [abstract],
                "meta_info": {
                    "articleids": article_ids,
                },
                "pmid": pmid,
            }

            # Add keywords with error handling
            try:
                json_output["meta_info"]["kwd"] = (
                    self.article_info_extractor.get_keywords(xml_tree)
                )
            except Exception as e:
                logger.warning(
                    f"Error extracting keywords for PMID {pmid or 'unknown'}: {e}"
                )
                json_output["meta_info"]["kwd"] = []

            # Add dates history with error handling
            try:
                json_output["meta_info"]["dates_history"] = (
                    self.article_info_extractor.get_dates_history(xml_tree)
                )
            except Exception as e:
                logger.warning(
                    f"Error extracting dates history for PMID {pmid or 'unknown'}: {e}"
                )
                json_output["meta_info"]["dates_history"] = []

            # Add journal info with error handling
            try:
                journal_info = self.journal_info_extractor.get_journal_info(xml_tree)
                json_output["meta_info"].update(journal_info)
            except Exception as e:
                logger.warning(
                    f"Error extracting journal info for PMID {pmid or 'unknown'}: {e}"
                )

            # Add article info with error handling
            try:
                article_info = self.article_info_extractor.get_article_info(xml_tree)
                json_output["meta_info"].update(article_info)
            except Exception as e:
                logger.warning(
                    f"Error extracting article info for PMID {pmid or 'unknown'}: {e}"
                )

            # Add authors with error handling
            try:
                json_output["meta_info"]["authors"] = self.author_extractor.get_authors(
                    xml_tree
                )
            except Exception as e:
                logger.warning(
                    f"Error extracting authors for PMID {pmid or 'unknown'}: {e}"
                )
                json_output["meta_info"]["authors"] = []

            # Add mesh terms with error handling
            try:
                json_output["meta_info"]["mesh_terms"] = (
                    self.mesh_terms_extractor.parse_mesh_terms_with_subs(xml_tree)
                )
            except Exception as e:
                logger.warning(
                    f"Error extracting mesh terms for PMID {pmid or 'unknown'}: {e}"
                )
                json_output["meta_info"]["mesh_terms"] = ""

            # Get the article splits with error handling
            try:
                json_output["article_splits"] = split_article_paragraphs(
                    json_output,
                    self.max_split_token_length,
                    self.min_split_token_length,
                    self.sentence_overlap,
                )
            except Exception as e:
                logger.warning(
                    f"Error splitting article for PMID {pmid or 'unknown'}: {e}"
                )
                json_output["article_splits"] = []

            # Get the citation count of the article
            if self.citation_count_bool:
                try:
                    json_output["meta_info"]["citation_count"] = (
                        get_article_citation_count(doi, pmid)
                    )
                except Exception as e:
                    logger.warning(
                        f"Error getting citation count for PMID {pmid or 'unknown'}: {e}"
                    )
                    json_output["meta_info"]["citation_count"] = None

            # Get the journal ranking info
            if self.journal_ranking_bool:
                try:
                    journal_name = json_output["meta_info"].get("fulljournalname", "")
                    json_output["meta_info"]["journal_ranking"] = get_journal_ranking(
                        journal_name, pmid
                    )
                except Exception as e:
                    logger.warning(
                        f"Error getting journal ranking for PMID {pmid or 'unknown'}: {e}"
                    )
                    json_output["meta_info"]["journal_ranking"] = None

            if abstract["text"] == "":
                logger.info(f"No abstract found in pubmed article {pmid}")

            return json_output

        except Exception as e:
            logger.error(
                f"Unexpected error processing XML for PMID {pmid or 'unknown'}: {e}"
            )
            return None

    def build_pubmed_json_from_pmid(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Build JSON object for a PubMed article using its PMID.

        This method fetches the article XML from PubMed API and then builds
        the JSON representation.

        Args:
            pmid: PubMed ID of the article

        Returns:
            Dictionary containing article data, or None if retrieval failed
            or no abstract was found

        Examples:
            >>> parser = PubmedParser()
            >>> article = parser.build_pubmed_json_from_pmid("36464825")
            >>> print(article["pmid"])
            36464825
        """
        if not pmid:
            logger.error("Empty PMID provided")
            return None

        # Get the XML from PubMed API
        xml_text = self.get_pubmed_article_xml(pmid)
        if not xml_text:
            logger.error(f"Failed to retrieve XML for PMID {pmid}")
            return None

        try:
            # Parse the XML text into an XML tree
            xml_tree = etree.fromstring(xml_text.encode("utf-8"))

            # Find the PubmedArticle element
            pubmed_article = xml_tree.find(".//PubmedArticle")
            if pubmed_article is None:
                logger.error(f"No PubmedArticle element found in XML for PMID {pmid}")
                return None

            # Build the JSON from the XML tree
            return self.build_pubmed_json(xml_tree=pubmed_article)

        except Exception as e:
            logger.error(f"Error parsing XML for PMID {pmid}: {e}")
            return None

    def parse_pubmed_xml_iter(self, path):
        """Parse the XML file of the article and yield the JSON object for the article
        Args:
            path (str): The path to the XML GZ file of the article
        Yields:
            dict: A dictionary containing the JSON object for the article
        """
        logger.info(f"Starting to parse XML file: {path}")
        article_count = 0
        error_count = 0

        try:
            with gzip.open(path, "rb") as f:
                for _, element in etree.iterparse(f, events=("end",)):
                    if element.tag == "PubmedArticle":
                        try:
                            res = self.build_pubmed_json(xml_tree=element)
                            article_count += 1
                            if article_count % 100 == 0:
                                logger.debug(f"Processed {article_count} articles")
                            yield res
                        except Exception as e:
                            error_count += 1
                            logger.warning(f"Error processing article: {e}")
                            yield None
                        finally:
                            element.clear()

            logger.info(
                (
                    f"Finished parsing XML file. Processed {article_count} "
                    "articles with {error_count} errors"
                )
            )
        except Exception as e:
            logger.error(f"Error parsing XML file {path}: {e}")
            yield None
