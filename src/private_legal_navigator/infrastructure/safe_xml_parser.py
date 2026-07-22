"""Secure XML parser for legal source documents (M7-A).

Uses lxml with all entity resolution disabled to prevent:
- XXE (XML External Entity) attacks
- Billion laughs / recursive entity expansion
- External DTD loading
- Remote entity fetching

Requirements:
- lxml >= 6.1.0 (for iterparse resolve_entities fix CVE-2026-41066)
- resolve_entities=False for ALL parsers
- no_network=True (blocks remote DTD/entity fetching)
- huge_tree=False (enforces libxml2 size limits)
"""

import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from lxml import etree

logger = logging.getLogger("private_legal_navigator.xml_parser")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

MAX_XML_BYTES: int = 50 * 1024 * 1024  # 50 MB XML size limit before parsing


class XmlSecurityError(Exception):
    """Raised when XML fails security validation."""


class XmlTooLargeError(XmlSecurityError):
    """XML content exceeds the maximum allowed size."""


class XmlParseError(XmlSecurityError):
    """XML parsing failed."""


# ──────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────


def create_safe_parser() -> etree.XMLParser:
    """Create a security-hardened XML parser.

    ALL entity resolution is disabled. No network access.
    No DTD loading. Size limits enforced by libxml2.
    """
    return etree.XMLParser(
        resolve_entities=False,  # CRITICAL: Block ALL entity expansion
        no_network=True,  # Block external DTD/entity network access
        load_dtd=False,  # Do not load DTD
        dtd_validation=False,  # Do not validate against DTD
        huge_tree=False,  # Enforce libxml2 size/depth limits
        remove_pis=True,  # Strip processing instructions
        remove_blank_text=True,  # Reduce memory pressure
    )


def parse_xml_bytes(xml_bytes: bytes) -> etree._ElementTree:
    """Parse XML bytes with all security guardrails applied.

    Raises XmlTooLargeError if content exceeds MAX_XML_BYTES.
    Raises XmlParseError if parsing fails.
    """
    if len(xml_bytes) > MAX_XML_BYTES:
        raise XmlTooLargeError(f"XML content size {len(xml_bytes)} exceeds limit {MAX_XML_BYTES}")

    try:
        parser = create_safe_parser()
        tree = etree.fromstring(xml_bytes, parser)
        # Wrap in ElementTree for consistent API
        return etree.ElementTree(tree)
    except etree.XMLSyntaxError as exc:
        raise XmlParseError(f"XML parse error: {exc}") from exc


def parse_xml_file(file_path: Path) -> etree._ElementTree:
    """Parse an XML file with all security guardrails applied."""
    content = file_path.read_bytes()
    return parse_xml_bytes(content)


def iterparse_large_xml(
    source: BytesIO,
    tag_filter: str | None = None,
) -> Any:
    """Memory-efficient streaming parse of large legal XML.

    Uses iterparse with elem.clear() to free memory after each element.
    Tag filter reduces memory pressure (e.g., '{*}norm' for legal norms).

    WARNING: resolve_entities=False is non-negotiable.
    """
    if isinstance(source, bytes):  # type: ignore[unreachable]
        raise TypeError("iterparse_large_xml requires a file-like object, not bytes")

    events = ("end",)
    kwargs: dict[str, Any] = {
        "events": events,
        "resolve_entities": False,
        "no_network": True,
        "huge_tree": False,
    }
    if tag_filter:
        kwargs["tag"] = tag_filter

    return etree.iterparse(source, **kwargs)


def validate_xml_magic_bytes(content: bytes) -> bool:
    """Check if content starts with valid XML declaration or root element.

    Returns True if content looks like XML (starts with '<?xml' or '<').
    """
    if len(content) < 5:
        return False
    # Check for BOM + XML declaration or direct '<'
    if content.startswith(b"\xef\xbb\xbf"):
        return content[3:8] == b"<?xml"
    return content[:5] == b"<?xml" or content[:1] == b"<"
