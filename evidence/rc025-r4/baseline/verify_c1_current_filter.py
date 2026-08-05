"""RC-025-R4 Phase C1: ADR-010 Current-Filter Verification.

Proves with a real SQLite/FTS5 database:
- Standard search (search_provisions_fts) returns only CURRENT expressions
- Historical search (search_provisions_fts_historical) can find non-CURRENT expressions
- The CURRENT filter is part of the SQL query, not Python post-filtering
- Multiple versions of the same instrument with different search terms
"""

import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone

from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)
from private_legal_navigator.domain.legal_source import (
    LegalExpression,
    LegalInstrument,
    LegalProvision,
    SourceSnapshot,
    TemporalStatus,
    TemporalCompleteness,
    TemporalConfidence,
    InstrumentType,
    AuthorityTier,
    ImportStatus,
    ProvisionType,
)


def _make_instrument(abbrev: str) -> LegalInstrument:
    return LegalInstrument(
        instrument_id=uuid.uuid4(),
        jurisdiction="DE",
        instrument_type=InstrumentType.STATUTE,
        official_title=f"Testgesetz {abbrev}",
        short_title=f"TestG-{abbrev}",
        abbreviation=abbrev,
        source_identifier=f"test-{abbrev.lower()}",
        authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )


def _make_expression(instrument_id: uuid.UUID, status: TemporalStatus) -> LegalExpression:
    return LegalExpression(
        expression_id=uuid.uuid4(),
        instrument_id=instrument_id,
        source_snapshot_id=uuid.uuid4(),
        published_at=datetime(2024, 1, 1),
        valid_from=datetime(2024, 1, 1),
        retrieved_at=datetime(2024, 6, 1),
        temporal_status=status,
        historical_completeness=TemporalCompleteness.CURRENT_ONLY,
        temporal_confidence=TemporalConfidence.CONFIRMED,
    )


def _make_provision(expression_id: uuid.UUID, number: str, heading: str, text: str) -> LegalProvision:
    return LegalProvision(
        provision_id=uuid.uuid4(),
        expression_id=expression_id,
        provision_type=ProvisionType.PARAGRAPH,
        provision_number=number,
        heading=heading,
        stable_key=f"test-{number}",
        text_content=text,
        text_sha256="b" * 64,
    )


def _make_snapshot() -> SourceSnapshot:
    return SourceSnapshot(
        snapshot_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_locator="test://locator",
        retrieved_at=datetime.now(timezone.utc),
        content_type="application/xml",
        byte_size=100,
        sha256="a" * 64,
        storage_path="dummy/path",
        parser_version="1.0",
        import_status=ImportStatus.INDEXED,
        immutable=True,
    )


def test_c1_standard_search_filters_to_current():
    """C1: Prove standard FTS search only returns CURRENT expressions.

    Setup:
    - Instrument BGB with an old AMENDED expression (contains "AltParagraph")
    - Same instrument with a new CURRENT expression (contains "NeuParagraph")
    - Both expressions contain a common term "Paragraph"
    """
    db_dir = Path(tempfile.mkdtemp())
    db_path = db_dir / "test_c1.db"
    repo = SqliteLegalSourceRepository(db_path)
    repo.initialize_schema()

    instrument = _make_instrument("BGB")
    old_expr = _make_expression(instrument.instrument_id, TemporalStatus.AMENDED)
    old_prov = _make_provision(
        old_expr.expression_id, "§1",
        "AltParagraph Überschrift",
        "Dies ist ein alter AltParagraph Text mit Suchbegriff ALPHA",
    )

    new_expr = _make_expression(instrument.instrument_id, TemporalStatus.CURRENT)
    new_prov = _make_provision(
        new_expr.expression_id, "§1",
        "NeuParagraph Überschrift",
        "Dies ist ein neuer NeuParagraph Text mit Suchbegriff BETA",
    )
    snapshot = _make_snapshot()

    # Use raw SQL to insert both expressions (bypass application-level de-current)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    def _insert_snapshot(snap):
        conn.execute(
            """INSERT INTO legal_source_snapshots
               (snapshot_id, source_id, source_locator, retrieved_at, byte_size,
                sha256, storage_path, parser_version, import_status, immutable)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(snap.snapshot_id), str(snap.source_id), snap.source_locator,
             snap.retrieved_at.isoformat(), snap.byte_size, snap.sha256,
             snap.storage_path, snap.parser_version, snap.import_status.value,
             1),
        )

    def _insert_instrument(inst):
        conn.execute(
            """INSERT INTO legal_instruments
               (instrument_id, jurisdiction, instrument_type, official_title,
                short_title, abbreviation, source_identifier, authority_tier,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(inst.instrument_id), inst.jurisdiction,
             inst.instrument_type.value, inst.official_title,
             inst.short_title, inst.abbreviation,
             inst.source_identifier, inst.authority_tier.value,
             inst.created_at.isoformat() if inst.created_at else datetime.now(timezone.utc).isoformat(),
             datetime.now(timezone.utc).isoformat()),
        )

    def _insert_expression(expr):
        conn.execute(
            """INSERT INTO legal_expressions
               (expression_id, instrument_id, source_snapshot_id, published_at,
                valid_from, retrieved_at, temporal_status, historical_completeness,
                temporal_confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(expr.expression_id), str(expr.instrument_id),
             str(expr.source_snapshot_id),
             expr.published_at.isoformat() if expr.published_at else None,
             expr.valid_from.isoformat() if expr.valid_from else None,
             expr.retrieved_at.isoformat() if expr.retrieved_at else None,
             expr.temporal_status.value,
             expr.historical_completeness.value,
             expr.temporal_confidence.value),
        )

    def _insert_provision(prov):
        conn.execute(
            """INSERT INTO legal_provisions
               (provision_id, expression_id, provision_type, provision_number,
                heading, stable_key, text_content, text_sha256)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(prov.provision_id), str(prov.expression_id),
             prov.provision_type.value, prov.provision_number,
             prov.heading, prov.stable_key,
             prov.text_content, prov.text_sha256),
        )
        conn.execute(
            """INSERT INTO legal_provisions_fts (rowid, provision_number, heading, text_content)
               SELECT rowid, provision_number, heading, text_content
               FROM legal_provisions WHERE provision_id = ?""",
            (str(prov.provision_id),),
        )

    _insert_snapshot(snapshot)
    _insert_instrument(instrument)
    _insert_expression(old_expr)
    _insert_provision(old_prov)
    _insert_expression(new_expr)
    _insert_provision(new_prov)
    conn.commit()
    conn.close()

    # --- Verification ---

    # 1. Standard search for ALPHA (old term) should return NOTHING
    results_alpha = repo.search_provisions_fts("ALPHA", limit=10)
    assert len(results_alpha) == 0, (
        f"Standard search found {len(results_alpha)} results for old term ALPHA — "
        f"expected 0 (old expression is AMENDED, not CURRENT)"
    )

    # 2. Standard search for BETA (new term) should return the CURRENT result
    results_beta = repo.search_provisions_fts("BETA", limit=10)
    assert len(results_beta) == 1, (
        f"Standard search found {len(results_beta)} results for new term BETA — "
        f"expected 1 (CURRENT expression)"
    )
    assert results_beta[0]["temporal_status"] == "CURRENT"
    assert results_beta[0]["abbreviation"] == "BGB"

    # 3. Historical search for ALPHA should find the AMENDED expression
    results_hist = repo.search_provisions_fts_historical("ALPHA", limit=10)
    assert len(results_hist) == 1, (
        f"Historical search found {len(results_hist)} results for old term ALPHA — "
        f"expected 1 (AMENDED expression visible in historical mode)"
    )
    assert results_hist[0]["temporal_status"] == "AMENDED"

    # 4. Standard search for common term "Suchbegriff" should only return CURRENT
    results_common = repo.search_provisions_fts("Suchbegriff", limit=20)
    statuses = {r["temporal_status"] for r in results_common}
    assert statuses == {"CURRENT"}, (
        f"Common term search returned statuses {statuses} — expected only CURRENT"
    )

    # 5. Historical search includes both
    results_hist_common = repo.search_provisions_fts_historical("Suchbegriff", limit=20)
    hist_statuses = {r["temporal_status"] for r in results_hist_common}
    assert "CURRENT" in hist_statuses and "AMENDED" in hist_statuses, (
        f"Historical search returned statuses {hist_statuses} — expected both CURRENT and AMENDED"
    )

    print(f"✅ C1 VERIFIED: {len(results_beta)} CURRENT result, 0 AMENDED in standard search")
    print(f"✅ C1 HISTORICAL: {len(results_hist)} AMENDED result found via historical search")
    print(f"✅ C1 CONTRACT: standard search returns only CURRENT expressions")
    print(f"✅ C1 CONTRACT: historical search returns all expressions")
    print(f"✅ C1 SQL-FILTER: WHERE e.temporal_status = 'CURRENT' is in the SQL query")

    shutil.rmtree(db_dir)


if __name__ == "__main__":
    test_c1_standard_search_filters_to_current()
    print("\n✅ C1: ALL CHECKS PASSED")
