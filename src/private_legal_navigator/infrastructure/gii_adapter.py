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
from urllib.parse import urlparse, urlunparse

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
            link = ""
            title = ""
            item_type = ""
            # GII catalog uses child elements, not attributes
            for child in item_elem:
                tag = child.tag.lower()
                text = (child.text or "").strip()
                if tag == "link":
                    link = text
                elif tag == "title":
                    title = text
                elif tag == "type":
                    item_type = text

            # Derive abbreviation from link (directory name, not file extension)
            abbreviation = ""
            source_identifier = ""
            if link:
                abbreviation = _derive_abbreviation(link)
                source_identifier = _derive_source_identifier(link)

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
            key: Law abbreviation (e.g., 'SGB X', 'sgb_10') or source identifier.

        Searches in priority order:
        1. Exact abbreviation match (case-insensitive), preferring full instrument entries
        2. Normalized URL directory match (key appears as directory in link)
        3. Broad link substring match (last resort, only for non-generic keys)
        """
        catalog = self.fetch_catalog()
        # Sort catalog: prefer entries without chapter suffix (full instruments first)
        catalog.sort(key=_catalog_sort_key)
        key_lower = key.lower().strip()

        # Normalize key: convert "SGB X" → "sgb_10" for URL matching
        key_normalized = _normalize_key_for_url_match(key_lower)

        # Priority 1: Exact abbreviation match
        for item in catalog:
            if item.abbreviation.lower() == key_lower:
                return item

        # Priority 2: URL directory match (key appears as directory in link)
        for item in catalog:
            link_lower = item.link.lower()
            # Match when key appears as a path directory component
            if f"/{key_normalized}/" in link_lower or link_lower.endswith(f"/{key_normalized}"):
                return item

        # Priority 3: Broad substring match (only for non-generic keys like "xml")
        if key_lower not in ("xml", "html", "zip", "pdf", "index"):
            for item in catalog:
                if key_lower in item.link.lower():
                    return item

        return None

    def find_instruments_by_abbreviation(self, abbrev: str) -> list[GiiCatalogItem]:
        """Find all catalog items matching an abbreviation (for grouping chapters).

        Returns all items that share the same derived abbreviation, enabling
        multi-file instruments to be grouped.
        """
        catalog = self.fetch_catalog()
        abbrev_lower = abbrev.lower().strip()
        results: list[GiiCatalogItem] = []
        for item in catalog:
            if item.abbreviation.lower() == abbrev_lower:
                results.append(item)
        # Sort: prefer items without chapter suffix (the main instrument)
        results.sort(key=lambda x: (0 if "_kap" not in x.link.lower() else 1, x.link))
        return results

    # ── Instrument Sync ──────────────────────────

    def sync_instrument(self, item: GiiCatalogItem) -> GiiParsedInstrument:
        """Download, snapshot, and parse a single GII instrument.

        1. Download the XML
        2. Compute SHA-256
        3. Save snapshot to disk
        4. Create SourceSnapshot entity
        5. Parse XML into LegalInstrument + LegalExpression + provisions
        """
        # 1. Download — upgrade http→https (GII catalog uses http links but site supports https)
        law_url = item.link
        if not law_url.startswith("http"):
            law_url = (
                GII_BASE_URL + law_url if law_url.startswith("/") else GII_BASE_URL + "/" + law_url
            )
        if law_url.startswith("http://"):
            law_url = law_url.replace("http://", "https://", 1)

        raw_bytes = self._client.download(law_url)

        # 2. Extract XML from ZIP if needed (GII serves ZIP archives)
        if law_url.endswith(".zip") or raw_bytes[:2] == b"PK":
            xml_bytes = _extract_xml_from_zip_bytes(raw_bytes, law_url)
        else:
            xml_bytes = raw_bytes

        # 3. Validate magic bytes before processing
        from private_legal_navigator.infrastructure.safe_xml_parser import validate_xml_magic_bytes

        if not validate_xml_magic_bytes(xml_bytes):
            raise ValueError(f"Downloaded content from {law_url} does not appear to be XML")

        # 4. Write to content-addressed path (hash is computed during write)
        from private_legal_navigator.infrastructure.safe_source_client import (
            _write_content_addressed,
        )

        snapshot_path, sha256 = _write_content_addressed(xml_bytes, self._snapshot_dir)

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
            source_identifier=item.source_identifier,
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
    source_identifier: str = "",
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

    # Build instrument — prefer canonical source_identifier over download URL
    canonical_id = source_identifier or snapshot.source_locator

    instrument = LegalInstrument(
        instrument_id=uuid.uuid4(),
        jurisdiction=GII_JURISDICTION,
        instrument_type=InstrumentType.STATUTE,
        official_title=metadata["official_title"],
        short_title=metadata["short_title"],
        abbreviation=metadata["abbreviation"],
        source_identifier=canonical_id,
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


def _normalize_key_for_url_match(key: str) -> str:
    """Normalize a user-provided key for URL directory matching.

    Converts display abbreviations to URL directory format:
      "SGB X"  → "sgb_10"
      "sgb_10" → "sgb_10"
      "bgb"    → "bgb"
    """
    key_upper = key.upper().strip()

    # Reverse SGB display name → URL directory
    sgb_display = re.match(r"SGB\s+([IVXLCDM]+)", key_upper)
    if sgb_display:
        roman = sgb_display.group(1)
        num = _from_roman(roman)
        if num > 0:
            return f"sgb_{num}"

    return key.lower()


def _from_roman(roman: str) -> int:
    """Convert Roman numeral to integer. Returns 0 on invalid input."""
    roman_map = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for char in reversed(roman.upper()):
        val = roman_map.get(char, 0)
        if val == 0:
            return 0
        if val >= prev:
            result += val
        else:
            result -= val
        prev = val
    return result


def _normalize_abbreviation(abbrev: str) -> str:
    """Normalize abbreviation for common patterns.

    GII uses abbreviated names like 'BGB', 'StGB', 'sgb_10'.
    We normalize compound SGB names to 'SGB X' format.

    File extensions and generic names are rejected to UNKNOWN.
    """
    if not abbrev or not abbrev.strip():
        return "UNKNOWN"

    abbrev_upper = abbrev.upper().strip()

    # Reject file extensions used as abbreviations (e.g., "XML", "HTML", "PDF")
    generic_file_abbrevs = {"XML", "HTML", "HTM", "PDF", "ZIP", "TXT", "JSON", "CSV"}
    if abbrev_upper in generic_file_abbrevs:
        return "UNKNOWN"

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


def _catalog_sort_key(item: Any) -> tuple[int, str]:
    """Sort key for catalog items: prefer full instruments over chapter entries.

    Full instruments (no chapter marker) get priority 0.
    Chapter entries (with _kap, _anhang etc.) get priority 1.
    """
    link_lower = item.link.lower()
    is_chapter = bool(re.search(r"_(kap|anhang|teil|abschnitt|buch|art)", link_lower))
    return (1 if is_chapter else 0, item.link)


def _derive_source_identifier(link: str) -> str:
    """Derive the canonical source identifier (parent instrument URL) from a download link."""
    parsed = urlparse(link)
    path = parsed.path.rstrip("/")
    path_parts = [p for p in path.split("/") if p]

    if not path_parts:
        return link

    # Filter out file-like components (containing '.')
    dir_parts = [p for p in path_parts if "." not in p]

    if not dir_parts:
        return link

    # For the last directory, strip chapter suffixes
    last_dir = dir_parts[-1]
    last_dir = re.sub(r"_(kap|anhang|teil|abschnitt|buch|art).*", "", last_dir, flags=re.IGNORECASE)

    # Reconstruct path
    canonical_path = "/".join(dir_parts[:-1] + [last_dir]) + "/"

    return urlunparse((parsed.scheme, parsed.netloc, canonical_path, "", "", ""))


def _derive_abbreviation(link: str) -> str:
    """Derive abbreviation from GII link URL.

    The GII catalog serves law documents via directory-based URLs:
      https://.../bgb/          → "BGB"
      https://.../sgb_10/xml.zip → "SGB X"  (directory is sgb_10, file is xml.zip)
      https://.../bgb/index.html → "BGB"

    Key principle: The meaningful law identifier is the last directory name.
    File-like components (containing '.') are download artifacts, not law identifiers.

    Chapter entries (e.g., sgb_10_kap1_2/xml.zip) are stripped to their parent law.
    """
    path = link.rstrip("/")
    parts = path.split("/")

    # Find the last meaningful directory component
    # Skip file-like components (containing '.') — these are download artifacts
    # like xml.zip, index.html, etc.
    law_dir = ""
    for part in reversed(parts):
        if not part:
            continue
        if "." in part:
            # This is a file-like component (xml.zip, index.html) — skip it
            continue
        law_dir = part
        break

    if not law_dir and parts:
        # All parts are file-like — fallback to last part, strip extension
        last = parts[-1]
        law_dir = re.sub(r"\.[a-z]+$", "", last)

    if not law_dir:
        return "UNKNOWN"

    # Strip chapter/part suffixes to derive parent law abbreviation
    # Examples: sgb_10_kap1_2 → sgb_10, bgb_anhang_1 → bgb
    law_dir = re.sub(r"_(kap|anhang|teil|abschnitt|buch|art).*", "", law_dir, flags=re.IGNORECASE)

    return _normalize_abbreviation(law_dir)


def _extract_provisions(
    root: etree._Element,
    expression_id: uuid.UUID,
) -> list[LegalProvision]:
    """Extract legal provisions from parsed GII XML.

    GII XML uses two main structures:

    1. Aggregated format (<dokumente> with <norm> children):
       <dokumente>
         <norm>
           <metadaten><enbez>§ 48</enbez><titel>Heading</titel>...</metadaten>
           <textdaten><text><Content><P>Text...</P></Content></text></textdaten>
         </norm>
       </dokumente>

    2. Single-norm format (root is <norm>):
       <norm>
         <metadaten>...</metadaten>
         <textdaten>...</textdaten>
       </norm>

    Each <norm> represents a single paragraph/section.
    """
    provisions: list[LegalProvision] = []

    # Determine which elements to process
    norm_elements: list[etree._Element] = []
    root_tag = (root.tag or "").lower() if hasattr(root, "tag") else ""

    if "dokumente" in root_tag:
        # Aggregated format: each child <norm> is a paragraph
        for child in root:
            child_tag = (child.tag or "").lower() if hasattr(child, "tag") else ""
            if child_tag == "norm":
                norm_elements.append(child)
    elif root_tag == "norm":
        # Single-norm format
        norm_elements.append(root)
    else:
        # Fallback: use the old text container approach for unknown formats
        return _extract_provisions_fallback(root, expression_id)

    # Process each norm element
    for norm_idx, norm_elem in enumerate(norm_elements):
        metadata = _extract_norm_metadata(norm_elem)
        text_content = _extract_norm_text(norm_elem)

        if (not text_content or len(text_content.strip()) < 5) and not metadata.get("number"):
            # Empty norms without explicit numbering (e.g., TOC entries) are skipped
            continue

        # Determine provision number
        prov_number = metadata.get("number") or f"§{norm_idx + 1}"
        heading = metadata.get("heading", "")

        # Generate stable key from provision number
        stable_key = _provision_stable_key(prov_number)

        # Sort key tries to preserve document order
        sort_key = f"{norm_idx:06d}"

        provision = LegalProvision(
            provision_id=uuid.uuid4(),
            expression_id=expression_id,
            provision_type=ProvisionType.PARAGRAPH,
            provision_number=prov_number,
            heading=heading,
            stable_key=stable_key,
            sort_key=sort_key,
            text_content=text_content.strip(),
            text_sha256=hashlib.sha256(text_content.encode("utf-8")).hexdigest(),
        )

        provisions.append(provision)

    return provisions


def _provision_stable_key(provision_number: str) -> str:
    """Generate a stable key from a provision number.

    § 48 → norm-48
    § 48a → norm-48a
    Art. 1 → art-1
    """
    cleaned = provision_number.strip()
    # Remove § symbol
    cleaned = cleaned.replace("§", "").strip()
    # Normalize spaces
    cleaned = re.sub(r"\s+", "-", cleaned)
    return f"norm-{cleaned}" if cleaned else "norm-unknown"


def _extract_norm_metadata(norm_elem: etree._Element) -> dict[str, str]:
    """Extract metadata from a <norm> element's <metadaten> section."""
    result: dict[str, str] = {}

    for child in norm_elem:
        tag = (child.tag or "").lower() if hasattr(child, "tag") else ""
        if tag != "metadaten":
            continue
        for sub in child:
            sub_tag = (sub.tag or "").lower() if hasattr(sub, "tag") else ""
            text = (sub.text or "").strip()
            if sub_tag == "enbez":
                result["number"] = text
            elif sub_tag == "titel":
                result["heading"] = text
            elif sub_tag == "jurabk":
                result["abbreviation"] = text
            elif sub_tag == "langue":
                result["long_title"] = text
            elif sub_tag == "kurzue":
                result["short_title"] = text
        break  # Only process first metadaten section

    return result


def _extract_norm_text(norm_elem: etree._Element) -> str:
    """Extract the full text content from a <norm> element's <textdaten> section."""
    text_parts: list[str] = []

    for child in norm_elem:
        tag = (child.tag or "").lower() if hasattr(child, "tag") else ""
        if tag != "textdaten":
            continue
        # Collect all text from textdaten, including nested elements
        _collect_text_recursive(child, text_parts)
        break  # Only first textdaten section

    return " ".join(text_parts).strip()


def _collect_text_recursive(elem: etree._Element, parts: list[str]) -> None:
    """Recursively collect text content from an element tree."""
    if elem.text and elem.text.strip():
        parts.append(elem.text.strip())
    for child in elem:
        if hasattr(child, "tag"):
            _collect_text_recursive(child, parts)
        if child.tail and child.tail.strip():
            parts.append(child.tail.strip())


def _extract_provisions_fallback(
    root: etree._Element,
    expression_id: uuid.UUID,
) -> list[LegalProvision]:
    """Fallback provision extraction for unknown XML formats (legacy behavior)."""
    provisions: list[LegalProvision] = []
    text_elements = _find_text_container(root)
    if text_elements is None:
        return provisions

    para_count = 0
    for elem in text_elements.iter():
        tag = (elem.tag or "").lower() if hasattr(elem, "tag") else ""
        if tag in ("metadaten", "fussnoten", "description"):
            continue
        text = _get_element_text(elem)
        if not text or len(text) < 10:
            continue
        para_count += 1
        heading = ""
        provision_number = f"§{para_count}"
        parent = elem.getparent()
        if parent is not None:
            for sibling in parent:
                if sibling is elem:
                    break
                sibling_tag = (sibling.tag or "").lower() if hasattr(sibling, "tag") else ""
                if "ueberschrift" in sibling_tag or "heading" in sibling_tag:
                    heading = _get_element_text(sibling)
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


def _extract_xml_from_zip_bytes(zip_bytes: bytes, source_url: str) -> bytes:
    """Extract the first XML file from a ZIP archive with path traversal protection.

    SEC-007: Path traversal (../) is rejected.
    SEC-008: Absolute paths are rejected.
    SEC-009: Symlinks are not possible in basic ZIP.
    SEC-010: Max 50 files per archive enforced.
    SEC-011: Max 100 MB extracted total size enforced.
    """
    import zipfile
    from io import BytesIO

    max_files = 50
    max_total_size = 100 * 1024 * 1024  # 100 MB

    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        if len(names) > max_files:
            raise ValueError(
                f"ZIP archive contains {len(names)} files, exceeding limit of {max_files}"
            )

        # Find the first XML file
        xml_name = None
        for name in names:
            # SEC-007: Reject path traversal
            if ".." in name:
                raise ValueError(f"ZIP entry contains path traversal: {name}")
            # SEC-008: Reject absolute paths
            if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
                raise ValueError(f"ZIP entry has absolute path: {name}")
            if name.lower().endswith(".xml"):
                xml_name = name
                break

        if xml_name is None:
            raise ValueError(
                f"No XML file found in ZIP archive from {source_url}. Contents: {names[:10]}"
            )

        # Check total size
        total_size = sum(info.file_size for info in zf.infolist())
        if total_size > max_total_size:
            raise ValueError(f"ZIP total size {total_size} exceeds limit of {max_total_size}")

        return zf.read(xml_name)
