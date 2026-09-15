"""Presidio-based PII scanner for filtering chatbot responses."""
import logging
import re

logger = logging.getLogger(__name__)

_LICENSE_PLATE_RE = re.compile(r"\b[A-Z]{2,3}[-\s]?\d{2,4}[-\s]?[A-Z]{0,3}\b")

_PII_ENTITIES = [
    "PERSON",
    "LOCATION",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
]


class PiiScanner:
    """Scan text for PII entities using Microsoft Presidio."""

    def __init__(self) -> None:
        try:
            from presidio_analyzer import AnalyzerEngine

            self._analyzer = AnalyzerEngine()
            self._available = True
        except Exception as exc:
            logger.warning("Presidio unavailable, PII scanning disabled: %s", exc)
            self._analyzer = None
            self._available = False

    def scan(self, text: str) -> list[str]:
        """Return list of detected PII entity types (empty = clean)."""
        found: list[str] = []

        if _LICENSE_PLATE_RE.search(text):
            found.append("LICENSE_PLATE")

        if self._available and self._analyzer is not None:
            try:
                results = self._analyzer.analyze(text=text, entities=_PII_ENTITIES, language="en")
                found.extend(r.entity_type for r in results)
            except Exception as exc:
                logger.error("Presidio analysis failed: %s", exc)

        return found
