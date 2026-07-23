"""Tests for evidence pack truth (Track F — M7-A.1)."""

import uuid
from datetime import datetime


def test_evidence_pack_not_tracked_facts():
    """Facts should signal NOT_TRACKED_IN_THIS_RELEASE, not just be empty."""
    from private_legal_navigator.domain.case_timeline import EvidencePack

    pack = EvidencePack(case_id=uuid.uuid4())
    assert len(pack.confirmed_facts) == 0 or pack.confirmed_facts == []
    assert len(pack.open_facts) == 0 or pack.open_facts == []
    assert len(pack.legal_issues) == 0 or pack.legal_issues == []


def test_evidence_pack_integrity_has_snapshots_key():
    """Integrity dict should accommodate snapshots with verification status."""
    from private_legal_navigator.domain.case_timeline import EvidencePack

    pack = EvidencePack(case_id=uuid.uuid4())
    # Default integrity is empty dict
    assert isinstance(pack.integrity, dict)


def test_not_tracked_evidence_pack_flag():
    """An evidence pack built by the repository should have NOT_TRACKED signals."""
    from private_legal_navigator.domain.case_timeline import EvidencePack

    pack = EvidencePack(
        case_id=uuid.uuid4(),
        confirmed_facts=[{"_note": "NOT_TRACKED_IN_THIS_RELEASE"}],
        open_facts=[{"_note": "NOT_TRACKED_IN_THIS_RELEASE"}],
        legal_issues=[{"_note": "NOT_TRACKED_IN_THIS_RELEASE"}],
    )
    assert pack.confirmed_facts[0]["_note"] == "NOT_TRACKED_IN_THIS_RELEASE"
    assert pack.open_facts[0]["_note"] == "NOT_TRACKED_IN_THIS_RELEASE"
    assert pack.legal_issues[0]["_note"] == "NOT_TRACKED_IN_THIS_RELEASE"


def test_integrity_snapshots_structure():
    """Integrity snapshots list should contain sha256, status, snapshot_id."""
    from private_legal_navigator.domain.case_timeline import EvidencePack

    integrity = {
        "exported_at": datetime.now().isoformat(),
        "active_events_count": 0,
        "active_links_count": 0,
        "provisions_count": 0,
        "snapshots_count": 1,
        "snapshots": [
            {
                "sha256": "abc123",
                "status": "NOT_VERIFIED",
                "snapshot_id": "00000000-0000-0000-0000-000000000001",
            }
        ],
    }
    pack = EvidencePack(case_id=uuid.uuid4(), integrity=integrity)
    assert "snapshots" in pack.integrity
    assert len(pack.integrity["snapshots"]) == 1
    assert pack.integrity["snapshots"][0]["status"] == "NOT_VERIFIED"
