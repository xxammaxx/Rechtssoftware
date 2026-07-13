"""Unit tests for ClassificationResult and RuleBasedClassifier."""

from private_legal_navigator.domain.classification import ClassificationResult
from private_legal_navigator.infrastructure.rule_based_classifier import (
    RuleBasedClassifier,
)


class TestClassificationResult:
    """Tests for ClassificationResult value object."""

    def test_valid_result(self) -> None:
        result = ClassificationResult("bescheid", 0.85, ["bescheid"])
        assert result.doc_type == "bescheid"
        assert result.confidence == 0.85
        assert result.matched_patterns == ["bescheid"]

    def test_low_confidence_becomes_sonstiges(self) -> None:
        """Confidence < 0.5 should force doc_type to 'sonstiges'."""
        result = ClassificationResult("bescheid", 0.3, ["bescheid"])
        assert result.doc_type == "sonstiges"

    def test_confidence_bounds(self) -> None:
        """Confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValueError):
            ClassificationResult("bescheid", 1.5, [])
        with pytest.raises(ValueError):
            ClassificationResult("bescheid", -0.1, [])

    def test_confidence_zero(self) -> None:
        """Confidence 0.0 is valid."""
        result = ClassificationResult("sonstiges", 0.0, [])
        assert result.confidence == 0.0


import pytest  # noqa: E402


class TestRuleBasedClassifier:
    """Tests for the rule-based document classifier."""

    @pytest.fixture
    def classifier(self) -> RuleBasedClassifier:
        return RuleBasedClassifier()

    def test_classify_bescheid(self, classifier: RuleBasedClassifier) -> None:
        """Text containing 'Bescheid' keywords should classify as bescheid."""
        text = """
        Steuerbescheid für 2025
        Die Festsetzung erfolgt gemäß § 32a EStG.
        Gegen diesen Bescheid können Sie innerhalb eines Monats Widerspruch einlegen.
        Rechtsbehelfsbelehrung: ...
        """
        result = classifier.classify(text)
        assert result.doc_type == "bescheid"
        assert result.confidence > 0.3

    def test_classify_rechnung(self, classifier: RuleBasedClassifier) -> None:
        """Text containing 'Rechnung' keywords should classify as rechnung."""
        text = """
        Rechnung Nr. 2025-0042
        Rechnungsbetrag: 1.250,00 EUR
        Zahlbar innerhalb von 14 Tagen.
        Umsatzsteuer: 237,50 EUR
        """
        result = classifier.classify(text)
        assert result.doc_type == "rechnung"

    def test_classify_mahnung(self, classifier: RuleBasedClassifier) -> None:
        """Text containing 'Mahnung' keywords should classify as mahnung."""
        text = """
        Letzte Mahnung
        Sie befinden sich mit der Zahlung in Verzug.
        Mahngebühr: 15,00 EUR
        """
        result = classifier.classify(text)
        assert result.doc_type == "mahnung"

    def test_classify_vertrag(self, classifier: RuleBasedClassifier) -> None:
        """Text containing 'Vertrag' keywords should classify as vertrag."""
        text = """
        Mietvertrag
        Vertragspartei A: Max Mustermann
        Vertragslaufzeit: 24 Monate
        Kündigungsfrist: 3 Monate
        """
        result = classifier.classify(text)
        assert result.doc_type == "vertrag"

    def test_classify_widerspruch(self, classifier: RuleBasedClassifier) -> None:
        """Text containing 'Widerspruch' keywords should classify as widerspruch."""
        text = """
        Widerspruch gegen den Bescheid vom 01.01.2025
        Hiermit lege ich Widerspruch ein.
        """
        result = classifier.classify(text)
        assert result.doc_type == "widerspruch"

    def test_empty_text_returns_sonstiges(self, classifier: RuleBasedClassifier) -> None:
        """Empty text should return 'sonstiges' with 0 confidence."""
        result = classifier.classify("")
        assert result.doc_type == "sonstiges"
        assert result.confidence == 0.0

    def test_unrecognized_text_returns_sonstiges(self, classifier: RuleBasedClassifier) -> None:
        """Text with no matching keywords returns 'sonstiges'."""
        result = classifier.classify("Lorem ipsum dolor sit amet.")
        assert result.doc_type == "sonstiges"
        assert result.confidence == 0.0

    def test_matched_patterns_are_reported(self, classifier: RuleBasedClassifier) -> None:
        """The classifier should report which patterns matched."""
        result = classifier.classify("Dies ist ein Bescheid. Rechnung ist beigefügt.")
        assert len(result.matched_patterns) > 0

    def test_classification_included_in_result(self, classifier: RuleBasedClassifier) -> None:
        """Classification must return all expected fields."""
        result = classifier.classify("Bescheid über Einkommensteuer. Rechnungsnummer 123.")
        assert result.doc_type in (
            "bescheid",
            "rechnung",
            "mahnung",
            "vertrag",
            "widerspruch",
            "sonstiges",
        )
        assert 0.0 <= result.confidence <= 1.0
