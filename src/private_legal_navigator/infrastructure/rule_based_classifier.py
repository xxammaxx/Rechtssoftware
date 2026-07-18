"""Rule-based document classifier for German administrative documents."""

import re

from private_legal_navigator.application.document_classifier import DocumentClassifier
from private_legal_navigator.domain.classification import ClassificationResult


class RuleBasedClassifier(DocumentClassifier):
    """Keyword-pattern-based classifier for German administrative documents.

    Fully local — no ML models, no cloud services.
    Designed for transparency: every classification can be traced
    back to specific keyword matches.

    Uses ratio-model confidence: matched patterns of winning type
    divided by total patterns of that type. Tie-breaking: highest
    ratio wins; ties resolved by definition order (insertion order
    of PATTERNS dict).
    """

    # Keyword patterns per document type (case-insensitive).
    # Definition order determines tie-breaking priority.
    PATTERNS: dict[str, list[str]] = {
        "bescheid": [
            r"bescheid",
            r"festsetzungsbescheid",
            r"steuerbescheid",
            r"bewilligungsbescheid",
            r"ablehnungsbescheid",
            r"widerspruchsbescheid",
            r"änderungsbescheid",
            r"festsetzung",
            r"erlass",
            r"verfügung",
            r"gemäß\s+\$\s+\d+",
            r"rechtsbehelfsbelehrung",
            r"gegen diesen bescheid",
            r"festgesetzt",
        ],
        "rechnung": [
            r"rechnung",
            r"rechnungsnummer",
            r"rechnungssumme",
            r"zahlbar",
            r"fällig",
            r"betrag",
            r"gesamtbetrag",
            r"umsatzsteuer",
            r"mwst",
            r"mehrwertsteuer",
            r"zahlungsziel",
            r"skonto",
            r"rechnungsbetrag",
            r"leistungszeitraum",
            r"zahlungsbedingungen",
        ],
        "mahnung": [
            r"mahnung",
            r"mahnbescheid",
            r"vollstreckung",
            r"vollstreckungsbescheid",
            r"zahlungserinnerung",
            r"in verzug",
            r"verzug",
            r"säumnis",
            r"letzte mahnung",
            r"mahngebühr",
            r"mahnkosten",
            r"gerichtliches mahnverfahren",
            r"pfändung",
            r"zwangsvollstreckung",
        ],
        "vertrag": [
            r"vertrag",
            r"vereinbarung",
            r"vertragspartei",
            r"vertragsgegenstand",
            r"vertragslaufzeit",
            r"kündigung",
            r"kündigungsfrist",
            r"laufzeit",
            r"vertragsbeginn",
            r"vertragsende",
            r"allgemeine geschäftsbedingungen",
            r"agb",
            r"unterzeichner",
            r"vertraglich",
        ],
        "widerspruch": [
            r"widerspruch",
            r"einspruch",
            r"widersprechen",
            r"lege .{0,20} widerspruch",
            r"lege .{0,20} einspruch",
            r"widerspruch ein",
            r"einspruch ein",
            r"anfechtung",
            r"anfechten",
            r"klage",
            r"klageerhebung",
        ],
    }

    def classify(self, text: str) -> ClassificationResult:
        """Classify document text using ratio-model keyword pattern matching.

        For each document type, computes ratio = matched_count / total_patterns.
        The type with the highest ratio wins. Tie → first in definition order.
        Confidence = winning type's ratio.
        """
        if not text.strip():
            return ClassificationResult(
                doc_type="sonstiges",
                confidence=0.0,
                matched_patterns=[],
            )

        text_lower = text.lower()
        ratios: dict[str, tuple[float, list[str]]] = {}

        for doc_type, patterns in self.PATTERNS.items():
            matched: list[str] = []
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matched.append(pattern)
            total = len(patterns)
            ratio = len(matched) / total if total > 0 else 0.0
            ratios[doc_type] = (ratio, matched)

        # Find type with highest ratio; tie → first in definition order
        # Python's max() is stable: picks first encountered element on tie.
        best_type = max(ratios, key=lambda t: ratios[t][0])
        best_ratio, best_matches = ratios[best_type]

        if best_ratio == 0.0:
            return ClassificationResult(
                doc_type="sonstiges",
                confidence=0.0,
                matched_patterns=[],
            )

        return ClassificationResult(
            doc_type=best_type,
            confidence=round(best_ratio, 2),
            matched_patterns=best_matches,
        )
