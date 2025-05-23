"""Module for splitting articles into smaller chunks."""

from typing import List
from loguru import logger

import tiktoken  # type: ignore

from src.utils.detect_sentences import get_sentences

# Initialize tokenizer
_tokenizer = tiktoken.get_encoding("p50k_base")


def split_article_paragraphs(
    article_json,
    max_split_token_length=500,
    min_split_token_length=100,
    sentence_overlap=2,
):
    """Split article paragraphs into smaller chunks.

    Args:
        article_json: Dictionary containing article data
        max_split_token_length: Maximum number of tokens in a split
        min_split_token_length: Minimum number of tokens in a split
        sentence_overlap: Number of sentences to overlap between splits

    Returns:
        List of dictionaries containing split paragraphs
    """
    article_splits = []

    # Get abstract text
    abstract_sections = article_json.get("abstract", [])
    if not abstract_sections:
        logger.warning(
            f"No abstract found for article {article_json.get('pmid', 'unknown')}"
        )
        return article_splits

    try:
        # Process each abstract section
        for section in abstract_sections:
            section_text = section.get("text", "")
            if not section_text:
                continue

            # Get sentences from section text
            sentences = get_sentences(section_text)
            if not sentences:
                logger.warning(
                    f"No sentences found in section: {section.get('section_title', 'Unknown')}"
                )
                continue

            # Split sentences into chunks
            chunks = _split_sentences_into_chunks(
                sentences,
                max_split_token_length,
                min_split_token_length,
                sentence_overlap,
            )

            # Create article splits
            for i, chunk in enumerate(chunks):
                article_splits.append(
                    {
                        "text": chunk,
                        "section_title": section.get("section_title", ""),
                        "section_type": section.get("section_type", ""),
                        "split_number": i + 1,
                        "total_splits": len(chunks),
                    }
                )

        logger.debug(f"Created {len(article_splits)} article splits")
        return article_splits
    except Exception as e:
        logger.error(f"Error splitting article paragraphs: {e}")
        return []


def _split_sentences_into_chunks(
    sentences: List[str],
    max_token_length: int,
    min_token_length: int,
    sentence_overlap: int,
) -> List[str]:
    """Split sentences into chunks based on token length.

    Args:
        sentences: List of sentences
        max_token_length: Maximum number of tokens in a chunk
        min_token_length: Minimum number of tokens in a chunk
        sentence_overlap: Number of sentences to overlap between chunks

    Returns:
        List of text chunks
    """
    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_length = 0

    for _, sentence in enumerate(sentences):
        # Get token length of sentence
        sentence_tokens = len(_tokenizer.encode(sentence))

        # If adding this sentence would exceed max length and we have enough content,
        # finalize the current chunk and start a new one
        if (
            current_length + sentence_tokens > max_token_length
            and current_length >= min_token_length
            and current_chunk
        ):

            chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap
            overlap_start = max(0, len(current_chunk) - sentence_overlap)
            current_chunk = current_chunk[overlap_start:]
            current_length = sum(len(_tokenizer.encode(s)) for s in current_chunk)

        # Add sentence to current chunk
        current_chunk.append(sentence)
        current_length += sentence_tokens

    # Add the last chunk if it's not empty
    if current_chunk and current_length >= min_token_length:
        chunks.append(" ".join(current_chunk))

    return chunks
