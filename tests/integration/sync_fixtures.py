"""Shared test data and helpers for M7-B sync integration tests.

Provides synthetic XML data for catalog and law downloads.
"""

import io
import zipfile


def _wrap_in_zip(xml_bytes: bytes, filename: str = "gesetz.xml") -> bytes:
    """Wrap XML bytes in a minimal ZIP archive (as GII serves content)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, xml_bytes)
    return buf.getvalue()


# ── Synthetic GII Catalog XML ────────────────────
# A minimal catalog with 3 instruments for testing.

SYNTH_CATALOG_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<gii-toc stand="2026-07-25">\n'
    b"  <item>\n"
    b"    <link>https://www.gesetze-im-internet.de/bgb/xml.zip</link>\n"
    b"    <title>B\xc3\xbcrgerliches Gesetzbuch</title>\n"
    b"    <type>G</type>\n"
    b"  </item>\n"
    b"  <item>\n"
    b"    <link>https://www.gesetze-im-internet.de/stgb/xml.zip</link>\n"
    b"    <title>Strafgesetzbuch</title>\n"
    b"    <type>G</type>\n"
    b"  </item>\n"
    b"  <item>\n"
    b"    <link>https://www.gesetze-im-internet.de/vwgo/xml.zip</link>\n"
    b"    <title>Verwaltungsgerichtsordnung</title>\n"
    b"    <type>G</type>\n"
    b"  </item>\n"
    b"</gii-toc>\n"
)

# ── Synthetic Law XML (minimal valid GII norm format) ─

SYNTH_BGB_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b"<norm>\n"
    b"  <metadaten>\n"
    b"    <jurabk>BGB</jurabk>\n"
    b"    <langue>B\xc3\xbcrgerliches Gesetzbuch</langue>\n"
    b"    <kurzue>BGB</kurzue>\n"
    b"  </metadaten>\n"
    b"  <textdaten>\n"
    b"    <text>\n"
    b"      <Content>\n"
    b"        <P>\xc2\xa7 1 Beginn der Rechtsf\xc3\xa4higkeit."
    b" Die Rechtsf\xc3\xa4higkeit des Menschen beginnt"
    b" mit der Vollendung der Geburt.</P>\n"
    b"      </Content>\n"
    b"    </text>\n"
    b"  </textdaten>\n"
    b"</norm>\n"
)

SYNTH_STGB_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b"<norm>\n"
    b"  <metadaten>\n"
    b"    <jurabk>StGB</jurabk>\n"
    b"    <langue>Strafgesetzbuch</langue>\n"
    b"    <kurzue>StGB</kurzue>\n"
    b"  </metadaten>\n"
    b"  <textdaten>\n"
    b"    <text>\n"
    b"      <Content>\n"
    b"        <P>\xc2\xa7 1 Keine Strafe ohne Gesetz."
    b" Eine Tat kann nur bestraft werden,"
    b" wenn die Strafbarkeit gesetzlich bestimmt war,"
    b" bevor die Tat begangen wurde.</P>\n"
    b"      </Content>\n"
    b"    </text>\n"
    b"  </textdaten>\n"
    b"</norm>\n"
)

SYNTH_VWGO_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b"<norm>\n"
    b"  <metadaten>\n"
    b"    <jurabk>VwGO</jurabk>\n"
    b"    <langue>Verwaltungsgerichtsordnung</langue>\n"
    b"    <kurzue>VwGO</kurzue>\n"
    b"  </metadaten>\n"
    b"  <textdaten>\n"
    b"    <text>\n"
    b"      <Content>\n"
    b"        <P>\xc2\xa7 40 Zul\xc3\xa4ssigkeit des Verwaltungsrechtswegs."
    b" Der Verwaltungsrechtsweg ist in allen"
    b" \xc3\xb6ffentlich-rechtlichen Streitigkeiten"
    b" nichtverfassungsrechtlicher Art gegeben.</P>\n"
    b"      </Content>\n"
    b"    </text>\n"
    b"  </textdaten>\n"
    b"</norm>\n"
)

# Map abbreviated law key → synthetic XML bytes
SYNTH_LAW_XML_MAP: dict[str, bytes] = {
    "BGB": SYNTH_BGB_XML,
    "StGB": SYNTH_STGB_XML,
    "VwGO": SYNTH_VWGO_XML,
}

# ZIP-wrapped versions (for catalog URLs ending in .zip)
SYNTH_BGB_ZIP = _wrap_in_zip(SYNTH_BGB_XML, "bgb.xml")
SYNTH_STGB_ZIP = _wrap_in_zip(SYNTH_STGB_XML, "stgb.xml")
SYNTH_VWGO_ZIP = _wrap_in_zip(SYNTH_VWGO_XML, "vwgo.xml")

# Map source_identifier → synthetic XML bytes (for download_with_headers)
SYNTH_LAW_URL_TO_XML: dict[str, bytes] = {
    "https://www.gesetze-im-internet.de/bgb/": SYNTH_BGB_XML,
    "https://www.gesetze-im-internet.de/stgb/": SYNTH_STGB_XML,
    "https://www.gesetze-im-internet.de/vwgo/": SYNTH_VWGO_XML,
}

# Map full download URL → ZIP-wrapped synthetic XML (for adapter downloads)
SYNTH_LAW_DOWNLOAD_URL_TO_XML: dict[str, bytes] = {
    "https://www.gesetze-im-internet.de/bgb/xml.zip": SYNTH_BGB_ZIP,
    "https://www.gesetze-im-internet.de/stgb/xml.zip": SYNTH_STGB_ZIP,
    "https://www.gesetze-im-internet.de/vwgo/xml.zip": SYNTH_VWGO_ZIP,
}
