"""Tests for CLI verify command (Track D — M7-A.1)."""

import uuid
from unittest.mock import MagicMock

from private_legal_navigator.application.legal_source_service import LegalSourceService


class TestVerifySnapshotDetailed:
    def test_verify_snapshot_missing_returns_missing_status(self):
        repo = MagicMock()
        repo.get_snapshot.return_value = None
        svc = LegalSourceService(repo, MagicMock(), MagicMock())
        result = svc._verify_snapshot_detailed(uuid.uuid4())
        assert result["status"] == "MISSING"
        assert result["error_code"] == "SNAPSHOT_NOT_FOUND"

    def test_verify_all_snapshots_returns_list(self):
        repo = MagicMock()
        repo.list_sources.return_value = []
        svc = LegalSourceService(repo, MagicMock(), MagicMock())
        results = svc.verify_all_snapshots()
        assert isinstance(results, list)
        assert len(results) == 0
