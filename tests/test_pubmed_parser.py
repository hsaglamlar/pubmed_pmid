import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parsers.pubmed_parser import PubmedParser


class TestPubmedParser:
    """Test cases for the PubmedParser class."""

    def test_init(self):
        """Test initialization of PubmedParser with default parameters."""
        parser = PubmedParser()
        assert parser.max_split_token_length == 500
        assert parser.min_split_token_length == 100
        assert parser.sentence_overlap == 2
        assert parser.citation_count_bool is False
        assert parser.journal_ranking_bool is False

    @patch("src.api.pubmed_api.requests.get")
    def test_get_pubmed_article_xml(self, mock_get):
        """Test getting PubMed article XML."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "<PubmedArticleSet><PubmedArticle>Test XML</PubmedArticle></PubmedArticleSet>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        parser = PubmedParser()
        xml = parser.get_pubmed_article_xml("12345")

        assert xml == mock_response.text
        mock_get.assert_called_once()

    def test_get_pubmed_article_xml_empty_pmid(self):
        """Test getting PubMed article XML with empty PMID."""
        parser = PubmedParser()
        with pytest.raises(ValueError):
            parser.get_pubmed_article_xml("")

