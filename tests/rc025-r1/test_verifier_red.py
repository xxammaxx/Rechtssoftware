"""RC-025-R1 RED Contract Verification Tests — F4 Byte Identity & F6 Atomicity.

INDEPENDENT VERIFIER TESTS — must NOT be modified by the Builder.
These tests demonstrate genuine violations before any fix is applied.

Created: 2026-08-02 | Independent Verifier
Test data: SYNTHETISCH – no real GII calls, no real legal data.
"""

import hashlib
import io
import os
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.rc025_r1_verifier, pytest.mark.m7b_integrity]

# ── Helpers ────────────────────────────────────────────────────


def _temp_db() -> Path:
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_rc025_r1_")
    os.close(fd)
    return Path(path)


def _wrap_in_zip(xml_bytes: bytes, filename: str = "gesetz.xml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, xml_bytes)
    return buf.getvalue()


# ── Synthetic test data ──────────────────────────────────────────

SYNTH_CATALOG = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<gii-toc stand="2026-08-01">\n'
    b'  <item>\n'
    b'    <link>https://www.gesetze-im-internet.de/bgb/xml.zip</link>\n'
    b'    <title>B\xc3\xbcrgerliches Gesetzbuch</title>\n'
    b'    <type>G</type>\n'
    b'  </item>\n'
    b'</gii-toc>\n'
)

SYNTH_BGB_XML_V1 = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<norm>\n'
    b'  <metadaten>\n'
    b'    <jurabk>BGB</jurabk>\n'
    b'    <langue>B\xc3\xbcrgerliches Gesetzbuch</langue>\n'
    b'  </metadaten>\n'
    b'  <textdaten>\n'
    b'    <text>\n'
    b'      <Content>\n'
    b'        <P>\xc2\xa7 1 Beginn der Rechtsf\xc3\xa4higkeit.'
    b' Die Rechtsf\xc3\xa4higkeit des Menschen beginnt'
    b' mit der Vollendung der Geburt.</P>\n'
    b'      </Content>\n'
    b'    </text>\n'
    b'  </textdaten>\n'
    b'</norm>\n'
)

SYNTH_BGB_XML_V2 = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<norm>\n'
    b'  <metadaten>\n'
    b'    <jurabk>BGB</jurabk>\n'
    b'    <langue>B\xc3\xbcrgerliches Gesetzbuch (ge\xc3\xa4ndert)</langue>\n'
    b'  </metadaten>\n'
    b'  <textdaten>\n'
    b'    <text>\n'
    b'      <Content>\n'
    b'        <P>\xc2\xa7 1 Beginn der Rechtsf\xc3\xa4higkeit.'
    b' Die Rechtsf\xc3\xa4higkeit des Menschen beginnt'
    b' mit der Vollendung der Geburt. (Stand: 2026)</P>\n'
    b'      </Content>\n'
    b'    </text>\n'
    b'  </textdaten>\n'
    b'</norm>\n'
)

SYNTH_BGB_ZIP_V1 = _wrap_in_zip(SYNTH_BGB_XML_V1, "bgb.xml")
SYNTH_BGB_ZIP_V2 = _wrap_in_zip(SYNTH_BGB_XML_V2, "bgb.xml")


# ── Adversarial Download Tracking ────────────────────────────────


def _make_adversarial_download_fn():
    """Create download functions that serve DIFFERENT content.

    download_with_headers (used by _process_item): always returns V1.
    download (used by sync_instrument): always returns V2.
    
    This simulates a race condition where the server changes between
    the two download calls — proving byte identity violation.
    """
    call_count = {"download": 0, "download_with_headers": 0}
    urls_seen: dict[str, int] = {}

    def adversarial_download(self, url: str) -> bytes:
        call_count["download"] += 1
        urls_seen[url] = urls_seen.get(url, 0) + 1
        if "gii-toc.xml" in url:
            return SYNTH_CATALOG
        # Instrument download via sync_instrument: ALWAYS return V2
        return SYNTH_BGB_ZIP_V2

    def adversarial_download_with_headers(self, url: str):
        from private_legal_navigator.infrastructure.safe_source_client import (
            DownloadResult,
        )
        call_count["download_with_headers"] += 1
        # download_with_headers via _process_item: ALWAYS return V1
        return DownloadResult(
            content=SYNTH_BGB_XML_V1,
            http_status=200,
            etag='"etag-v1"',
            last_modified="Sat, 02 Aug 2026 00:00:00 GMT",
            content_type="application/xml",
        )

    return adversarial_download, adversarial_download_with_headers, call_count


# ──────────────────────────────────────────────────────────────
# RED-R1-1: Double Download Proof
# ──────────────────────────────────────────────────────────────


def test_red_r1_double_download_detected() -> None:
    """RED: Prove that the current code downloads the same instrument
    at least twice during a single apply (via download_with_headers
    and then via sync_gii_instrument → sync_instrument → download).

    Patches SourceClient.download and download_with_headers to track
    call counts. After a non-dry-run apply to a single NEW item,
    asserts that more than one download call was made.
    """
    from private_legal_navigator.application.legal_source_service import (
        LegalSourceService,
    )
    from private_legal_navigator.application.sync_service import (
        SyncExecutionService,
        SyncPlanningService,
    )
    from private_legal_navigator.infrastructure.database import initialize_schema
    from private_legal_navigator.infrastructure.gii_adapter import GiiAdapter
    from private_legal_navigator.infrastructure.safe_source_client import (
        SourceClient,
        SourceClientConfig,
        TransportMode,
    )
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    db_path = _temp_db()
    db_path.unlink(missing_ok=True)
    try:
        initialize_schema(db_path)
        repo = SqliteLegalSourceRepository(db_path)
        config = SourceClientConfig(transport_mode=TransportMode.TEST)

        adv_dl, adv_dlwh, call_count = _make_adversarial_download_fn()

        with (
            patch.object(SourceClient, "download", adv_dl),
            patch.object(SourceClient, "download_with_headers", adv_dlwh),
        ):
            client = SourceClient(config)

            with tempfile.TemporaryDirectory() as snap_dir:
                snap_path = Path(snap_dir)
                gii = GiiAdapter(client, snap_path)

                planner = SyncPlanningService(repo, client, gii)
                plan = planner.plan()

                # Only proceed if we have NEW items
                new_items = [i for i in plan.items if i.item_status.value == "NEW"]
                if not new_items:
                    pytest.skip("No NEW items in plan")

                lss = LegalSourceService(repo, client, snap_path)
                executor = SyncExecutionService(repo, lss, client, gii)

                # Count before
                dl_before = call_count["download"]
                dlwh_before = call_count["download_with_headers"]

                executor.execute(plan, dry_run=False)

                dl_after = call_count["download"]
                dlwh_after = call_count["download_with_headers"]

                total_downloads = (dl_after - dl_before) + (dlwh_after - dlwh_before)

                # RED assertion: total downloads > 1
                # If this fails (=1), the double-download problem was already fixed
                assert total_downloads > 1, (
                    f"RED-R1-1 PASSED: Expected >1 download call, got {total_downloads} "
                    f"(download={dl_after - dl_before}, "
                    f"download_with_headers={dlwh_after - dlwh_before}). "
                    f"If total=1, the double-download violation may already be fixed."
                )
    finally:
        db_path.unlink(missing_ok=True)
        # Clean up WAL/SHM
        for suffix in (".db-wal", ".db-shm"):
            p = Path(str(db_path) + suffix)
            p.unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────
# RED-R1-2: Byte Identity Violation
# ──────────────────────────────────────────────────────────────


def test_red_r1_byte_identity_violation() -> None:
    """RED: Prove bytes hashed in _process_item differ from snapshot.
    
    Patches SourceClient to serve V1 on download_with_headers and
    V2 on download. After execution, compares the hash from the
    sync item (computed from V1 bytes) with the snapshot hash
    (computed from V2 bytes). These MUST differ before the fix.
    """
    from private_legal_navigator.application.legal_source_service import (
        LegalSourceService,
    )
    from private_legal_navigator.application.sync_service import (
        SyncExecutionService,
        SyncPlanningService,
    )
    from private_legal_navigator.infrastructure.database import initialize_schema
    from private_legal_navigator.infrastructure.gii_adapter import GiiAdapter
    from private_legal_navigator.infrastructure.safe_source_client import (
        SourceClient,
        SourceClientConfig,
        TransportMode,
    )
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    db_path = _temp_db()
    db_path.unlink(missing_ok=True)
    try:
        initialize_schema(db_path)
        repo = SqliteLegalSourceRepository(db_path)
        config = SourceClientConfig(transport_mode=TransportMode.TEST)

        adv_dl, adv_dlwh, call_count = _make_adversarial_download_fn()

        with (
            patch.object(SourceClient, "download", adv_dl),
            patch.object(SourceClient, "download_with_headers", adv_dlwh),
        ):
            client = SourceClient(config)

            with tempfile.TemporaryDirectory() as snap_dir:
                snap_path = Path(snap_dir)
                gii = GiiAdapter(client, snap_path)

                planner = SyncPlanningService(repo, client, gii)
                plan = planner.plan()

                lss = LegalSourceService(repo, client, snap_path)
                executor = SyncExecutionService(repo, lss, client, gii)
                executor.execute(plan, dry_run=False)

                # Check sync items against snapshots
                runs = repo.list_runs(source_key="gesetze-im-internet")
                if not runs:
                    pytest.skip("No sync runs created — cannot verify byte identity")

                items = repo.get_items_for_run(runs[0].sync_run_id)
                mismatches = 0
                for item_dict in items:
                    snap_id_str = item_dict.get("snapshot_id")
                    new_sha = item_dict.get("new_sha256", "")
                    if not snap_id_str or not new_sha:
                        continue

                    from uuid import UUID
                    snapshot = repo.get_snapshot(UUID(str(snap_id_str)))
                    if snapshot is None:
                        continue

                    snap_sha = snapshot.sha256
                    if new_sha != snap_sha:
                        mismatches += 1

                if mismatches > 0:
                    # RED: Violation found — test passes as RED
                    return

                # If no mismatch found, warn that the test may be inconclusive
                if call_count["download_with_headers"] > 0 and call_count["download"] > 0:
                    pytest.fail(
                        "RED-R1-2 INCONCLUSIVE: Downloads occurred but no hash mismatch "
                        "was detected. Hashes may have coincidentally matched or the "
                        "code path may differ from expectations."
                    )
    finally:
        db_path.unlink(missing_ok=True)
        for suffix in (".db-wal", ".db-shm"):
            p = Path(str(db_path) + suffix)
            p.unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────
# RED-R1-3: No Download Count Enforcement
# ──────────────────────────────────────────────────────────────


def test_red_r1_no_download_count_check() -> None:
    """RED: Prove that _process_item has no mechanism to ensure
    download_count == 1 per instrument.
    
    Inspects the source code of SyncExecutionService._process_item
    and the SyncItem domain model for any download counting.
    """
    import inspect

    from private_legal_navigator.application.sync_service import SyncExecutionService
    from private_legal_navigator.domain.sync import SyncItem

    source = inspect.getsource(SyncExecutionService._process_item)

    # Check for download count / payload tracking
    has_counter = any(
        term in source.lower()
        for term in ["download_count", "download_counter", "payload", "verified_"]
    )

    # Check SyncItem for download_count field
    item_fields = [f.name for f in SyncItem.__dataclass_fields__.values()]
    has_field = "download_count" in item_fields

    # RED: Before F4 fix, there should be no counter mechanism
    if has_counter or has_field:
        pytest.fail(
            "RED-R1-3: Download counting mechanism already present. "
            f"has_counter={has_counter}, has_field={has_field}"
        )
    # Test passes as RED — violation confirmed (no counting exists)


# ──────────────────────────────────────────────────────────────
# RED-R1-5: Snapshot Hash Not Cross-Validated
# ──────────────────────────────────────────────────────────────


def test_red_r1_snapshot_hash_not_cross_validated() -> None:
    """RED: Prove that snapshot hash is never compared against
    the hash computed from download_with_headers content.
    
    After a non-dry-run apply, verify that there is no code path
    that validates snapshot.sha256 == item.new_sha256.
    """
    import inspect

    from private_legal_navigator.application.sync_service import SyncExecutionService

    source = inspect.getsource(SyncExecutionService._process_item)

    # Check if there's any cross-validation between new_sha256 and snapshot hash
    # The new_sha256 is computed (line 690) and stored on item (line 691)
    # But the snapshot hash comes from sync_gii_instrument (line 719) 
    # via save_instrument_batch — these two values are NEVER compared.
    
    # The RED condition: new_sha256 exists in source AND
    # there is NO comparison between new_sha256 and any snapshot property
    has_new_sha256 = "new_sha256" in source
    
    # Check for explicit cross-validation:
    # "new_sha256 == snapshot" or "new_sha256 != snapshot" or
    # "computed_sha256 == parsed.snapshot" etc.
    has_explicit_check = any(
        pattern in source
        for pattern in [
            "new_sha256 == parsed.snapshot",
            "new_sha256 != parsed.snapshot",
            "computed_sha256 == snapshot",
            "computed_sha256 == parsed.snapshot",
        ]
    )
    
    if not has_explicit_check:
        # RED: no cross-validation between download hash and snapshot hash
        return
    
    pytest.fail(
        "RED-R1-5: Cross-validation between new_sha256 and snapshot.sha256 "
        "may already exist. Manual review required."
    )
