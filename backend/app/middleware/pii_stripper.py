"""PII-Stripping Middleware using Microsoft Presidio.

Every piece of raw text passes through this to strip names, companies,
and financial figures before touching the FTI pipeline or database.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded Presidio instances to avoid slow startup
_analyzer = None
_anonymizer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            _analyzer = AnalyzerEngine()
            logger.info("Presidio Analyzer initialized successfully")
        except Exception as e:
            logger.warning(f"Presidio not available, PII stripping disabled: {e}")
            _analyzer = "unavailable"
    return _analyzer


def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        try:
            from presidio_anonymizer import AnonymizerEngine
            _anonymizer = AnonymizerEngine()
            logger.info("Presidio Anonymizer initialized successfully")
        except Exception as e:
            logger.warning(f"Presidio Anonymizer not available: {e}")
            _anonymizer = "unavailable"
    return _anonymizer


def _regex_strip_pii(text: str) -> str:
    """Regex-based PII fallback when Presidio is unavailable.

    Covers: email addresses, phone numbers, US SSNs, credit card numbers,
    and capitalised proper-noun sequences (likely names).
    Each distinct person gets a unique numbered identifier (PERSON_1, PERSON_2, etc.).
    """
    import re

    # Email addresses
    text = re.sub(r'\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b', '<EMAIL_ADDRESS>', text)

    # Phone numbers  (various formats)
    text = re.sub(
        r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b',
        '<PHONE_NUMBER>', text,
    )

    # US SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '<US_SSN>', text)

    # Credit card numbers (16 digits, optionally grouped)
    text = re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '<CREDIT_CARD>', text)

    # Capitalised proper-noun runs (2-4 consecutive Title-Case words not at sentence start)
    # e.g. "John Smith", "Mary Jane Watson"
    # Each distinct name gets a unique numbered identifier.
    person_map: dict[str, int] = {}
    person_counter = 0

    def _replace_person(match):
        nonlocal person_counter
        name = match.group(1)
        if name not in person_map:
            person_counter += 1
            person_map[name] = person_counter
        return f'<PERSON_{person_map[name]}>'

    text = re.sub(
        r'(?<!\. )(?<!\n)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b',
        _replace_person, text,
    )

    return text


def _anonymize_with_unique_ids(text: str, results: list) -> str:
    """Replace detected PII entities with uniquely numbered placeholders.

    For entity types that can appear multiple times referring to different
    real-world entities (PERSON, ORGANIZATION, LOCATION), each distinct
    surface form gets a stable counter (e.g. PERSON_1, PERSON_2).
    Other entity types use a flat label (e.g. <EMAIL_ADDRESS>).
    """
    # Entity types that should receive unique numbering
    numbered_types = {"PERSON", "ORGANIZATION", "LOCATION"}

    # Map: entity_type -> {surface_text -> counter}
    counters: dict[str, dict[str, int]] = {}

    # Sort results by start position descending so replacements don't shift offsets
    sorted_results = sorted(results, key=lambda r: r.start, reverse=True)

    for result in sorted_results:
        original = text[result.start:result.end]
        entity_type = result.entity_type

        if entity_type in numbered_types:
            if entity_type not in counters:
                counters[entity_type] = {}
            type_map = counters[entity_type]
            if original not in type_map:
                type_map[original] = len(type_map) + 1
            placeholder = f"<{entity_type}_{type_map[original]}>"
        else:
            placeholder = f"<{entity_type}>"

        text = text[:result.start] + placeholder + text[result.end:]

    return text


def strip_pii(text: str, language: str = "en") -> str:
    """Strip PII from text using Presidio, falling back to regex if unavailable.

    Detects and anonymizes:
    - Person names
    - Phone numbers
    - Email addresses
    - Credit card numbers / SSNs
    """
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()

    if analyzer == "unavailable" or anonymizer == "unavailable":
        logger.debug("Presidio unavailable — using regex PII fallback")
        return _regex_strip_pii(text)

    try:
        results = analyzer.analyze(
            text=text,
            language=language,
            entities=[
                "PERSON",
                "ORGANIZATION",
                "PHONE_NUMBER",
                "EMAIL_ADDRESS",
                "CREDIT_CARD",
                "IBAN_CODE",
                "US_SSN",
                "LOCATION",
                "NRP",
            ],
        )

        if not results:
            return text

        anonymized = _anonymize_with_unique_ids(text, results)
        logger.debug(f"Presidio stripped {len(results)} PII entities")
        return anonymized

    except Exception as e:
        logger.error(f"Presidio PII stripping failed: {e} — falling back to regex")
        return _regex_strip_pii(text)


def strip_financial_figures(text: str) -> str:
    """Additional stripping for exact financial figures.
    
    Replaces specific dollar amounts with ranges.
    """
    import re

    # Replace exact dollar amounts with ranges
    def replace_amount(match):
        amount = float(match.group(1).replace(",", ""))
        if amount < 1000:
            return "<$1K"
        elif amount < 10000:
            return "$1K-$10K"
        elif amount < 100000:
            return "$10K-$100K"
        elif amount < 1000000:
            return "$100K-$1M"
        elif amount < 10000000:
            return "$1M-$10M"
        else:
            return "$10M+"

    pattern = r'\$([0-9,]+(?:\.[0-9]{2})?)'
    return re.sub(pattern, replace_amount, text)


def full_scrub(text: str) -> str:
    """Full PII + financial scrubbing pipeline."""
    scrubbed = strip_pii(text)
    scrubbed = strip_financial_figures(scrubbed)
    return scrubbed
