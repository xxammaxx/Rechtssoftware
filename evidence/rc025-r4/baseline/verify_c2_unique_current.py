"""RC-025-R4 Phase C2: Database-level Unique-Current Invariant Verification.

Proves that the database enforces:
- At most one CURRENT expression per instrument
- The constraint is at the SQL level (partial unique index)
- Application-level pre-check alone is not sufficient
"""

import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone

from private_legal_navigator.infrastructure.database import initialize_schema


def test_c2_db_enforces_one_current():
    """C2: Prove DB-level enforcement of at most one CURRENT per instrument.

    1. Insert first CURRENT expression → succeeds
    2. Attempt second CURRENT expression for same instrument via raw SQL → must fail
    3. Expected SQLite error: UNIQUE constraint violation on the partial index
    """
    db_dir = Path(tempfile.mkdtemp())
    db_path = db_dir / "test_c2.db"

    # Initialize schema (should create the partial unique index)
    initialize_schema(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Setup: source, snapshot, instrument
    snap_id = str(uuid.uuid4())
    src_id = str(uuid.uuid4())
    inst_id = str(uuid.uuid4())
    expr1_id = str(uuid.uuid4())
    expr2_id = str(uuid.uuid4())

    conn.execute(
        """INSERT INTO legal_sources
           (source_id, source_key, display_name, authority_tier, jurisdiction, enabled, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (src_id, 'test', 'Test', 'UNKNOWN', 'DE', 1,
         datetime.now(timezone.utc).isoformat()))
    conn.execute(
        """INSERT INTO legal_source_snapshots
           (snapshot_id, source_id, source_locator, retrieved_at, content_type,
            byte_size, sha256, storage_path, parser_version, import_status, immutable)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (snap_id, src_id, 'test://', datetime.now(timezone.utc).isoformat(),
         'text/xml', 100, 'a' * 64, '/tmp', '1.0', 'INDEXED', 1))
    conn.execute(
        """INSERT INTO legal_instruments
           (instrument_id, jurisdiction, instrument_type, official_title,
            short_title, abbreviation, source_identifier, authority_tier,
            created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (inst_id, 'DE', 'STATUTE', 'Test', 'Test', 'BGB', 'test-bgb',
         'CONSOLIDATED_NON_OFFICIAL',
         datetime.now(timezone.utc).isoformat(),
         datetime.now(timezone.utc).isoformat()))

    # 1. Insert first CURRENT expression — should succeed
    conn.execute(
        """INSERT INTO legal_expressions
           (expression_id, instrument_id, source_snapshot_id, published_at,
            valid_from, retrieved_at, temporal_status, historical_completeness,
            temporal_confidence)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (expr1_id, inst_id, snap_id, '2024-01-01', '2024-01-01', '2024-06-01',
         'CURRENT', 'CURRENT_ONLY', 'CONFIRMED'))
    conn.commit()

    # Verify first insert
    count = conn.execute(
        "SELECT COUNT(*) FROM legal_expressions WHERE instrument_id = ? AND temporal_status = 'CURRENT'",
        (inst_id,)
    ).fetchone()[0]
    assert count == 1, f"Expected 1 CURRENT expression, got {count}"

    # 2. Attempt second CURRENT expression for same instrument — must fail
    constraint_violated = False
    try:
        conn.execute(
            """INSERT INTO legal_expressions
               (expression_id, instrument_id, source_snapshot_id, published_at,
                valid_from, retrieved_at, temporal_status, historical_completeness,
                temporal_confidence)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (expr2_id, inst_id, snap_id, '2024-06-01', '2024-06-01', '2024-06-01',
             'CURRENT', 'CURRENT_ONLY', 'CONFIRMED'))
        conn.commit()
        print("ERROR: Second CURRENT expression was allowed — invariant NOT enforced!")
        assert False, "DB failed to reject duplicate CURRENT expression"
    except sqlite3.IntegrityError as e:
        constraint_violated = True
        error_msg = str(e)
        print(f"✅ DB REJECTED second CURRENT: {error_msg}")
        assert "UNIQUE constraint failed" in error_msg or "idx_le_one_current" in error_msg, (
            f"Expected UNIQUE constraint error, got: {error_msg}")

    assert constraint_violated, "Expected IntegrityError was not raised"

    # 3. Verify only one CURRENT remains
    conn.rollback()
    count_after = conn.execute(
        "SELECT COUNT(*) FROM legal_expressions WHERE instrument_id = ? AND temporal_status = 'CURRENT'",
        (inst_id,)
    ).fetchone()[0]
    assert count_after == 1, f"Expected 1 CURRENT after failed insert, got {count_after}"

    # 4. Verify the partial unique index exists
    index_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_le_one_current'"
    ).fetchone()
    assert index_exists is not None, "Partial unique index idx_le_one_current not found"

    # 5. Different instrument can have its own CURRENT expression
    inst2_id = str(uuid.uuid4())
    expr3_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO legal_instruments
           (instrument_id, jurisdiction, instrument_type, official_title,
            short_title, abbreviation, source_identifier, authority_tier,
            created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (inst2_id, 'DE', 'STATUTE', 'Test2', 'Test2', 'ZPO', 'test-zpo',
         'CONSOLIDATED_NON_OFFICIAL',
         datetime.now(timezone.utc).isoformat(),
         datetime.now(timezone.utc).isoformat()))
    conn.execute(
        """INSERT INTO legal_expressions
           (expression_id, instrument_id, source_snapshot_id, published_at,
            valid_from, retrieved_at, temporal_status, historical_completeness,
            temporal_confidence)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (expr3_id, inst2_id, snap_id, '2024-01-01', '2024-01-01', '2024-06-01',
         'CURRENT', 'CURRENT_ONLY', 'CONFIRMED'))
    conn.commit()  # Should succeed — different instrument

    print(f"✅ C2 ENFORCED: DB rejects duplicate CURRENT per instrument")
    print(f"✅ C2 INDEX: idx_le_one_current partial unique index exists")
    print(f"✅ C2 SCOPE: Different instruments can each have their own CURRENT")

    conn.close()
    shutil.rmtree(db_dir)


if __name__ == "__main__":
    test_c2_db_enforces_one_current()
    print("\n✅ C2: ALL CHECKS PASSED")
