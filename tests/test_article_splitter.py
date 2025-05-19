import os
import sys
import pytest

# Add the parent directory to the path so we can import the src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.article_splitter import (
    split_article_paragraphs,
    _split_sentences_into_chunks,
)
from src.utils.detect_sentences import get_sentences


class TestArticleSplitter:
    """Test cases for the article_splitter module."""

    def test_split_sentences_into_chunks(self):
        """Test splitting sentences into chunks based on token length."""
        # Create a long text with multiple sentences
        long_text = (
            "This is the first sentence. This is the second sentence. "
            "This is the third sentence. This is the fourth sentence. "
            "This is the fifth sentence. This is the sixth sentence. "
            "This is the seventh sentence. This is the eighth sentence. "
            "This is the ninth sentence. This is the tenth sentence. "
            "This is the eleventh sentence. This is the twelfth sentence. "
            "This is the thirteenth sentence. This is the fourteenth sentence. "
            "This is the fifteenth sentence. This is the sixteenth sentence. "
            "This is the seventeenth sentence. This is the eighteenth sentence. "
            "This is the nineteenth sentence. This is the twentieth sentence."
        )

        # Get sentences from the text
        sentences = get_sentences(long_text)

        # Test with different max token lengths
        chunks_50 = _split_sentences_into_chunks(
            sentences, max_token_length=50, min_token_length=10, sentence_overlap=1
        )
        chunks_100 = _split_sentences_into_chunks(
            sentences, max_token_length=100, min_token_length=10, sentence_overlap=2
        )

        # Assertions
        assert len(chunks_50) > len(
            chunks_100
        )  # Smaller max_token_length should result in more chunks
        assert all(
            len(chunk) > 0 for chunk in chunks_50
        )  # All chunks should have content
        assert all(
            len(chunk) > 0 for chunk in chunks_100
        )  # All chunks should have content

    def test_split_article_paragraphs(self):
        """Test splitting article paragraphs based on token length."""
        # Create a mock article JSON
        article_json = {
            "abstract": [
                {
                    "text": (
                        "This is a long abstract with multiple sentences. "
                        "It contains important information. "
                        "The researchers conducted experiments. The results were significant. "
                        "Further research is needed. This is the conclusion of the abstract. "
                        "Additional information is provided. The methodology was sound. "
                        "Statistical analysis was performed. The p-value was less than 0.05. "
                        "The hypothesis was confirmed. The study had limitations. "
                        "Future work will address these limitations. "
                        "The implications are significant. "
                        "This research contributes to the field. "
                        "The authors acknowledge funding sources."
                        "This is a long abstract with multiple sentences. "
                        "It contains important information. "
                        "The researchers conducted experiments. The results were significant. "
                        "Further research is needed. This is the conclusion of the abstract. "
                        "Additional information is provided. The methodology was sound. "
                        "Statistical analysis was performed. The p-value was less than 0.05. "
                        "The hypothesis was confirmed. The study had limitations. "
                        "Future work will address these limitations. "
                        "The implications are significant. "
                        "This research contributes to the field. "
                        "The authors acknowledge funding sources."
                    ),
                    "section_title": "Abstract",
                    "section_type": "ABSTRACT",
                }
            ],
            "pmid": "12345",
        }

        # Test with different max token lengths
        splits_50 = split_article_paragraphs(
            article_json,
            max_split_token_length=50,
            min_split_token_length=10,
            sentence_overlap=1,
        )
        splits_100 = split_article_paragraphs(
            article_json,
            max_split_token_length=100,
            min_split_token_length=10,
            sentence_overlap=2,
        )
        print(splits_50)
        print(splits_100)
        # Assertions
        assert len(splits_50) > 0  # Should have at least one split
        assert len(splits_100) > 0  # Should have at least one split
        assert len(splits_50) >= len(
            splits_100
        )  # Smaller max_token_length should result in more splits

        # Check structure of splits
        for split in splits_50:
            assert "text" in split
            assert "section_title" in split
            assert "section_type" in split
            assert "split_number" in split
            assert "total_splits" in split
            assert split["section_title"] == "Abstract"
            assert split["section_type"] == "ABSTRACT"
