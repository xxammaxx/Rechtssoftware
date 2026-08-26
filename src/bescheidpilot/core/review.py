"""Human Review Gate — ensures no analysis result is treated as final.

Every critical extraction must be flagged for human review. No field
may be marked as ``reviewed`` automatically. The gate produces
ReviewItems and warnings for the BescheidAnalysisResult.
"""

from __future__ import annotations

from .models import (
    BescheidAnalysisResult,
    ReviewItem,
)

# ---------------------------------------------------------------------------
# Fields that MUST be reviewed before any further processing or export
# ---------------------------------------------------------------------------

CRITICAL_REVIEW_FIELDS: dict[str, str] = {
    "deadline": "HIGH",
    "required_action": "HIGH",
    "missing_documents": "MEDIUM",
    "risk_level": "MEDIUM",
    "document_type": "LOW",
    "authority": "LOW",
}


def _has_evidence(result: BescheidAnalysisResult, field: str) -> bool:
    return any(e.field == field for e in result.evidence)


def _field_value(result: BescheidAnalysisResult, field: str) -> str | None:
    value = getattr(result, field, None)
    if isinstance(value, list):
        return ", ".join(value) if value else None
    return value if value else None


def build_review_gate(result: BescheidAnalysisResult) -> BescheidAnalysisResult:
    """Add mandatory review items and warnings to an analysis result.

    This function never marks anything as ``reviewed`` and never sets
    ``final_decision`` to ``True``. It is purely additive — all
    existing extractions and evidence are preserved.

    Returns a new BescheidAnalysisResult with review fields populated.
    """
    review_items: list[ReviewItem] = []
    review_warnings: list[str] = list(result.warnings)
    any_critical = False

    for field, default_severity in CRITICAL_REVIEW_FIELDS.items():
        value = _field_value(result, field)
        has_ev = _has_evidence(result, field)

        if field == "risk_level" and value in (None, "unknown"):
            review_warnings.append(
                f"Risiko-Level nicht sicher bestimmt — manuelle Prüfung nötig ({field})"
            )

        if field == "missing_documents" and value is None:
            continue  # No missing docs → no review needed

        if field in ("authority", "document_type") and value is None:
            continue  # Non-critical absence → warning only

        if value is not None or field in ("deadline", "required_action"):
            if value is None:
                # Critical field is missing
                severity = "HIGH"
                reason = f"Kritisches Feld '{field}' fehlt — manuelle Prüfung zwingend erforderlich"
            elif not has_ev:
                severity = default_severity
                reason = f"Keine Fundstelle für '{field}' — manuelle Verifikation nötig"
            else:
                severity = default_severity
                reason = f"Extrahiertes Feld '{field}' muss geprüft werden"

            review_items.append(
                ReviewItem(
                    field=field,
                    value=value,
                    status="requires_review",
                    reason=reason,
                    evidence_required=True,
                    evidence_present=has_ev,
                    severity=severity,
                )
            )
            any_critical = True

    # If risk is HIGH, ensure a HIGH severity review item exists
    if result.risk_level == "high" and not any(ri.field == "risk_level" for ri in review_items):
        review_items.append(
            ReviewItem(
                field="risk_level",
                value="high",
                status="requires_review",
                reason="Hohes Risiko — sofortige manuelle Prüfung erforderlich",
                evidence_required=False,
                evidence_present=_has_evidence(result, "risk_level"),
                severity="HIGH",
            )
        )

    # Never set final_decision to True
    return BescheidAnalysisResult(
        authority=result.authority,
        document_type=result.document_type,
        letter_date=result.letter_date,
        deadline=result.deadline,
        required_action=result.required_action,
        missing_documents=list(result.missing_documents),
        risk_level=result.risk_level,
        evidence=list(result.evidence),
        warnings=list(result.warnings),
        review_required=any_critical,
        review_items=review_items,
        final_decision=False,
    )
