''' This module contains the get_sentences for detecting sentences in a text.'''

import re

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


def get_sentences(content):
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