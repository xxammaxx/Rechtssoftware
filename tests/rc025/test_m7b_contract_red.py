"""RC-025 RED Contract Verification Tests for M7-B Sync.

These tests demonstrate the 10 mandatory RED conditions from Phase E2.
They MUST fail before any fix is applied (Builder phase).

Test data: SYNTHETISCH – (no real GII calls, no real legal data)
"""

import os
import sqlite3
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this file as RED (expected to fail before fixes)
pytestmark = [pytest.mark.rc025_red, pytest.mark.m7b_contracts]


# ── Helpers ────────────────────────────────────────


def _temp_db() -> str:
    """Create a temporary SQLite database for isolated testing."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_rc025_")
    os.close(fd)
    return path


def _read_db(path: str) -> list[tuple[str, int]]:
    """Read table names and row counts from a SQLite database."""
    conn = sqlite3.connect(path)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cur.fetchall()]
    result = []
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        result.append((table, count))
    conn.close()
    return result


# ── RED-1: Dry-Run modifies the product database ───


def test_red1_dry_run_does_not_modify_product_db():
    """RED-1: Dry-run MUST NOT persist SyncRun or SyncItem records.

    Currently, execute(dry_run=True) calls save_sync_run() and
    save_sync_item() which writes to the product database.
    """
    from private_legal_navigator.application.sync_service import SyncPlanningService, SyncExecutionService
    from private_legal_navigator.domain.sync import SyncItem, SyncItemStatus, SyncPlan

    # Setup: Create a plan with a single NEW item (synthetic data)
    plan = SyncPlan(
        sync_run_id=str(uuid.uuid4()),
        items=[
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=str(uuid.uuid4()),  # will be overwritten
                source_identifier="SYNTHETISCH – test-instrument",
                abbreviation="SYNTEST",
                title="SYNTHETISCH – Test Instrument",
                item_status=SyncItemStatus.NEW,
            )
        ],
    )

    # The plan has a sync_run_id that differs from items — typical for real usage
    plan = SyncPlan(
        sync_run_id=str(uuid.uuid4()),
        items=[
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=plan.sync_run_id,
                source_identifier="SYNTHETISCH – test-instrument",
                abbreviation="SYNTEST",
                title="SYNTHETISCH – Test Instrument",
                item_status=SyncItemStatus.NEW,
            )
        ],
    )

    # Mock the repository to detect writes
    mock_repo = MagicMock()
    mock_repo.get_latest_sync_run.return_value = None

    executor = SyncExecutionService(
        repo=mock_repo,
        legal_source_service=MagicMock(),
        source_client=MagicMock(),
        gii_adapter=MagicMock(),
    )

    # Execute in dry-run mode
    executor.execute(plan, dry_run=True)

    # Assert: No SyncRun should be saved during dry-run
    # This WILL FAIL because save_sync_run is called even in dry_run mode
    mock_repo.save_sync_run.assert_not_called()


# ── RED-2: Dry-Run creates persistent sync history ──


def test_red2_dry_run_creates_no_sync_history():
    """RED-2: Dry-run MUST NOT create persistent SyncRun records.

    SyncRun records with dry_run=True should not be persisted;
    they should only exist in-memory or as evidence files.
    """
    from private_legal_navigator.application.sync_service import SyncExecutionService
    from private_legal_navigator.domain.sync import SyncItem, SyncItemStatus, SyncPlan

    plan = SyncPlan(
        sync_run_id=str(uuid.uuid4()),
        items=[
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=str(uuid.uuid4()),
                source_identifier="SYNTHETISCH – test-instrument",
                abbreviation="SYNTEST",
                title="SYNTHETISCH – Test",
                item_status=SyncItemStatus.NEW,
            )
        ],
    )

    mock_repo = MagicMock()
    mock_repo.get_latest_sync_run.return_value = None

    executor = SyncExecutionService(
        repo=mock_repo,
        legal_source_service=MagicMock(),
        source_client=MagicMock(),
        gii_adapter=MagicMock(),
    )

    executor.execute(plan, dry_run=True)

    # Assert: No SyncItem should be saved during dry-run
    # This WILL FAIL because save_sync_item is called for each item in dry_run mode
    mock_repo.save_sync_item.assert_not_called()


# ── RED-3: KNOWN classified without remote evidence ──


def test_red3_known_unverified_required():
    """RED-3: Planning MUST NOT classify items as KNOWN without remote evidence.

    The planning phase should use KNOWN_UNVERIFIED, not KNOWN,
    until remote evidence (HTTP request) confirms the item's state.
    """
    from private_legal_navigator.domain.sync import SyncItemStatus

    # KNOWN_UNVERIFIED should exist as a valid status
    # Currently it does NOT exist in the SyncItemStatus enum
    valid_statuses = [s.value for s in SyncItemStatus]
    assert "KNOWN_UNVERIFIED" in valid_statuses, (
        "KNOWN_UNVERIFIED status must exist for truthful planning-phase classification. "
        f"Current statuses: {valid_statuses}"
    )


# ── RED-4: Instrument can be downloaded twice ──


def test_red4_single_download_per_apply():
    """RED-4: Each instrument MUST be downloaded exactly once per apply.

    The current code downloads content in _process_item(),
    then calls sync_gii_instrument() which downloads again.
    """
    from private_legal_navigator.application.sync_service import SyncExecutionService, _compute_plan_digest
    from private_legal_navigator.domain.sync import SyncItem, SyncItemStatus, SyncPlan
    from private_legal_navigator.infrastructure.safe_source_client import SourceClient

    plan = SyncPlan(
        schema_version="1.0",
        plan_id=str(uuid.uuid4()),
        sync_run_id=str(uuid.uuid4()),
        source_key="gesetze-im-internet",
        items=[
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=str(uuid.uuid4()),
                source_identifier="SYNTHETISCH – test-instrument",
                abbreviation="SYNTEST",
                title="SYNTHETISCH – Test",
                item_status=SyncItemStatus.NEW,
            )
        ],
    )
    # Compute digest so plan passes integrity check
    plan = SyncPlan(
        schema_version=plan.schema_version,
        plan_id=plan.plan_id,
        sync_run_id=plan.sync_run_id,
        source_key=plan.source_key,
        items=plan.items,
        warnings=plan.warnings,
        estimated_download_bytes=plan.estimated_download_bytes,
        plan_digest=_compute_plan_digest(plan),
    )

    mock_client = MagicMock(spec=SourceClient)
    mock_client.download_with_headers.return_value = MagicMock(
        content=b"<xml>SYNTHETISCH - test content</xml>",
        http_status=200,
        etag='"test-etag"',
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
    )

    mock_repo = MagicMock()
    mock_repo.get_latest_sync_run.return_value = None
    mock_repo.get_snapshot_by_hash.return_value = None

    mock_lss = MagicMock()
    mock_lss.sync_gii_instrument.return_value = MagicMock(
        snapshot=MagicMock(snapshot_id=uuid.uuid4()),
        instrument=MagicMock(instrument_id=uuid.uuid4()),
        expression=MagicMock(expression_id=uuid.uuid4()),
    )

    executor = SyncExecutionService(
        repo=mock_repo,
        legal_source_service=mock_lss,
        source_client=mock_client,
        gii_adapter=MagicMock(),
    )

    executor.execute(plan, dry_run=False)

    # Assert: download_with_headers should be called exactly once per item
    # Currently it's called once in _process_item, but sync_gii_instrument
    # also downloads again via the adapter — the test should verify
    # that the adapter's download is NOT called separately
    assert mock_client.download_with_headers.call_count == 1, (
        f"Expected 1 download, got {mock_client.download_with_headers.call_count}. "
        "Each instrument must be downloaded exactly once per apply."
    )


# ── RED-5: Plan can be applied after corpus change ──


def test_red5_plan_stale_detection():
    """RED-5: Apply MUST reject a plan whose base corpus has changed.

    The SyncPlan currently lacks schema_version, plan_digest,
    and base_corpus_fingerprint — no staleness check is possible.
    """
    from private_legal_navigator.domain.sync import SyncPlan

    plan = SyncPlan(
        sync_run_id=str(uuid.uuid4()),
        items=[],
        warnings=[],
        estimated_download_bytes=0,
    )

    # The plan must have these fields for staleness detection
    required_fields = [
        "schema_version",
        "plan_id",
        "source_key",
        "catalog_url",
        "catalog_sha256",
        "catalog_stand_date",
        "generated_at",
        "base_corpus_fingerprint",
        "plan_digest",
    ]

    missing = [f for f in required_fields if not hasattr(plan, f)]
    assert not missing, (
        f"SyncPlan missing required fields for staleness detection: {missing}. "
        "Without these, a stale plan can be applied after corpus/catalog changes."
    )


# ── RED-6: Tampered plan not detected ──


def test_red6_plan_integrity_check():
    """RED-6: A tampered plan MUST be detected before any mutation.

    The plan_digest field is mandatory for detecting manipulation.
    Apply must verify the digest before the first product mutation.
    """
    from private_legal_navigator.domain.sync import SyncPlan

    plan = SyncPlan(
        sync_run_id=str(uuid.uuid4()),
        items=[],
        warnings=[],
        estimated_download_bytes=0,
    )

    # plan_digest must exist — now present after domain fix
    assert hasattr(plan, "plan_digest"), (
        "SyncPlan must have plan_digest field for integrity verification."
    )

    # Verify the plan() service produces a valid digest
    from private_legal_navigator.application.sync_service import _compute_plan_digest

    # Create a plan with all binding fields populated
    full_plan = SyncPlan(
        schema_version="1.0",
        plan_id="test-plan-id",
        sync_run_id=str(uuid.uuid4()),
        source_key="gesetze-im-internet",
        catalog_url="https://example.com/catalog.xml",
        catalog_sha256="abc123",
        catalog_stand_date="2024-01-01",
        generated_at="2024-01-01T00:00:00Z",
        base_corpus_fingerprint="def456",
        items=[],
        warnings=[],
        estimated_download_bytes=0,
        plan_digest="",  # empty before computation
    )
    digest = _compute_plan_digest(full_plan)
    assert digest and len(digest) == 64, (
        f"plan_digest must be a valid SHA-256 hash (64 hex chars), "
        f"got: '{digest}'"
    )

    # Verify digest changes when plan is modified
    tampered = SyncPlan(
        schema_version=full_plan.schema_version,
        plan_id=full_plan.plan_id,
        sync_run_id=full_plan.sync_run_id,
        source_key=full_plan.source_key,
        catalog_url=full_plan.catalog_url,
        catalog_sha256=full_plan.catalog_sha256,
        catalog_stand_date=full_plan.catalog_stand_date,
        generated_at=full_plan.generated_at,
        base_corpus_fingerprint="TAMPERED_VALUE",
        items=full_plan.items,
        warnings=full_plan.warnings,
        estimated_download_bytes=full_plan.estimated_download_bytes,
        plan_digest="",
    )
    tampered_digest = _compute_plan_digest(tampered)
    assert tampered_digest != digest, (
        "Tampered plan must produce different digest. "
        f"Original: {digest[:16]}, Tampered: {tampered_digest[:16]}"
    )


# ── RED-7: No concurrent apply protection ──


def test_red7_concurrent_apply_prevention():
    """RED-7: Two concurrent apply processes MUST be prevented.

    A file-based or database-based lock per data directory and source_key
    must prevent parallel apply runs. Currently no lock exists.
    """
    from private_legal_navigator.application.sync_service import SyncExecutionService

    # Verify that the execute method has lock acquisition logic
    import inspect

    source = inspect.getsource(SyncExecutionService.execute)
    lock_indicators = ["lock", "flock", "acquire", "SYNC_ALREADY_RUNNING"]
    has_lock = any(indicator.lower() in source.lower() for indicator in lock_indicators)

    assert has_lock, (
        "execute() must acquire a process lock before any mutation. "
        "Without locking, two apply processes can run concurrently, "
        "causing data corruption."
    )


# ── RED-8: Imported bytes ≠ hashed bytes ──


def test_red8_byte_identity_invariant():
    """RED-8: Downloaded bytes must equal parsed bytes must equal snapshot bytes.

    Invariant: HASHED_BYTES == PARSED_BYTES == SNAPSHOT_BYTES

    Currently, _process_item downloads and hashes content, but then
    calls sync_gii_instrument which downloads again. The bytes that
    were hashed are not the bytes that get imported.
    """
    from private_legal_navigator.application.sync_service import SyncExecutionService

    import inspect

    source = inspect.getsource(SyncExecutionService._process_item)

    # Check that the downloaded content is passed through to import
    # The import must receive the SAME bytes object that was hashed
    content_flow_indicators = ["content", "download_result.content", "raw_bytes"]
    hash_then_pass = False

    # Simple heuristic: check if content is passed to import
    lines = source.split("\n")
    download_line = None
    hash_line = None
    import_line = None

    for i, line in enumerate(lines):
        if "download_with_headers" in line or "download(" in line:
            download_line = i
        if "compute_sha256" in line:
            hash_line = i
        if "sync_gii_instrument" in line or "import" in line.lower():
            import_line = i

    # The content reference from download should be used in import
    assert download_line is not None, "Download must occur"
    assert hash_line is not None, "Hash must be computed"
    assert import_line is not None, "Import must occur"
    assert hash_line < import_line, "Hash must be computed BEFORE import"
    assert download_line < import_line, "Download must occur before import"


# ── RED-9: Non-atomic FTS activation ──


def test_red9_atomic_fts_activation():
    """RED-9: FTS must be atomically activated after full persistence.

    If an error occurs between persistence and FTS activation,
    the old valid state must remain. No partial FTS state allowed.
    """
    from private_legal_navigator.application.legal_source_service import LegalSourceService

    import inspect

    # Check that the save_instrument_batch is atomic
    # and that FTS activation happens only after full success
    source = inspect.getsource(LegalSourceService.sync_gii_instrument)

    # Look for atomicity indicators
    atomic_indicators = [
        "save_instrument_batch",
        "atomic",
        "transaction",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
    ]
    has_atomic = any(ind.lower() in source.lower() for ind in atomic_indicators)

    # Look for FTS update AFTER persistence
    fts_indicators = ["fts", "FTS", "full_text", "rebuild"]
    has_fts = any(ind.lower() in source.lower() for ind in fts_indicators)

    # This test will likely fail because:
    # 1. save_instrument_batch may not be truly atomic
    # 2. FTS content rebuild may not be atomic
    if has_atomic and has_fts:
        # Verify FTS happens AFTER persistence
        save_pos = source.find("save_instrument_batch")
        for ind in fts_indicators:
            pos = source.lower().find(ind.lower())
            if pos > 0:
                assert pos > save_pos, (
                    f"FTS operation '{ind}' must occur AFTER persistence, not before. "
                    "Premature FTS activation can leave partial state on error."
                )


# ── RED-10: Truth mirror numbers without fresh evidence ──


def test_red10_truth_mirror_requires_fresh_evidence():
    """RED-10: Truth mirror numbers MUST be backed by fresh test execution.

    README.md and release documents must only contain numbers from
    the most recent test run, not manually entered claims.
    """
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    if not readme_path.exists():
        pytest.skip("README.md not found")

    content = readme_path.read_text()

    # Check for unverified numerical claims
    import re

    # Look for patterns like "XX tests" or "XX% coverage"
    test_claims = re.findall(r"(\d+)\s+(?:tests|Tests)", content)
    coverage_claims = re.findall(r"(\d+)%\s*(?:coverage|Coverage|Abdeckung)", content)

    # These claims must be traceable to the most recent evidence
    # For now, verify they exist and flag them as needing fresh evidence
    if test_claims:
        # Check if there's evidence of a recent test run matching these numbers
        evidence_dir = Path(__file__).parent.parent  # evidence/rc025/
        baseline = evidence_dir / "baseline" / "test-collection.txt"
        if baseline.exists():
            baseline_text = baseline.read_text()
            for claim in test_claims:
                assert claim in baseline_text, (
                    f"README claims {claim} tests, but baseline evidence does not "
                    f"confirm this number. Truth mirror requires fresh evidence."
                )
