"""Rule-based document classifier for German administrative documents."""

import re

from private_legal_navigator.application.document_classifier import DocumentClassifier
from private_legal_navigator.domain.classification import ClassificationResult


class RuleBasedClassifier(DocumentClassifier):
    """Keyword-pattern-based classifier for German administrative documents.

    Fully local — no ML models, no cloud services.
    Designed for transparency: every classification can be traced
    back to specific keyword matches.

    The classifier scores document types by counting keyword matches
    in the extracted text. The type with the most matches wins.
    Confidence is the ratio of winning-type matches to total matches.
    """

    # Keyword patterns per document type (case-insensitive)
    PATTERNS: dict[str, list[str]] = {
        "bescheid": [
            r"bescheid", r"festsetzungsbescheid", r"steuerbescheid",
            r"bewilligungsbescheid", r"ablehnungsbescheid",
            r"widerspruchsbescheid", r"änderungsbescheid",
            r"festsetzung", r"erlass", r"verfügung",
            r"gemäß\s+\$\s+\d+", r"rechtsbehelfsbelehrung",
            r"gegen diesen bescheid", r"festgesetzt",
        ],
        "rechnung": [
            r"rechnung", r"rechnungsnummer", r"rechnungssumme",
            r"zahlbar", r"fällig", r"betrag", r"gesamtbetrag",
            r"umsatzsteuer", r"mwst", r"mehrwertsteuer",
            r"zahlungsziel", r"skonto", r"rechnungsbetrag",
            r"leistungszeitraum", r"zahlungsbedingungen",
        ],
        "mahnung": [
            r"mahnung", r"mahnbescheid", r"vollstreckung",
            r"vollstreckungsbescheid", r"zahlungserinnerung",
            r"in verzug", r"verzug", r"säumnis",
            r"letzte mahnung", r"mahngebühr", r"mahnkosten",
            r"gerichtliches mahnverfahren", r"pfändung",
            r"zwangsvollstreckung",
        ],
        "vertrag": [
            r"vertrag", r"vereinbarung", r"vertragspartei",
            r"vertragsgegenstand", r"vertragslaufzeit",
            r"kündigung", r"kündigungsfrist", r"laufzeit",
            r"vertragsbeginn", r"vertragsende",
            r"allgemeine geschäftsbedingungen", r"agb",
            r"unterzeichner", r"vertraglich",
        ],
        "widerspruch": [
            r"widerspruch", r"einspruch", r"widersprechen",
            r"lege .{0,20} widerspruch", r"lege .{0,20} einspruch",
            r"widerspruch ein", r"einspruch ein",
            r"anfechtung", r"anfechten",
            r"klage", r"klageerhebung",
        ],
    }

    def classify(self, text: str) -> ClassificationResult:
        """Classify document text using keyword pattern matching.

        Counts matches per document type, selects the type with
        the most matches. Computes confidence as winning_matches / total_matches.
        """
        if not text.strip():
            return ClassificationResult(
                doc_type="sonstiges",
                confidence=0.0,
                matched_patterns=[],
            )

        text_lower = text.lower()
        scores: dict[str, tuple[int, list[str]]] = {}

        for doc_type, patterns in self.PATTERNS.items():
            matched: list[str] = []
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matched.append(pattern)
            scores[doc_type] = (len(matched), matched)

        # Find the type with the most matches
        best_type = max(scores, key=lambda t: scores[t][0])
        best_count, best_matches = scores[best_type]
        total_matches = sum(s[0] for s in scores.values())

        if best_count == 0 or total_matches == 0:
            return ClassificationResult(
                doc_type="sonstiges",
                confidence=0.0,
                matched_patterns=[],
            )

        confidence = best_count / total_matches if total_matches > 0 else 0.0

        return ClassificationResult(
            doc_type=best_type,
            confidence=round(confidence, 2),
            matched_patterns=best_matches,
        )
