"""Local structured text export for BescheidPilot analysis results.

All exports are local-only: no network, no upload, no remote services.
Every export clearly states that human review is mandatory and that no
legal decision has been made.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .models import BescheidAnalysisResult


def render_analysis_export(
    result: BescheidAnalysisResult,
    include_draft: bool = False,
) -> str:
    """Render an analysis result as a structured text document.

    The output contains all extracted fields, review items, evidence
    spans, and warnings. It explicitly states that human review is
    required and that no legal decision has been made.

    No network access. No external dependencies. No sensitive logging.
    """
    lines: list[str] = []

    # ---- Header ----
    lines.append("=" * 60)
    lines.append("BESCHEIDPILOT ANALYSE-EXPORT")
    lines.append("=" * 60)
    lines.append("")

    # ---- Status ----
    lines.append("--- STATUS ---")
    if result.review_required:
        lines.append("Status: PRÜFUNG ERFORDERLICH")
    else:
        lines.append("Status: Prüfung empfohlen")
    lines.append(f"Review required: {'Ja' if result.review_required else 'Nein'}")
    lines.append(f"Finale Entscheidung: {'NEIN' if not result.final_decision else 'JA'}")
    lines.append("")

    # ---- Mandatory notice ----
    lines.append("--- WICHTIGER HINWEIS ---")
    lines.append("Diese Analyse ist ein technischer Entwurf und ersetzt keine Rechtsberatung.")
    lines.append(
        "Alle Fristen, Handlungen und Unterlagen müssen durch einen Menschen geprüft werden."
    )
    lines.append("")

    # ---- Extracted data ----
    lines.append("--- ERKANNTE DATEN ---")
    if result.authority:
        lines.append(f"Behörde: {result.authority}")
    else:
        lines.append("Behörde: nicht erkannt")
    if result.document_type:
        lines.append(f"Dokumenttyp: {result.document_type}")
    else:
        lines.append("Dokumenttyp: nicht erkannt")
    if result.letter_date:
        lines.append(f"Datum des Schreibens: {result.letter_date}")
    if result.deadline:
        lines.append(f"Frist: {result.deadline}")
    else:
        lines.append("Frist: keine erkannt")
    if result.required_action:
        lines.append(f"Handlung: {result.required_action}")
    else:
        lines.append("Handlung: keine erkannt")
    if result.missing_documents:
        lines.append("Fehlende Unterlagen:")
        for doc in result.missing_documents:
            lines.append(f"  - {doc}")
    else:
        lines.append("Fehlende Unterlagen: keine erkannt")
    lines.append("")

    # ---- Risk ----
    lines.append("--- RISIKO ---")
    lines.append(f"Risiko-Level: {result.risk_level.upper()}")
    lines.append("")

    # ---- Review items ----
    if result.review_items:
        lines.append("--- REVIEW-PFLICHT ---")
        for ri in result.review_items:
            ev_status = "vorhanden" if ri.evidence_present else "fehlt"
            lines.append(
                f"  {ri.field}: {ri.status} | Severity: {ri.severity} | Evidence: {ev_status}"
            )
            if ri.reason:
                lines.append(f"    Grund: {ri.reason}")
        lines.append("")

    # ---- Evidence spans ----
    if result.evidence:
        lines.append("--- FUNDSTELLEN ---")
        for ev in result.evidence:
            quote_short = ev.quote[:120].replace("\n", " ")
            if len(ev.quote) > 120:
                quote_short += "..."
            lines.append(f"  {ev.field}: {ev.value} [confidence={ev.confidence:.0%}]")
            if quote_short.strip():
                lines.append(f'    Quelle: "{quote_short}"')
    else:
        lines.append("--- FUNDSTELLEN ---")
        lines.append("  Keine Fundstellen vorhanden.")
    lines.append("")

    # ---- Warnings ----
    all_warnings = list(result.warnings)
    if result.critical_warnings:
        all_warnings.extend(result.critical_warnings)
    if all_warnings:
        lines.append("--- WARNUNGEN ---")
        for w in all_warnings:
            lines.append(f"  - {w}")
        lines.append("")

    # ---- Limits ----
    lines.append("--- GRENZEN ---")
    lines.append("Dieser Export ist lokal erzeugt.")
    lines.append("Es wurde keine automatische Rechtsentscheidung getroffen.")
    lines.append("Der Export ersetzt keine Prüfung durch eine fachkundige Person.")
    lines.append("")

    lines.append("=" * 60)

    lines.append("=" * 60)

    # ---- Optional answer draft ----
    if include_draft:
        lines.append("")
        lines.append("--- ANTWORTENTWURF ---")
        if result.answer_draft:
            lines.append(f"Titel: {result.answer_draft.title}")
            lines.append(f"Status: {result.answer_draft.status}")
            lines.append("Review required: Ja")
            lines.append("Finale Entscheidung: NEIN")
            lines.append("")
            lines.append(result.answer_draft.body)
        else:
            lines.append("Kein Antwortentwurf vorhanden.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File export with local-path safety
# ---------------------------------------------------------------------------

_FORBIDDEN_SCHEMES = frozenset({"http", "https", "ftp", "ftps", "sftp", "ssh"})


def _is_safe_local_path(path_str: str) -> bool:
    """Return True if *path_str* looks like a safe local filesystem path."""
    if not path_str or not path_str.strip():
        return False
    parsed = urlparse(path_str)
    if parsed.scheme and parsed.scheme.lower() in _FORBIDDEN_SCHEMES:
        return False
    return not (path_str.startswith("//") or path_str.startswith("\\\\"))


def write_analysis_export(
    result: BescheidAnalysisResult,
    output_path: str,
    include_draft: bool = False,
) -> None:
    """Write the analysis export to a local UTF-8 text file.

    Only local filesystem paths are allowed. URLs, network paths, and
    empty paths are rejected. The target directory must exist.
    """
    if not _is_safe_local_path(output_path):
        raise ValueError("[REDACTED_PATH]: Ungültiger oder nicht-lokaler Exportpfad")

    target = Path(output_path).resolve()

    if not target.parent.is_dir():
        raise FileNotFoundError("[REDACTED_PATH]: Zielverzeichnis existiert nicht")

    rendered = render_analysis_export(result, include_draft=include_draft)
    target.write_text(rendered, encoding="utf-8")
