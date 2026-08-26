"""Deterministic, rule-based Bescheid fact extraction.

No ML, no remote APIs, no external dependencies. Purely regex-based
and heuristic extraction designed for German administrative documents.
"""

from __future__ import annotations

import re

from .evidence import evidence_for_match
from .models import BescheidAnalysisResult, EvidenceSpan

# ---------------------------------------------------------------------------
# Authority patterns
# ---------------------------------------------------------------------------

_AUTHORITY_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("Jobcenter", re.compile(r"(?i)\bJobcenter\b"), 1.0),
    ("Sozialamt", re.compile(r"(?i)\bSozialamt\b"), 1.0),
    ("Agentur für Arbeit", re.compile(r"(?i)\bAgentur\s+f[üu]r\s+Arbeit\b"), 0.95),
    ("Familienkasse", re.compile(r"(?i)\bFamilienkasse\b"), 1.0),
    ("Wohngeldstelle", re.compile(r"(?i)\bWohngeldstelle\b"), 1.0),
    ("Amtsgericht", re.compile(r"(?i)\bAmtsgericht\b"), 0.95),
    ("Inkasso", re.compile(r"(?i)\bInkasso\b"), 0.9),
    (
        "Rentenversicherung",
        re.compile(r"(?i)\b(?:Deutsche\s+)?Rentenversicherung\b"),
        0.95,
    ),
    ("Krankenkasse", re.compile(r"(?i)\bKrankenkasse\b"), 0.9),
    ("Finanzamt", re.compile(r"(?i)\bFinanzamt\b"), 0.95),
    ("Jugendamt", re.compile(r"(?i)\bJugendamt\b"), 0.95),
    ("Ordnungsamt", re.compile(r"(?i)\bOrdnungsamt\b"), 0.95),
    ("BAföG-Amt", re.compile(r"(?i)\bBAf[öo]G[- ]?Amt\b"), 0.95),
    ("Versorgungsamt", re.compile(r"(?i)\bVersorgungsamt\b"), 0.95),
    ("Bauamt", re.compile(r"(?i)\bBauamt\b"), 0.9),
]

# ---------------------------------------------------------------------------
# Document type patterns
# ---------------------------------------------------------------------------

_DOCUMENT_TYPE_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    (
        "Aufforderung zur Mitwirkung",
        re.compile(r"(?i)Aufforderung\s+zur\s+Mitwirkung"),
        0.95,
    ),
    ("Anhörung", re.compile(r"(?i)Anh[öo]rung(?!\w)"), 0.95),
    ("Rückforderung", re.compile(r"(?i)R[üu]ckforderung"), 0.9),
    ("Änderungsbescheid", re.compile(r"(?i)[ÄA]nderungsbescheid"), 0.9),
    ("Aufhebungsbescheid", re.compile(r"(?i)Aufhebungsbescheid"), 0.95),
    ("Ablehnungsbescheid", re.compile(r"(?i)Ablehnungsbescheid"), 0.95),
    ("Bewilligungsbescheid", re.compile(r"(?i)Bewilligungsbescheid"), 0.95),
    ("Widerspruchsbescheid", re.compile(r"(?i)Widerspruchsbescheid"), 0.95),
    (
        "Terminbestätigung",
        re.compile(r"(?i)Terminbest[äa]tigung|Terminaufforderung"),
        0.9,
    ),
    ("Mahnung", re.compile(r"(?i)\bMahnung\b"), 0.9),
    ("Nachforderung", re.compile(r"(?i)Nachforderung"), 0.9),
    ("Bescheid", re.compile(r"(?i)\bBescheid\b"), 0.85),
    ("Kostennote", re.compile(r"(?i)Kostennote|Kostenrechnung"), 0.85),
    ("Eingangsbestätigung", re.compile(r"(?i)Eingangsbest[äa]tigung"), 0.9),
]

# ---------------------------------------------------------------------------
# Deadline patterns
# ---------------------------------------------------------------------------

_DEADLINE_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # Absolute: "bis zum 15.07.2026"
    (re.compile(r"(?i)bis\s+zum\s+\d{1,2}[.]\d{1,2}[.]\d{2,4}"), 0.95),
    # Absolute: "spätestens zum 15. Juli 2026" or "spätestens zum 01.08.2026"
    # Also matches ASCII-safe variants "spaetestens"
    (
        re.compile(r"(?i)(?:sp[äa]testens|spaetestens)\s+(?:am|zum)\s+\d{1,2}[.]\d{1,2}[.]\d{2,4}"),
        0.95,
    ),
    # Absolute: "Frist bis 15.07.2026" / "Frist: 15.07.2026"
    (re.compile(r"(?i)Frist\s*(?:bis|:)?\s*\d{1,2}[.]\d{1,2}[.]\d{2,4}"), 0.9),
    # Simple: "bis 15.07.2026" (may overlap with "bis zum" - order matters)
    (re.compile(r"(?i)\bbis\s+\d{1,2}[.]\d{1,2}[.]\d{2,4}"), 0.85),
    # Absolute: "Termin am 15.07.2026 um 10:00 Uhr"
    (re.compile(r"(?i)Termin\s+am\s+\d{1,2}[.]\d{1,2}[.]\d{2,4}"), 0.9),
    # Relative: "innerhalb von 14 Tagen"
    (re.compile(r"(?i)innerhalb\s+von\s+\d+\s+(?:Tagen|Wochen|Monaten)"), 0.7),
    # Relative: "innerhalb eines Monats"
    (re.compile(r"(?i)innerhalb\s+eines\s+Monats"), 0.6),
    # Relative: "binnen 4 Wochen"
    (re.compile(r"(?i)binnen\s+\d+\s+(?:Tagen|Wochen|Monaten)"), 0.7),
    # Relative: "innerhalb von 2 Wochen nach Zustellung"
    (re.compile(r"(?i)innerhalb\s+von\s+\d+\s+Wochen\s+nach"), 0.65),
]

# ---------------------------------------------------------------------------
# Required action patterns
# ---------------------------------------------------------------------------

_ACTION_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    (
        "Unterlagen einreichen",
        re.compile(
            r"(?i)(?:reichen|legen|senden|schicken)\s+Sie\s+(?:.*?\s)?(?:die\s+)?(?:folgenden\s+|fehlenden\s+|alle\s+)?Unterlagen"
        ),
        0.9,
    ),
    (
        "Stellungnahme abgeben",
        re.compile(r"(?i)(?:nehmen|geben)\s+Sie\s+(?:.*?\s)?(?:schriftlich\s+)?Stellung"),
        0.85,
    ),
    (
        "Zahlung leisten",
        re.compile(r"(?i)(?:zahlen|überweisen|begleichen)\s+Sie\b"),
        0.85,
    ),
    (
        "Termin wahrnehmen",
        re.compile(r"(?i)(?:kommen|erscheinen)\s+Sie\s+(?:bitte\s+)?(?:zum|zu\s+dem)\s+Termin"),
        0.9,
    ),
    (
        "Angaben machen",
        re.compile(r"(?i)(?:machen|teilen)\s+Sie\s+(?:bitte\s+)?(?:Angaben|mit)\b"),
        0.8,
    ),
    (
        "Widerspruch einlegen",
        re.compile(r"(?i)Widerspruch\s+(?:einlegen|erheben|einreichen)"),
        0.9,
    ),
    (
        "Antrag stellen",
        re.compile(r"(?i)(?:stellen|einreichen)\s+Sie\s+(?:bitte\s+)?(?:einen\s+)?Antrag"),
        0.85,
    ),
    (
        "Nachweis erbringen",
        re.compile(r"(?i)(?:Nachweis|Beleg|Bescheinigung)\s+(?:erbringen|vorlegen|einreichen)"),
        0.85,
    ),
    (
        "Kontoauszug vorlegen",
        re.compile(r"(?i)Kontoausz(?:ug|üge)\s+(?:vorlegen|einreichen)"),
        0.9,
    ),
    (
        "Mietvertrag vorlegen",
        re.compile(r"(?i)Mietvertrag\s+(?:vorlegen|einreichen)"),
        0.9,
    ),
]

# ---------------------------------------------------------------------------
# Missing document patterns
# ---------------------------------------------------------------------------

_MISSING_DOC_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("Kontoauszüge", re.compile(r"(?i)Kontoausz(?:[üu]ge?|ug)"), 0.9),
    ("Mietvertrag", re.compile(r"(?i)Mietvertrag"), 0.95),
    (
        "Lohnabrechnung",
        re.compile(r"(?i)Lohn(?:abrechnung|bescheinigung|nachweis)"),
        0.9,
    ),
    ("Einkommensnachweis", re.compile(r"(?i)Einkommensnachweis"), 0.9),
    ("Personalausweis", re.compile(r"(?i)Personalausweis|Lichtbildausweis"), 0.9),
    ("Meldebescheinigung", re.compile(r"(?i)Meldebescheinigung"), 0.95),
    ("Mietbescheinigung", re.compile(r"(?i)Mietbescheinigung"), 0.95),
    (
        "Krankenversicherungsnachweis",
        re.compile(r"(?i)Krankenversicherungsnachweis|Krankenkassenbescheinigung"),
        0.9,
    ),
    ("Arbeitsvertrag", re.compile(r"(?i)Arbeitsvertrag"), 0.9),
    ("Steuerbescheid", re.compile(r"(?i)Steuerbescheid"), 0.9),
    ("Rentenbescheid", re.compile(r"(?i)Rentenbescheid"), 0.9),
    (
        "Schulbescheinigung",
        re.compile(r"(?i)Schulbescheinigung"),
        0.9,
    ),
    (
        "Immatrikulationsbescheinigung",
        re.compile(r"(?i)Immatrikulationsbescheinigung"),
        0.9,
    ),
    (
        "Unterhaltsbescheinigung",
        re.compile(r"(?i)Unterhaltsbescheinigung|Unterhaltsnachweis"),
        0.9,
    ),
    ("Vollmacht", re.compile(r"(?i)Vollmacht|Vorsorgevollmacht"), 0.8),
    ("Geburtsurkunde", re.compile(r"(?i)Geburtsurkunde"), 0.95),
    ("Heiratsurkunde", re.compile(r"(?i)Heiratsurkunde|Eheurkunde"), 0.95),
    ("Scheidungsurteil", re.compile(r"(?i)Scheidungsurteil"), 0.95),
    ("Schwerbehindertenausweis", re.compile(r"(?i)Schwerbehindertenausweis"), 0.95),
    (
        "Aufenthaltstitel",
        re.compile(r"(?i)Aufenthaltstitel|Aufenthaltserlaubnis"),
        0.95,
    ),
    ("Wohngeldbescheid", re.compile(r"(?i)Wohngeldbescheid"), 0.9),
]

# ---------------------------------------------------------------------------
# Risk indicators
# ---------------------------------------------------------------------------

_HIGH_RISK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(?:versagt|entzogen|eingestellt|gestrichen)\s*(?:werden|wird)"),
    re.compile(r"(?i)(?:droht|drohendes?)\s+(?:Versagung|Einstellung|Entziehung|Vollstreckung)"),
    re.compile(r"(?i)(?:Zwangsvollstreckung|Pf[äa]ndung|Vollstreckungsbescheid)"),
    re.compile(r"(?i)(?:Klage|Klageerhebung|gerichtlich(?:es|en)?\s+(?:Mahnverfahren|Verfahren))"),
    re.compile(r"(?i)(?:Vers[äa]umnisurteil|S[äa]umnis)"),
]

_MEDIUM_RISK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(?:Frist|Fristablauf|fristgerecht)"),
    re.compile(r"(?i)(?:aufforderung|aufgefordert|fordern\s+wir\s+Sie\s+auf)"),
    re.compile(r"(?i)(?:ansonsten|andernfalls|widrigenfalls)"),
    re.compile(r"(?i)(?:Nachteil|nachteilig)"),
]

# ---------------------------------------------------------------------------
# Letter date patterns
# ---------------------------------------------------------------------------

_LETTER_DATE_PATTERN = re.compile(
    r"(?i)(?:Datum|vom|ausgestellt\s+am)[:\s]*(\d{1,2}[.]\d{1,2}[.]\d{2,4})"
)
_DATE_FALLBACK_PATTERN = re.compile(
    r"(?i)(?:Musterstadt|Ort),\s*(?:den\s+)?(\d{1,2}[.]\d{1,2}[.]\d{2,4})"
)


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_bescheid_facts(text: str) -> BescheidAnalysisResult:
    """Extract structured facts from a German administrative notice.

    All extraction is deterministic, regex-based, and runs without
    network, APIs, or external models. Every critical finding is
    anchored by an EvidenceSpan.

    Parameters
    ----------
    text: The full Bescheid document text.

    Returns
    -------
    BescheidAnalysisResult with extracted fields and evidence.
    """
    evidence: list[EvidenceSpan] = []
    warnings: list[str] = []

    # --- Authority ---
    authority: str | None = None
    for name, pattern, confidence in _AUTHORITY_PATTERNS:
        match = pattern.search(text)
        if match:
            authority = name
            evidence.append(
                evidence_for_match("authority", text, match.start(), match.end(), confidence)
            )
            break

    if authority is None:
        warnings.append("Behörde nicht erkannt — manuelle Prüfung nötig")

    # --- Document type ---
    document_type: str | None = None
    for name, pattern, confidence in _DOCUMENT_TYPE_PATTERNS:
        match = pattern.search(text)
        if match:
            document_type = name
            evidence.append(
                evidence_for_match("document_type", text, match.start(), match.end(), confidence)
            )
            break

    # --- Letter date ---
    letter_date: str | None = None
    date_match = _LETTER_DATE_PATTERN.search(text)
    if date_match:
        letter_date = date_match.group(1)
        evidence.append(
            evidence_for_match("letter_date", text, date_match.start(), date_match.end(), 0.9)
        )
    else:
        date_match = _DATE_FALLBACK_PATTERN.search(text)
        if date_match:
            letter_date = date_match.group(1)
            evidence.append(
                evidence_for_match("letter_date", text, date_match.start(), date_match.end(), 0.7)
            )

    # --- Deadline ---
    deadline: str | None = None
    for pattern, confidence in _DEADLINE_PATTERNS:
        match = pattern.search(text)
        if match:
            deadline = match.group(0).strip()
            evidence.append(
                evidence_for_match("deadline", text, match.start(), match.end(), confidence)
            )
            break

    if deadline is None:
        warnings.append("Keine Frist erkannt")

    # --- Required action ---
    required_action: str | None = None
    for action_name, pattern, confidence in _ACTION_PATTERNS:
        match = pattern.search(text)
        if match:
            required_action = action_name
            evidence.append(
                evidence_for_match("required_action", text, match.start(), match.end(), confidence)
            )
            break

    if required_action is None:
        warnings.append("Keine Handlungspflicht erkannt")

    # --- Missing documents ---
    missing_documents: list[str] = []
    for doc_name, pattern, confidence in _MISSING_DOC_PATTERNS:
        match = pattern.search(text)
        if match:
            if doc_name not in missing_documents:
                missing_documents.append(doc_name)
            evidence.append(
                evidence_for_match(
                    "missing_documents", text, match.start(), match.end(), confidence
                )
            )

    # --- Risk level ---
    risk_level = _assess_risk(text, deadline, required_action)
    if deadline is None and risk_level == "low":
        risk_level = "medium"

    return BescheidAnalysisResult(
        authority=authority,
        document_type=document_type,
        letter_date=letter_date,
        deadline=deadline,
        required_action=required_action,
        missing_documents=sorted(missing_documents),
        risk_level=risk_level,
        evidence=evidence,
        warnings=warnings,
    )


def _assess_risk(text: str, deadline: str | None, action: str | None) -> str:
    """Heuristic risk assessment based on text patterns."""
    high_count = sum(1 for p in _HIGH_RISK_PATTERNS if p.search(text))
    medium_count = sum(1 for p in _MEDIUM_RISK_PATTERNS if p.search(text))

    if high_count >= 1:
        return "high"
    if medium_count >= 2 or (deadline is not None and medium_count >= 1):
        return "medium"
    if action is not None:
        return "low"
    return "unknown"
