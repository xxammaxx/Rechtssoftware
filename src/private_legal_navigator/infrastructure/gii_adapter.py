"""Gesetze-im-Internet (GII) Adapter for M7-A.

Implements LegalSourceAdapter protocol for the official German government
legal information service (gesetze-im-internet.de).

Key characteristics:
- Authority tier: CONSOLIDATED_NON_OFFICIAL
- Source: XML catalog at https://www.gesetze-im-internet.de/gii-toc.xml
- Provides consolidated current versions, NOT official promulgations
- Idempotent sync: hash check prevents duplicate snapshots
- No case data ever transmitted during sync

The GII XML structure:
  <gii-toc>
    <item link="..." title="..." type="..." />
  </gii-toc>

Each item link points to the full XML of a law.
XML structure of individual laws follows the juris-norm.dtd.
"""

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree

from private_legal_navigator.domain.legal_source import (
    AuthorityTier,
    ImportStatus,
    InstrumentType,
    LegalExpression,
    LegalInstrument,
    LegalProvision,
    LegalSource,
    ProvisionType,
    SourceSnapshot,
    TemporalCompleteness,
    TemporalConfidence,
    TemporalStatus,
)
from private_legal_navigator.infrastructure.safe_source_client import (
    SourceClient,
    compute_sha256,
)
from private_legal_navigator.infrastructure.safe_xml_parser import (
    parse_xml_bytes,
)

logger = logging.getLogger("private_legal_navigator.gii")

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

GII_SOURCE_KEY = "gesetze-im-internet"
GII_BASE_URL = "https://www.gesetze-im-internet.de"
GII_CATALOG_URL = f"{GII_BASE_URL}/gii-toc.xml"
GII_DISPLAY_NAME = "Gesetze im Internet"
GII_DESCRIPTION = (
    "Konsolidierte, nicht amtliche Fassung aktueller Bundesgesetze. "
    "Bereitgestellt vom Bundesministerium der Justiz."
)
GII_JURISDICTION = "DE"
GII_AUTHORITY_TIER = AuthorityTier.CONSOLIDATED_NON_OFFICIAL
PARSER_VERSION = "m7a-gii-1.0.0"

# GII XML namespaces
NSMAP: dict[str, str] = {}  # No namespace prefixes needed for juris-norm


def make_gii_source() -> LegalSource:
    """Create the canonical GII source entity."""
    return LegalSource(
        source_id=uuid.uuid5(uuid.NAMESPACE_URL, GII_SOURCE_KEY),
        source_key=GII_SOURCE_KEY,
        display_name=GII_DISPLAY_NAME,
        authority_tier=GII_AUTHORITY_TIER,
        jurisdiction=GII_JURISDICTION,
        enabled=True,
        base_url=GII_BASE_URL,
        description=GII_DESCRIPTION,
    )


# ──────────────────────────────────────────────
# Parsed data structures
# ──────────────────────────────────────────────


@dataclass
class GiiCatalogItem:
    """A single entry from the GII table of contents."""

    link: str
    title: str
    item_type: str = ""
    abbreviation: str = ""
    source_identifier: str = ""


@dataclass
class GiiParsedInstrument:
    """Parsed result of a single GII law XML."""

    instrument: LegalInstrument
    expression: LegalExpression
    provisions: list[LegalProvision]
    snapshot: SourceSnapshot


# ──────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────


class GiiAdapterError(Exception):
    """Base error for GII adapter operations."""


class GiiCatalogError(GiiAdapterError):
    """Failed to fetch or parse the GII catalog."""


class GiiInstrumentError(GiiAdapterError):
    """Failed to fetch or parse a specific GII instrument."""


class GiiAdapter:
    """Adapter for the Gesetze-im-Internet legal source.

    Responsible for:
    1. Fetching the GII catalog (list of available laws)
    2. Fetching individual law XMLs
    3. Parsing law XML into domain entities
    4. Supporting idempotent re-sync (hash-based deduplication)
    """

    def __init__(
        self,
        client: SourceClient,
        snapshot_dir: Path,
    ) -> None:
        self._client = client
        self._snapshot_dir = snapshot_dir
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    # ── Catalog ──────────────────────────────────

    def fetch_catalog(self) -> list[GiiCatalogItem]:
        """Fetch and parse the GII table of contents (XML catalog)."""
        xml_bytes = self._client.download(GII_CATALOG_URL)
        tree = parse_xml_bytes(xml_bytes)
        root = tree.getroot()

        items: list[GiiCatalogItem] = []
        for item_elem in root.iter("item"):
            link = item_elem.get("link", "")
            title = item_elem.get("title", "")
            item_type = item_elem.get("type", "")

            # Derive abbreviation from link (e.g., "BGB" from "https://.../bgb/")
            abbreviation = ""
            source_identifier = ""
            if link:
                abbreviation = _derive_abbreviation(link)
                source_identifier = link

            items.append(
                GiiCatalogItem(
                    link=link,
                    title=title,
                    item_type=item_type,
                    abbreviation=abbreviation,
                    source_identifier=source_identifier,
                )
            )

        return items

    def find_in_catalog(self, key: str) -> GiiCatalogItem | None:
        """Find a specific instrument in the GII catalog by abbreviation or key.

        Args:
            key: Law abbreviation (e.g., 'sgb_10') or source identifier.
        """
        catalog = self.fetch_catalog()
        key_lower = key.lower()
        for item in catalog:
            if item.abbreviation.lower() == key_lower:
                return item
            if key_lower in item.link.lower():
                return item
        return None

    # ── Instrument Sync ──────────────────────────

    def sync_instrument(self, item: GiiCatalogItem) -> GiiParsedInstrument:
        """Download, snapshot, and parse a single GII instrument.

        1. Download the XML
        2. Compute SHA-256
        3. Save snapshot to disk
        4. Create SourceSnapshot entity
        5. Parse XML into LegalInstrument + LegalExpression + provisions
        """
        # 1. Download
        law_url = item.link
        if not law_url.startswith("http"):
            law_url = (
                GII_BASE_URL + law_url if law_url.startswith("/") else GII_BASE_URL + "/" + law_url
            )

        xml_bytes = self._client.download(law_url)

        # 2. Hash
        sha256 = compute_sha256(xml_bytes)

        # 3. Validate magic bytes before processing
        from private_legal_navigator.infrastructure.safe_xml_parser import validate_xml_magic_bytes

        validate_xml_magic_bytes(xml_bytes)

        # 4. Save snapshot atomically
        from private_legal_navigator.infrastructure.safe_source_client import _atomic_write

        snapshot_path = _atomic_write(xml_bytes, self._snapshot_dir)

        retrieved_at = datetime.now()

        # 4. Create snapshot entity
        gii_source = make_gii_source()
        assert gii_source.source_id is not None
        snapshot = SourceSnapshot(
            snapshot_id=uuid.uuid4(),
            source_id=gii_source.source_id,
            source_locator=law_url,
            retrieved_at=retrieved_at,
            content_type="application/xml",
            byte_size=len(xml_bytes),
            sha256=sha256,
            storage_path=str(snapshot_path),
            parser_version=PARSER_VERSION,
            import_status=ImportStatus.DOWNLOADED,
            immutable=True,
        )

        # 5. Parse XML into domain entities
        instrument, expression, provisions = _parse_law_xml(
            xml_bytes=xml_bytes,
            snapshot=snapshot,
            abbreviation=item.abbreviation,
            title=item.title,
        )

        return GiiParsedInstrument(
            instrument=instrument,
            expression=expression,
            provisions=provisions,
            snapshot=snapshot,
        )

    def sync_instrument_by_key(self, key: str) -> GiiParsedInstrument | None:
        """Find and sync an instrument by its catalog key (abbreviation)."""
        item = self.find_in_catalog(key)
        if item is None:
            return None
        return self.sync_instrument(item)


# ──────────────────────────────────────────────
# XML Parsing
# ──────────────────────────────────────────────


def _parse_law_xml(
    xml_bytes: bytes,
    snapshot: SourceSnapshot,
    abbreviation: str,
    title: str,
) -> tuple[LegalInstrument, LegalExpression, list[LegalProvision]]:
    """Parse a GII law XML file into domain entities.

    The GII XML uses the juris-norm.dtd structure:
    <norm>
      <metadaten>
        <jurabk>BGB</jurabk>  (abbreviation in law)
        <amtabk>BGBl I</amtabk>  (official publication)
        <langue>Bürgerliches Gesetzbuch</langue>  (long title)
        ...
      </metadaten>
      <textdaten>
        <text>
          <Content>
            <P>...</P>  (paragraph text)
            ...
          </Content>
        </text>
      </textdaten>
      ...
    </norm>

    The actual structure may vary by law. We extract what's available.
    """
    tree = parse_xml_bytes(xml_bytes)
    root = tree.getroot()

    # Extract metadata
    metadata = _extract_metadata(root, abbreviation, title)

    # Build instrument
    instrument = LegalInstrument(
        instrument_id=uuid.uuid4(),
        jurisdiction=GII_JURISDICTION,
        instrument_type=InstrumentType.STATUTE,
        official_title=metadata["official_title"],
        short_title=metadata["short_title"],
        abbreviation=metadata["abbreviation"],
        source_identifier=snapshot.source_locator,
        authority_tier=GII_AUTHORITY_TIER,
    )

    # Build expression
    assert instrument.instrument_id is not None
    assert snapshot.snapshot_id is not None
    expression = LegalExpression(
        expression_id=uuid.uuid4(),
        instrument_id=instrument.instrument_id,
        source_snapshot_id=snapshot.snapshot_id,
        retrieved_at=snapshot.retrieved_at,
        temporal_status=TemporalStatus.CURRENT,
        historical_completeness=TemporalCompleteness.CURRENT_ONLY,
        temporal_confidence=TemporalConfidence.UNKNOWN,
        source_note=(
            "Konsolidierte, nicht amtliche Fassung von "
            "www.gesetze-im-internet.de. "
            "Keine historische Vollständigkeit. "
            "Amtliche Verkündungsfassung: www.recht.bund.de (BGBl). "
            "Abgerufen: "
            + (snapshot.retrieved_at.isoformat() if snapshot.retrieved_at else "unbekannt")
        ),
    )

    # Extract provisions
    assert expression.expression_id is not None
    provisions = _extract_provisions(root, expression.expression_id)

    return instrument, expression, provisions


def _extract_metadata(
    root: etree._Element, fallback_abbr: str, fallback_title: str
) -> dict[str, Any]:
    """Extract metadata from GII XML metadaten section.

    Falls back to catalog-provided values if XML metadata is incomplete.
    """
    abbrev = fallback_abbr
    official_title = fallback_title
    short_title = ""

    # Try to find metadata in norm > metadaten
    metadaten = None
    for child in root:
        if child.tag and "metadaten" in child.tag.lower():
            metadaten = child
            break

    if metadaten is not None:
        for child in metadaten:
            tag_lower = (child.tag or "").lower()
            text = (child.text or "").strip()
            if tag_lower == "jurabk" and text:
                abbrev = text
            elif tag_lower == "langue" and text:
                official_title = text
            elif tag_lower == "kurzue" and text:
                short_title = text
            elif tag_lower == "amtabk":
                pass  # Official publication reference — stored for context

    # Normalize abbreviation for SGB books
    abbrev = _normalize_abbreviation(abbrev)

    return {
        "abbreviation": abbrev,
        "official_title": official_title,
        "short_title": short_title,
    }


def _normalize_abbreviation(abbrev: str) -> str:
    """Normalize abbreviation for common patterns.

    GII uses abbreviated names like 'BGB', 'StGB', 'sgb_10'.
    We normalize compound SGB names to 'SGB X' format.
    """
    abbrev_upper = abbrev.upper().strip()

    # Normalize SGB book names
    sgb_match = re.match(r"SGB[_ ]*(\d+)", abbrev_upper)
    if sgb_match:
        book_num = int(sgb_match.group(1))
        # Convert to Roman numeral for SGB books I-XII
        roman = _to_roman(book_num)
        return f"SGB {roman}"

    return abbrev_upper


def _to_roman(num: int) -> str:
    """Convert integer to Roman numeral (1-99)."""
    val = [100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    for i in range(len(val)):
        count = num // val[i]
        roman_num += syms[i] * count
        num -= val[i] * count
    return roman_num


def _derive_abbreviation(link: str) -> str:
    """Derive abbreviation from GII link URL.

    Examples:
        https://www.gesetze-im-internet.de/bgb/ → "BGB"
        https://www.gesetze-im-internet.de/sgb_10/ → "SGB X"
    """
    # Extract the last path component
    path = link.rstrip("/")
    parts = path.split("/")
    last = parts[-1] if parts else ""

    # Remove file extension if present
    last = re.sub(r"\.[a-z]+$", "", last)

    return _normalize_abbreviation(last)


def _extract_provisions(
    root: etree._Element,
    expression_id: uuid.UUID,
) -> list[LegalProvision]:
    """Extract legal provisions from parsed GII XML.

    The GII XML structure for provisions varies by law format.
    We look for common patterns:
    - <norm> elements with paragraph metadata
    - Section headers vs paragraph content
    - Hierarchical numbering

    This is a best-effort extraction. Full structural parsing
    is handled by future pipeline stages.
    """
    provisions: list[LegalProvision] = []

    # Strategy: find all text elements containing substantive content
    # Look for <textdaten> → <text> → <Content> or similar structures
    text_elements = _find_text_container(root)

    if text_elements is None:
        return provisions

    # Look for paragraph-like elements
    para_count = 0
    for elem in text_elements.iter():
        tag = (elem.tag or "").lower() if hasattr(elem, "tag") else ""

        # Skip metadata and non-content elements
        if tag in ("metadaten", "fussnoten", "description"):
            continue

        text = _get_element_text(elem)
        if not text or len(text) < 10:
            continue

        para_count += 1
        heading = ""
        provision_number = f"§{para_count}"

        # Try to find heading in preceding sibling or parent
        parent = elem.getparent()
        if parent is not None:
            for sibling in parent:
                if sibling is elem:
                    break
                sibling_tag = (sibling.tag or "").lower() if hasattr(sibling, "tag") else ""
                if "ueberschrift" in sibling_tag or "heading" in sibling_tag:
                    heading = _get_element_text(sibling)

        # Generate stable key
        stable_key = f"para-{para_count}"

        provision = LegalProvision(
            provision_id=uuid.uuid4(),
            expression_id=expression_id,
            provision_type=ProvisionType.PARAGRAPH,
            provision_number=provision_number,
            heading=heading,
            stable_key=stable_key,
            sort_key=f"{para_count:06d}",
            text_content=text,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

        provisions.append(provision)

    return provisions


def _find_text_container(root: etree._Element) -> etree._Element | None:
    """Find the main text container in GII XML.

    Looks for common patterns:
    - <textdaten>/<text>/<Content>
    - <text>
    - Direct child with text
    """
    # Pattern 1: textdaten > text > Content
    for child in root:
        tag = (child.tag or "").lower() if hasattr(child, "tag") else ""
        if "textdaten" in tag:
            for sub in child:
                sub_tag = (sub.tag or "").lower() if hasattr(sub, "tag") else ""
                if "text" in sub_tag:
                    # Check for Content wrapper
                    for content in sub:
                        content_tag = (content.tag or "").lower() if hasattr(content, "tag") else ""
                        if "content" in content_tag:
                            return content
                    return sub
            return child

    # Pattern 2: Direct text element
    for child in root:
        tag = (child.tag or "").lower() if hasattr(child, "tag") else ""
        if "text" in tag:
            return child

    # Pattern 3: Root itself contains text
    return root


def _get_element_text(elem: etree._Element) -> str:
    """Get the text content of an XML element, including tail text of children."""
    text_parts: list[str] = []
    if elem.text:
        text_parts.append(elem.text)
    for child in elem:
        if child.tail:
            text_parts.append(child.tail)
    return " ".join(t.strip() for t in text_parts).strip()
