"""This module contains functions for detecting sentences in text using spaCy."""

import logging
from typing import List


import spacy  # type: ignore


# Configure logging
logger = logging.getLogger(__name__)

# Load spaCy model once at module level
try:
    # check if model is installed, if not install it
    if "en_core_web_sm" not in spacy.util.get_installed_models():
        logger.info("Downloading spaCy model 'en_core_web_sm'")
        spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
    logger.debug("Successfully loaded spaCy model 'en_core_web_sm'")
except Exception as e:
    logger.error("Failed to load spaCy model: %s", e)
    logger.warning("Using blank English model as fallback")
    nlp = spacy.blank("en")


def get_sentences(text: str) -> List[str]:
    """Extract sentences from text using spaCy.

    Args:
        text: The text to extract sentences from

    Returns:
        List of sentences as strings

    Examples:
        >>> get_sentences("Hello world. This is a test.")
        ['Hello world.', 'This is a test.']
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid input text: %s", type(text))
        return []

    try:
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        logger.debug("Extracted %d sentences from text", len(sentences))
        return sentences
    except Exception as e:
        logger.error("Error processing text with spaCy: %s", e)
        logger.warning("Falling back to simple sentence splitting")
        # Fallback to simple sentence splitting
        return _simple_sentence_split(text)


def _simple_sentence_split(text: str) -> List[str]:
    """Simple fallback sentence splitter using punctuation.

    Args:
        text: Text to split into sentences

    Returns:
        List of sentences
    """
    if not text:
        return []

    # Split on common sentence-ending punctuation
    sentences = []
    for sent in text.replace("!", ".").replace("?", ".").split("."):
        sent = sent.strip()
        if sent:
            sentences.append(sent + ".")

    return sentences
