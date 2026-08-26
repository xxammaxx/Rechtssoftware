"""Local rule-based answer draft generation.

All drafts are strictly review-required. No remote LLM, no legal
advice, no automatic transmission. Drafts use only extracted facts
and explicit placeholders for missing data.
"""

from __future__ import annotations

from .models import AnswerDraft, BescheidAnalysisResult


def create_answer_draft(result: BescheidAnalysisResult) -> AnswerDraft:
    """Generate a review-required answer draft from analysis results.

    Uses only deterministic, rule-based templates. No LLM, no network,
    no external data. Missing critical fields produce explicit
    placeholders.

    The returned draft always has:
    - status = "draft_requires_review"
    - requires_review = True
    - final_decision = False
    """
    warnings: list[str] = []
    based_on: list[str] = []

    # Collect available data with placeholders for missing fields
    authority = result.authority or "[BEHÖRDE BITTE MANUELL EINTRAGEN]"
    if result.authority:
        based_on.append("authority")

    doc_type = result.document_type or "Ihrem Schreiben"
    if result.document_type:
        based_on.append("document_type")

    deadline_str = result.deadline or "[FRIST BITTE MANUELL PRÜFEN]"
    if result.deadline:
        based_on.append("deadline")
    else:
        warnings.append("Keine Frist erkannt — bitte manuell prüfen")

    action_str = result.required_action or "[HANDLUNG BITTE MANUELL PRÜFEN]"
    if result.required_action:
        based_on.append("required_action")
    else:
        warnings.append("Keine Handlungspflicht erkannt — bitte manuell prüfen")

    if result.missing_documents:
        based_on.append("missing_documents")
        docs_list = "\n".join(f"  - {doc}" for doc in result.missing_documents)
    else:
        docs_list = "  [UNTERLAGEN BITTE MANUELL PRÜFEN]"
        warnings.append("Keine fehlenden Unterlagen erkannt")

    if result.risk_level != "unknown":
        based_on.append("risk_level")

    # Build the draft body
    body_lines: list[str] = []

    body_lines.append("ENTWURF — MENSCHLICHE PRÜFUNG ERFORDERLICH")
    body_lines.append("")
    body_lines.append("Dieser Text ist ein technischer Entwurf und ersetzt keine Rechtsberatung.")
    body_lines.append("Bitte prüfen Sie Fristen, Angaben, Unterlagen und den konkreten Einzelfall")
    body_lines.append("vor Verwendung vollständig.")
    body_lines.append("")

    # Recipient
    body_lines.append(f"An: {authority}")
    body_lines.append("")
    body_lines.append(f"Betreff: Rückmeldung zu {doc_type}")
    body_lines.append("")
    body_lines.append("Sehr geehrte Damen und Herren,")
    body_lines.append("")

    # Body based on what was found
    if result.required_action:
        body_lines.append("zu Ihrem Schreiben nehme ich wie folgt Stellung:")
        body_lines.append("")
        body_lines.append("Ich werde die geforderte Handlung wie folgt umsetzen:")
        body_lines.append(f"  {action_str}")
    else:
        body_lines.append("zu Ihrem Schreiben nehme ich wie folgt Stellung:")
        body_lines.append("")
        body_lines.append(f"Handlung: {action_str}")

    body_lines.append("")

    if result.missing_documents or result.required_action:
        body_lines.append("Folgende Unterlagen wurden als relevant erkannt:")
        body_lines.append(docs_list)

    body_lines.append("")

    if result.deadline:
        body_lines.append(f"Die genannte Frist lautet: {deadline_str}")
    else:
        body_lines.append(f"Frist: {deadline_str}")

    body_lines.append("")

    if result.risk_level == "high":
        body_lines.append("Wichtiger Hinweis: Das Risiko-Level wurde als HOCH eingestuft.")
        body_lines.append("Bitte handeln Sie umgehend und prüfen Sie alle Angaben sorgfältig.")
        body_lines.append("")

    # Closing
    body_lines.append("---")
    body_lines.append("Dieser Entwurf wurde automatisch aus einer lokalen Analyse erzeugt.")
    body_lines.append("Er muss vor Verwendung vollständig durch einen Menschen geprüft werden.")
    body_lines.append("Es wurde keine automatische Rechtsentscheidung getroffen.")
    body_lines.append("")
    body_lines.append("Mit freundlichen Grüßen")
    body_lines.append("")
    body_lines.append("[Name manuell eintragen]")

    title = f"Rückmeldung zu {doc_type}"

    return AnswerDraft(
        title=title,
        body="\n".join(body_lines),
        status="draft_requires_review",
        requires_review=True,
        based_on_fields=based_on,
        warnings=warnings,
        final_decision=False,
    )
