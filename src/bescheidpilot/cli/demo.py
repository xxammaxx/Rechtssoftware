"""Pilot Demo CLI — local end-to-end BescheidPilot text analysis.

Usage:
    python -m bescheidpilot.cli.demo --input <file> [--export <path>] [--include-draft]

No network, no remote LLM, no cloud OCR. Human review mandatory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from bescheidpilot.core import (
    BescheidAnalysisResult,
    analyze_bescheid_text,
    create_answer_draft,
    write_analysis_export,
)
from bescheidpilot.core.network_guard import deny_network


def _is_safe_local_path(path_str: str) -> bool:
    if not path_str or not path_str.strip():
        return False
    parsed = urlparse(path_str)
    forbidden = {"http", "https", "ftp", "ftps"}
    if parsed.scheme and parsed.scheme.lower() in forbidden:
        return False
    return not (path_str.startswith("//") or path_str.startswith("\\\\"))


def _print_banner() -> None:
    print("=" * 60)
    print("BESCHEIDPILOT PILOT-DEMO")
    print("=" * 60)
    print()
    print("Status: PRÜFUNG ERFORDERLICH")
    print("Finale Entscheidung: NEIN")
    print("Local-only: keine Cloud, keine Uploads, keine Remote-KI")
    print()


def _print_result(result: BescheidAnalysisResult) -> None:
    print("=" * 60)
    print("ERKANNTE DATEN")
    print("=" * 60)
    if result.authority:
        print(f"  Behörde: {result.authority}")
    else:
        print("  Behörde: nicht erkannt")
    if result.document_type:
        print(f"  Dokumenttyp: {result.document_type}")
    else:
        print("  Dokumenttyp: nicht erkannt")
    if result.letter_date:
        print(f"  Datum des Schreibens: {result.letter_date}")
    if result.deadline:
        print(f"  Frist: {result.deadline}")
    else:
        print("  Frist: keine erkannt")
    if result.required_action:
        print(f"  Handlung: {result.required_action}")
    else:
        print("  Handlung: keine erkannt")
    if result.missing_documents:
        print("  Fehlende Unterlagen:")
        for doc in result.missing_documents:
            print(f"    - {doc}")
    else:
        print("  Fehlende Unterlagen: keine erkannt")
    print()

    print("=" * 60)
    print("RISIKO")
    print("=" * 60)
    print(f"  Risiko-Level: {result.risk_level.upper()}")
    print()

    if result.review_items:
        print("=" * 60)
        print("REVIEW-PFLICHT")
        print("=" * 60)
        for ri in result.review_items:
            ev = "vorhanden" if ri.evidence_present else "fehlt"
            print(f"  {ri.field}: {ri.status} | {ri.severity} | Evidence: {ev}")
            if ri.reason:
                print(f"    Grund: {ri.reason}")
        print()

    if result.evidence:
        print("=" * 60)
        print("FUNDSTELLEN")
        print("=" * 60)
        for evidence_span in result.evidence[:10]:
            quote = evidence_span.quote[:100].replace("\n", " ")
            if len(evidence_span.quote) > 100:
                quote += "..."
            print(
                f"  {evidence_span.field}: {evidence_span.value} "
                f"[confidence={evidence_span.confidence:.0%}]"
            )
            if quote.strip():
                print(f'    "{quote}"')
        print()

    if result.warnings:
        print("=" * 60)
        print("WARNUNGEN")
        print("=" * 60)
        for w in result.warnings:
            print(f"  - {w}")
        print()

    print("Hinweis: Diese Analyse ersetzt keine Rechtsberatung.")
    print("Menschliche Prüfung vor Verwendung zwingend erforderlich.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="BescheidPilot Pilot Demo CLI — lokale Textanalyse"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Pfad zur lokalen Bescheid-Textdatei",
    )
    parser.add_argument(
        "--export",
        "-e",
        default=None,
        help="Export-Pfad für lokale strukturierte Ausgabe",
    )
    parser.add_argument(
        "--include-draft",
        action="store_true",
        help="Antwortentwurf in Export einschließen",
    )

    args = parser.parse_args(argv)

    # Input safety
    if not _is_safe_local_path(args.input):
        print(
            "[FEHLER]: Ungültiger Eingabepfad — nur lokale Dateien erlaubt",
            file=sys.stderr,
        )
        return 1

    input_path = Path(args.input)
    if not input_path.is_file():
        print("[FEHLER]: Datei nicht gefunden", file=sys.stderr)
        return 1

    # Load input
    try:
        text = input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("[FEHLER]: Datei konnte nicht als UTF-8 gelesen werden", file=sys.stderr)
        return 1

    if not text.strip():
        print("[FEHLER]: Datei ist leer", file=sys.stderr)
        return 1

    # Analyze
    _print_banner()

    with deny_network():
        result = analyze_bescheid_text(text)

    _print_result(result)

    # Export
    if args.export:
        if not _is_safe_local_path(args.export):
            print("[FEHLER]: Ungültiger Export-Pfad", file=sys.stderr)
            return 1

        if args.include_draft:
            draft = create_answer_draft(result)
            from dataclasses import replace

            result = replace(result, answer_draft=draft)

        try:
            write_analysis_export(result, args.export, include_draft=args.include_draft)
            print(f"Export geschrieben nach: {args.export}")
            if args.include_draft:
                print("Antwortentwurf im Export enthalten (prüfpflichtig).")
        except Exception:
            print("[FEHLER]: Export fehlgeschlagen", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
