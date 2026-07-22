"""Citation resolution service for M7-A.

Resolves legal citations like "§ 48 SGB X" to specific provisions
in the local legal corpus.

Resolution strategy:
1. Parse citation string
2. Find instrument by abbreviation
3. Find current expression
4. Find provision by number
5. Return resolved citation

No LLM is used. Purely deterministic lookup.
"""

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from private_legal_navigator.domain.legal_source import (
    CitationRequest,
    LegalCitation,
    LegalInstrument,
    LegalProvision,
    ResolutionConfidence,
    ResolutionStatus,
)
from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)

logger = logging.getLogger("private_legal_navigator.citation")


@dataclass
class ResolvedCitation:
    """Result of a citation resolution attempt."""

    raw: str
    instrument: LegalInstrument | None = None
    provision: LegalProvision | None = None
    status: ResolutionStatus = ResolutionStatus.PENDING
    confidence: ResolutionConfidence = ResolutionConfidence.UNKNOWN
    detail: str = ""
    authority_tier_display: str = ""
    retrieval_date: str = ""
    source_note: str = ""
    temporal_warning: str = ""


class CitationResolver:
    """Resolves legal citation strings to specific provisions."""

    # Regex for common German legal citation patterns
    CITATION_PATTERN = re.compile(
        r"§\s*(\d+[a-z]?)\s*(?:Abs\.?\s*(\d+))?\s*(?:Satz\s*(\d+))?\s*(?:Nr\.?\s*(\d+))?\s*(?:([A-Za-zäöüßÄÖÜ\s\-\.]+))",
        re.IGNORECASE,
    )

    def __init__(self, repo: SqliteLegalSourceRepository) -> None:
        self._repo = repo

    def parse_citation(self, raw: str) -> CitationRequest:
        """Parse a raw citation string into structured components.

        Examples:
            "§ 48 SGB X" → paragraph=48, law_abbreviation="SGB X"
            "§ 48 Abs. 1 Satz 2 Nr. 3 SGB X" → full decomposition
        """
        raw = raw.strip()
        match = self.CITATION_PATTERN.match(raw)
        if match:
            return CitationRequest(
                raw=raw,
                paragraph_number=match.group(1) or "",
                clause_number=match.group(2) or "",
                sentence_number=match.group(3) or "",
                alternative_number=match.group(4) or "",
                law_abbreviation=(match.group(5) or "").strip(),
            )

        # Fallback: try to extract paragraph and law name
        parts = raw.split()
        paragraph_num = ""
        law_abbrev = ""
        for i, part in enumerate(parts):
            if part.startswith("§"):
                paragraph_num = part.lstrip("§").strip()
                law_abbrev = " ".join(parts[i + 1 :]) if i + 1 < len(parts) else ""
                break
            elif part.replace(".", "").replace("-", "").isdigit():
                # Could be a paragraph number without § symbol
                law_abbrev = " ".join(parts[i + 1 :]) if i + 1 < len(parts) else ""

        return CitationRequest(
            raw=raw,
            paragraph_number=paragraph_num,
            law_abbreviation=law_abbrev,
        )

    def resolve(self, raw: str) -> ResolvedCitation:
        """Resolve a citation string to a specific provision.

        Args:
            raw: Citation string like "§ 48 SGB X"

        Returns:
            ResolvedCitation with status, instrument, and provision if found.
        """
        parsed = self.parse_citation(raw)
        result = ResolvedCitation(raw=raw)

        if not parsed.law_abbreviation:
            result.status = ResolutionStatus.NOT_FOUND
            result.detail = (
                "Kein Gesetz in der Eingabe erkannt. "
                "Bitte geben Sie die Zitierung im Format '§ 48 SGB X' ein."
            )
            return result

        # Step 1: Find instrument by abbreviation
        instrument = self._repo.get_instrument_by_abbreviation(parsed.law_abbreviation)
        if instrument is None:
            # Try case-insensitive search
            instruments = self._repo.list_instruments(jurisdiction="DE")
            for inst in instruments:
                if inst.abbreviation.upper() == parsed.law_abbreviation.upper():
                    instrument = inst
                    break

        if instrument is None:
            result.status = ResolutionStatus.NOT_FOUND
            result.detail = (
                f"Kein Gesetz mit der Abkürzung '{parsed.law_abbreviation}' gefunden. "
                f"Bitte synchronisieren Sie zuerst die Rechtsquelle."
            )
            return result

        result.instrument = instrument
        result.authority_tier_display = instrument.authority_tier.value

        # Step 2: Find current expression
        expression = self._repo.get_current_expression(instrument.instrument_id)
        if expression is None:
            expressions = self._repo.list_expressions(instrument.instrument_id)
            if expressions:
                expression = expressions[0]

        if expression is None:
            result.status = ResolutionStatus.NOT_FOUND
            result.detail = (
                f"Gesetz '{instrument.abbreviation}' gefunden, aber keine Textfassung verfügbar."
            )
            return result

        result.source_note = expression.source_note
        if expression.retrieved_at:
            result.retrieval_date = expression.retrieved_at.isoformat()

        # Temporal warning for non-official sources
        if instrument.authority_tier in (
            "CONSOLIDATED_NON_OFFICIAL",
            "UNKNOWN",
        ):
            result.temporal_warning = (
                "HINWEIS: Dieser Text ist eine konsolidierte, nicht amtliche Fassung. "
                f"Abgerufen am {result.retrieval_date}. "
                "Es wird keine Garantie für historische Vollständigkeit übernommen."
            )
        if expression.historical_completeness == "CURRENT_ONLY":
            result.temporal_warning += " Frühere Fassungen sind möglicherweise nicht verfügbar."

        # Step 3: Find provision
        if not parsed.paragraph_number:
            result.status = ResolutionStatus.AMBIGUOUS
            result.detail = "Kein Paragraph angegeben. Bitte spezifizieren Sie die Norm."
            return result

        # Try finding by searching provisions for this expression
        provisions = self._repo.get_provisions_for_expression(expression.expression_id)
        found_provision = None

        # Look for paragraph number match
        para_num = parsed.paragraph_number
        for prov in provisions:
            # Match against provision_number or stable_key
            if prov.provision_number == f"§{para_num}" or prov.provision_number == para_num:
                found_provision = prov
                break
            if para_num in prov.stable_key or para_num in prov.provision_number:
                found_provision = prov
                break

        # Also try FTS5 search for the paragraph number
        if found_provision is None:
            fts_results = self._repo.search_provisions_fts(f'"{para_num}"', limit=5)
            for fts_row in fts_results:
                prov_id = fts_row.get("provision_id")
                if prov_id:
                    try:
                        prov = self._repo.get_provision(uuid.UUID(prov_id))
                        if prov and prov.expression_id == expression.expression_id:
                            found_provision = prov
                            break
                    except (ValueError, TypeError):
                        pass

        if found_provision is None:
            result.status = ResolutionStatus.NOT_FOUND
            result.detail = (
                f"Paragraph {para_num} in {instrument.abbreviation} nicht gefunden. "
                f"({len(provisions)} Vorschriften im Korpus durchsucht)"
            )
            return result

        result.provision = found_provision
        result.status = ResolutionStatus.RESOLVED
        result.confidence = ResolutionConfidence.EXACT
        result.detail = (
            f"Gefunden: {found_provision.provision_number}"
            + (f" — {found_provision.heading}" if found_provision.heading else "")
            + f" in {instrument.abbreviation}"
        )

        return result

    def save_citation_record(self, raw: str, resolved: ResolvedCitation) -> LegalCitation:
        """Persist a citation resolution as a LegalCitation record."""
        citation = LegalCitation(
            citation_id=uuid.uuid4(),
            source_entity_type="citation_resolver",
            citation_text=raw,
            resolved_instrument_id=(
                resolved.instrument.instrument_id if resolved.instrument else None
            ),
            resolved_provision_id=(resolved.provision.provision_id if resolved.provision else None),
            resolution_status=resolved.status,
            resolution_confidence=resolved.confidence,
            reviewed_at=datetime.now(),
            resolution_detail=resolved.detail,
        )
        self._repo.save_citation(citation)
        return citation


def format_resolution_for_display(resolved: ResolvedCitation) -> str:
    """Format a citation resolution for CLI/UI display."""
    lines: list[str] = []

    if resolved.status == ResolutionStatus.RESOLVED:
        lines.append(f"✓ GEFUNDEN: {resolved.detail}")
        if resolved.instrument:
            lines.append(f"  Gesetz: {resolved.instrument.official_title}")
            lines.append(f"  Abkürzung: {resolved.instrument.abbreviation}")
            lines.append(f"  Autorität: {resolved.authority_tier_display}")
        if resolved.provision:
            lines.append(f"  Paragraph: {resolved.provision.provision_number}")
            if resolved.provision.heading:
                lines.append(f"  Überschrift: {resolved.provision.heading}")
            lines.append(f"  Text (Auszug): {resolved.provision.text_content[:200]}...")
        if resolved.retrieval_date:
            lines.append(f"  Abrufdatum: {resolved.retrieval_date}")
        if resolved.temporal_warning:
            lines.append(f"  ⚠ {resolved.temporal_warning}")
    elif resolved.status == ResolutionStatus.AMBIGUOUS:
        lines.append(f"⚠ NICHT EINDEUTIG: {resolved.detail}")
    elif resolved.status == ResolutionStatus.NOT_FOUND:
        lines.append(f"✗ NICHT GEFUNDEN: {resolved.detail}")
    else:
        lines.append(f"? UNBEKANNT: {resolved.detail}")

    return "\n".join(lines)
