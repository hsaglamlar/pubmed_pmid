"""Module containing classes for extracting information from PubMed XML."""

from itertools import chain
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

LIST_SEPERATOR = ";"


class BaseExtractor:
    """Base class for XML extractors."""

    def stringify_children(self, node) -> str:
        """Extract and concatenate all text from an XML node and its children.

        Args:
            node: XML node

        Returns:
            Concatenated text content
        """
        if node is None:
            return ""

        parts = (
            [node.text]
            + list(chain(*([c.text, c.tail] for c in node.getchildren())))
            + [node.tail]
        )
        return "".join(filter(None, parts)).strip()


class AbstractExtractor(BaseExtractor):
    """Extractor for article abstracts."""

    def get_abstract(self, xml_tree) -> Optional[Dict[str, str]]:
        """Extract abstract text from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            Dictionary with abstract text and metadata, or None if no abstract
        """
        article = xml_tree.find(".//MedlineCitation/Article")
        if article is None:
            return None

        category = "Label"
        abstract = ""

        if article.find("Abstract/AbstractText") is not None:
            # Parse structured abstract
            if len(article.findall("Abstract/AbstractText")) > 1:
                abstract_list = []
                for abstract_section in article.findall("Abstract/AbstractText"):
                    section = abstract_section.attrib.get(category, "")
                    if section != "UNASSIGNED":
                        abstract_list.append("\n")
                        abstract_list.append(section + ":")

                    section_text = self.stringify_children(abstract_section)
                    abstract_list.append(section_text)
                abstract = "\n".join(abstract_list)
            else:
                abstract = (
                    self.stringify_children(article.find("Abstract/AbstractText")) or ""
                )
        elif article.find("Abstract") is not None:
            abstract = self.stringify_children(article.find("Abstract")) or ""

        if not abstract.strip():
            return None

        return {
            "text": abstract,
            "section_title": "Abstract",
            "section_type": "ABSTRACT",
        }


class ArticleInfoExtractor(BaseExtractor):
    """Extractor for article information."""

    def get_article_ids(self, xml_tree) -> List[Dict[str, str]]:
        """Extract article IDs from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            List of dictionaries containing article IDs and their types
        """
        article_ids = []
        article_id_list = xml_tree.findall(".//PubmedData/ArticleIdList/ArticleId")

        if article_id_list:
            for article_id in article_id_list:
                article_ids.append(
                    {
                        "idtype": article_id.attrib.get("IdType", ""),
                        "value": article_id.text or "",
                    }
                )

        return article_ids

    def get_keywords(self, xml_tree) -> str:
        """Extract keywords from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            Comma-separated string of keywords
        """
        keywords = []
        keyword_list = xml_tree.findall(".//KeywordList/Keyword")

        if keyword_list:
            keywords = [keyword.text or "" for keyword in keyword_list]

        return LIST_SEPERATOR.join(keywords)

    def get_dates_history(self, xml_tree) -> List[Dict[str, str]]:
        """Extract publication history dates from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            List of dictionaries containing date information
        """
        dates = []
        date_list = xml_tree.findall(".//PubmedData/History/PubMedPubDate")

        if date_list:
            for date in date_list:
                year = date.find("Year")
                month = date.find("Month")
                day = date.find("Day")

                dates.append(
                    {
                        "date_type": date.attrib.get("PubStatus", ""),
                        "year": year.text or "" if year is not None else "",
                        "month": month.text or "" if month is not None else "",
                        "day": day.text or "" if day is not None else "",
                    }
                )

        return dates

    def get_article_info(self, xml_tree) -> Dict[str, Any]:
        """Extract article information from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            Dictionary containing article information
        """
        article = xml_tree.find(".//MedlineCitation/Article")
        article_info = {}

        if article is None:
            return article_info

        # Get article title
        article_info["title"] = ""
        if article.find("ArticleTitle") is not None:
            article_info["title"] = (
                self.stringify_children(article.find("ArticleTitle")) or ""
            )

        # Get article language
        article_info["languages"] = ""
        if article.findall("Language"):
            article_info["languages"] = LIST_SEPERATOR.join(
                [language.text for language in article.findall("Language")]
            )

        # Get article volume
        volume = article.find("Journal/JournalIssue/Volume")
        article_info["volume"] = volume.text or "" if volume is not None else ""

        # Get article issue
        issue = article.find("Journal/JournalIssue/Issue")
        article_info["issue"] = issue.text or "" if issue is not None else ""

        # Get article pages
        pages = article.find("Pagination/MedlinePgn")
        article_info["pages"] = pages.text or "" if pages is not None else ""

        # Get article publication type
        type_infos = article.findall("PublicationTypeList/PublicationType")
        article_info["publication_type"] = ""
        if type_infos:
            article_info["publication_type"] = [
                (type_info.attrib.get("UI", None), type_info.text)
                for type_info in type_infos
            ]

        return article_info


class JournalInfoExtractor(BaseExtractor):
    """Extractor for journal information."""

    def get_journal_info(self, xml_tree) -> Dict[str, str]:
        """Extract journal information from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            Dictionary containing journal information
        """
        journal_info = {}
        journal = xml_tree.find(".//MedlineCitation/Article/Journal")

        if journal is not None:
            # Get journal full name
            title = journal.find("Title")
            if title is not None:
                journal_info["fulljournalname"] = title.text or ""

            # Get journal abbreviation
            abbrev = journal.find("ISOAbbreviation")
            if abbrev is not None:
                journal_info["journal_abbrev"] = abbrev.text or ""

            # Get journal ISSN
            issn = journal.find("ISSN")
            if issn is not None:
                journal_info["issn"] = issn.text or ""

            # Get publication date
            date = journal.find("JournalIssue/PubDate")
            if date is not None:
                year = date.find("Year")
                month = date.find("Month")
                day = date.find("Day")

                year_text = year.text or "" if year is not None else ""
                month_text = month.text or "" if month is not None else ""
                day_text = day.text or "" if day is not None else ""

                if any([year_text, month_text, day_text]):
                    journal_info["pubdate"] = (
                        f"{year_text} {month_text} {day_text}".strip()
                    )

        return journal_info


class AuthorExtractor(BaseExtractor):
    """Extractor for author information."""

    def get_authors(self, xml_tree) -> List[Dict[str, str]]:
        """Extract author information from the XML tree.

        Args:
            xml_tree: The lxml node pointing to a medline document

        Returns:
            List of dictionaries containing author information
        """
        authors = []
        author_list = xml_tree.findall(".//AuthorList/Author")

        if author_list:
            for author in author_list:
                forename = author.find("ForeName")
                lastname = author.find("LastName")
                initials = author.find("Initials")
                affiliation = author.find("AffiliationInfo/Affiliation")

                authors.append(
                    {
                        "first": forename.text or "" if forename is not None else "",
                        "middle": "",
                        "last": lastname.text or "" if lastname is not None else "",
                        "suffix": "",
                        "initials": initials.text or "" if initials is not None else "",
                        "affiliation": (
                            self.stringify_children(affiliation) or ""
                            if affiliation is not None
                            else ""
                        ),
                        "email": "",
                    }
                )

        return authors


class MeshTermsExtractor(BaseExtractor):
    """Extractor for MeSH terms."""

    def parse_mesh_terms_with_subs(self, xml_tree):
        """
        Parse the mesh terms with subheadings from the XML tree
        Args:
            xml_tree (Element): The lxml node pointing to a medline document
        Returns:
            str: A string of LIST_SEPERATOR separated mesh terms with subheadings
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
            mesh_terms = LIST_SEPERATOR.join(mesh_terms_list)
        else:
            mesh_terms = ""
        return mesh_terms
