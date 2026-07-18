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
        """Text containing ≥7 bescheid keywords should classify as bescheid
        (ratio-model: 7/14 = 0.50, threshold exclusive → valid)."""
        text = (
            "Steuerbescheid über Einkommensteuer. "
            "Festsetzung gemäß § 10 EStG. "
            "Verfügung vom 01.01.2025. "
            "Gegen diesen Bescheid können Sie Widerspruch einlegen. "
            "Rechtsbehelfsbelehrung beachten. "
            "Erlass wurde beantragt."
        )
        result = classifier.classify(text)
        assert result.doc_type == "bescheid"
        # ~7 bescheid patterns match out of 14 → 7/14 = 0.50
        assert result.confidence == 0.5

    def test_classify_rechnung(self, classifier: RuleBasedClassifier) -> None:
        """Text containing ≥8 rechnung keywords should classify as rechnung
        (ratio-model: 8/15 ≈ 0.53, threshold exclusive → valid)."""
        text = (
            "Rechnung Nr. 2025-0042. "
            "Rechnungsbetrag: 1.250,00 EUR. "
            "Rechnungssumme entspricht Angebot. "
            "Zahlbar innerhalb von 14 Tagen, fällig am 15.02. "
            "Umsatzsteuer: 237,50 EUR. "
            "MwSt enthalten. "
            "Zahlungsziel: 14 Tage. "
            "Skonto: 2%."
        )
        result = classifier.classify(text)
        assert result.doc_type == "rechnung"
        # 8 patterns match: rechnung, rechnungssumme, zahlbar, fällig,
        # umsatzsteuer, mwst, zahlungsziel, skonto → 8/15 ≈ 0.53
        assert result.confidence >= 0.5

    def test_classify_mahnung(self, classifier: RuleBasedClassifier) -> None:
        """Text containing ≥7 mahnung keywords should classify as mahnung."""
        text = (
            "Letzte Mahnung. "
            "Sie befinden sich mit der Zahlung in Verzug. "
            "Mahngebühr: 15,00 EUR. "
            "Mahnkosten: 5,00 EUR. "
            "Bei Säumnis droht Vollstreckung. "
            "Mahnbescheid wird beantragt."
        )
        result = classifier.classify(text)
        assert result.doc_type == "mahnung"
        assert result.confidence >= 0.5

    def test_classify_vertrag(self, classifier: RuleBasedClassifier) -> None:
        """Text containing ≥7 vertrag keywords should classify as vertrag."""
        text = (
            "Mietvertrag. "
            "Vertragspartei A: Max Mustermann. "
            "Vertragsgegenstand: Wohnung. "
            "Vertragslaufzeit: 24 Monate. "
            "Kündigungsfrist: 3 Monate. "
            "Allgemeine Geschäftsbedingungen liegen bei. "
            "AGB sind Bestandteil des Vertrags."
        )
        result = classifier.classify(text)
        assert result.doc_type == "vertrag"
        assert result.confidence >= 0.5

    def test_classify_widerspruch(self, classifier: RuleBasedClassifier) -> None:
        """Text containing ≥6 widerspruch keywords should classify as widerspruch."""
        text = (
            "Widerspruch gegen den Bescheid vom 01.01.2025. "
            "Hiermit lege ich Widerspruch ein. "
            "Ich lege Einspruch gegen den Ablehnungsbescheid ein. "
            "Anfechtungsklage wird erhoben."
        )
        result = classifier.classify(text)
        assert result.doc_type == "widerspruch"
        assert result.confidence >= 0.5

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

    def test_tie_breaking_uses_ratio(self, classifier: RuleBasedClassifier) -> None:
        """Tie-breaking uses ratio (matched/total), not absolute count.
        Type with higher ratio wins even if absolute match count is lower."""
        text = (
            "Steuerbescheid Festsetzung Verfügung Erlass "
            "gegen diesen Bescheid Rechtsbehelfsbelehrung gemäß § 10 "
            "Widerspruch Einspruch widersprechen anfechten Klage "
            "anfechtung klageerhebung"
        )
        result = classifier.classify(text)
        # bescheid: ~7 patterns match / 14 = 0.50
        # widerspruch: ~6 patterns match / 11 = 0.55
        # widerspruch has higher ratio → wins
        assert result.doc_type == "widerspruch"

    def test_confidence_exactly_0_5_is_valid(self) -> None:
        """Confidence exactly 0.5 should NOT force sonstiges.
        The threshold is exclusive: < 0.5 → sonstiges, >= 0.5 preserved."""
        result = ClassificationResult("bescheid", 0.5, ["bescheid"])
        assert result.doc_type == "bescheid"  # Preserved, not forced to sonstiges
        assert result.confidence == 0.5

    def test_ratio_model_independence(self, classifier: RuleBasedClassifier) -> None:
        """Ratio-model confidence for one type should be independent
        of matches in other types."""
        # Text that matches 7 bescheid patterns (7/14 = 0.50)
        text_bescheid = (
            "Steuerbescheid Festsetzung Verfügung "
            "gegen diesen Bescheid Erlass "
            "Rechtsbehelfsbelehrung gemäß § 10"
        )
        result_bescheid = classifier.classify(text_bescheid)
        conf_bescheid = result_bescheid.confidence

        # Same bescheid text PLUS unrelated rechnung keywords
        text_mixed = (
            "Steuerbescheid Festsetzung Verfügung "
            "gegen diesen Bescheid Erlass "
            "Rechtsbehelfsbelehrung gemäß § 10 "
            "Rechnung Rechnungsnummer Zahlbar Fällig Betrag"
        )
        result_mixed = classifier.classify(text_mixed)
        conf_mixed = result_mixed.confidence

        # Confidence should be the same (bescheid ratio is independent)
        assert conf_bescheid == conf_mixed, (
            f"Ratio-model should be independent: {conf_bescheid} != {conf_mixed}"
        )

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
