"""Tests for content-addressable snapshot storage (Track C — M7-A.1)."""

import tempfile
from pathlib import Path

from private_legal_navigator.infrastructure.safe_source_client import (
    _write_content_addressed,
    compute_sha256,
)


class TestContentAddressedStorage:
    def test_deterministic_hash_path(self):
        """SNAP-001: Same content produces same path."""
        content = b"test content for hashing"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            path1, hash1 = _write_content_addressed(content, target)
            path2, hash2 = _write_content_addressed(content, target)
            assert path1 == path2
            assert hash1 == hash2
            assert path1.name == f"{hash1}.xml"
            # Verify the 2-char prefix directory
            assert path1.parent.name == hash1[:2]

    def test_duplicate_sync_creates_no_second_file(self):
        """SNAP-002: Same content twice → only one file."""
        content = b"unique snapshot data"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            path1, hash1 = _write_content_addressed(content, target)
            # Count files before second write
            files_before = list(target.rglob("*.xml"))
            path2, hash2 = _write_content_addressed(content, target)
            files_after = list(target.rglob("*.xml"))
            assert path1 == path2
            assert hash1 == hash2
            assert len(files_after) == len(files_before)

    def test_different_content_different_path(self):
        """Different content → different paths."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            path1, _ = _write_content_addressed(b"content A", target)
            path2, _ = _write_content_addressed(b"content B", target)
            assert path1 != path2
            assert path1.exists()
            assert path2.exists()

    def test_tampering_detected(self):
        """SNAP-004: Tampered content is detected via hash."""
        content = b"original content"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            path, original_hash = _write_content_addressed(content, target)
            # Tamper the file
            path.write_bytes(b"tampered content")
            # Re-read and verify hash mismatch
            tampered_content = path.read_bytes()
            tampered_hash = compute_sha256(tampered_content)
            assert tampered_hash != original_hash

    def test_content_addressed_naming_scheme(self):
        """Verify the SHA-256 based naming scheme."""
        content = b"test"
        sha = compute_sha256(content)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            path, hash_val = _write_content_addressed(content, target)
            assert hash_val == sha
            assert path.name == f"{sha}.xml"
            assert path.parent.name == sha[:2]
            assert path.parent.parent == target
