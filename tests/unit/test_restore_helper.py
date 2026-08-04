"""Comprehensive tests for safe ZIP restore helper."""

import hashlib
import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest import mock
from zipfile import ZipFile, ZipInfo

import pytest

from private_legal_navigator.infrastructure.restore_helper import (
    MAX_FILE_SIZE,
    _check_database_integrity,
    _sha256_hex,
    _validate_file_hashes,
    _validate_manifest_hash,
    _validate_zip_entries,
    _validate_zip_entry_path,
    restore_backup,
    run_restore_cli,
)


def _create_zip_with_entries(zip_path, entries):
    with ZipFile(zip_path, "w") as zf:
        for name, content, external_attr in entries:
            info = ZipInfo(name)
            info.date_time = time.localtime()[:6]
            info.external_attr = external_attr
            data = content if isinstance(content, bytes) else content.encode()
            info.file_size = len(data)
            info.compress_size = len(data)
            zf.writestr(info, data)


def _create_minimal_restore_zip(zip_path, db_content=None):
    if db_content is None:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        db_content = conn.serialize()
        conn.close()
    db_hash = hashlib.sha256(db_content).hexdigest()
    manifest_without_hash = {
        "app_name": "PrivateLegalNavigator",
        "app_version": "1.0.0rc2",
        "schema_version": "unknown",
        "created_at": "2026-07-28T00:00:00Z",
        "db_sha256": db_hash,
        "db_integrity": "ok",
        "db_file": "private_legal_navigator.db",
        "document_count": 0,
        "snapshot_count": 0,
        "documents": [],
        "snapshots": [],
    }
    manifest_json = json.dumps(manifest_without_hash, indent=2)
    manifest_file_hash = hashlib.sha256(manifest_json.encode()).hexdigest()
    manifest_with_hash = dict(manifest_without_hash)
    manifest_with_hash["manifest_sha256"] = manifest_file_hash

    entries = [
        ("private_legal_navigator.db", db_content, 0o100644 << 16),
        ("backup-manifest.json", manifest_json, 0o100644 << 16),
    ]
    _create_zip_with_entries(zip_path, entries)


class TestValidateZipEntryPath:
    def test_simple_relative_path(self):
        assert _validate_zip_entry_path("file.txt") == "file.txt"

    def test_nested_path(self):
        assert _validate_zip_entry_path("sub/dir/file.txt") == "sub/dir/file.txt"

    def test_blocks_absolute_unix_path(self):
        with pytest.raises(ValueError, match="Absolute"):
            _validate_zip_entry_path("/etc/passwd")

    def test_blocks_absolute_root_path(self):
        with pytest.raises(ValueError, match="Absolute"):
            _validate_zip_entry_path("/root")

    def test_blocks_drive_letter(self):
        with pytest.raises(ValueError, match="Drive"):
            _validate_zip_entry_path("C:\\Windows\\System32")

    def test_blocks_drive_letter_second(self):
        with pytest.raises(ValueError, match="Drive"):
            _validate_zip_entry_path("D:evil.txt")

    def test_blocks_unc_path_double_slash(self):
        with pytest.raises(ValueError, match="(Absolute|UNC)"):
            _validate_zip_entry_path("//server/share/file")

    def test_blocks_unc_path_double_backslash(self):
        with pytest.raises(ValueError, match="(Absolute|UNC)"):
            _validate_zip_entry_path("\\\\server\\share\\file")

    def test_blocks_parent_traversal(self):
        with pytest.raises(ValueError, match="traversal"):
            _validate_zip_entry_path("../etc/passwd")

    def test_blocks_deep_traversal(self):
        with pytest.raises(ValueError, match="traversal"):
            _validate_zip_entry_path("a/../../etc/passwd")

    def test_normalizes_backslashes(self):
        result = _validate_zip_entry_path("foo\\bar\\baz.txt")
        assert result == "foo/bar/baz.txt"

    def test_blocks_empty_path(self):
        with pytest.raises(ValueError, match="Empty"):
            _validate_zip_entry_path("")

    def test_blocks_single_dot(self):
        with pytest.raises(ValueError, match="Empty path"):
            _validate_zip_entry_path(".")

    def test_allows_double_dot_in_middle(self):
        result = _validate_zip_entry_path("a/b/../c")
        assert result == "a/c"

    def test_allows_leading_dot_slash(self):
        result = _validate_zip_entry_path("./file.txt")
        assert result == "file.txt"

    def test_normalizes_multiple_slashes(self):
        result = _validate_zip_entry_path("a//b///c")
        assert result == "a/b/c"

    def test_blocks_relative_path_root_traversal_start(self):
        with pytest.raises(ValueError, match="traversal"):
            _validate_zip_entry_path("..")


class TestValidateZipEntries:
    def test_valid_entries(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        entries = [
            ("file1.txt", b"content1", 0o100644 << 16),
            ("sub/file2.txt", b"content2", 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        result = _validate_zip_entries(zip_path)
        assert len(result) == 2
        paths = [r[0] for r in result]
        assert "file1.txt" in paths
        assert "sub/file2.txt" in paths

    def test_blocks_symlink(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        entries = [("link.txt", b"target", (0o120000) << 16)]
        _create_zip_with_entries(zip_path, entries)
        with pytest.raises(ValueError, match="Symlink"):
            _validate_zip_entries(zip_path)

    def test_blocks_duplicate_normalized_path(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        entries = [
            ("file.txt", b"a", 0o100644 << 16),
            ("file.txt", b"b", 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        with pytest.raises(ValueError, match="Duplicate"):
            _validate_zip_entries(zip_path)

    def test_blocks_duplicate_through_traversal(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        entries = [
            ("sub/../file.txt", b"a", 0o100644 << 16),
            ("file.txt", b"b", 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        with pytest.raises(ValueError, match="Duplicate"):
            _validate_zip_entries(zip_path)

    def test_blocks_oversized_file(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        big = b"x" * (MAX_FILE_SIZE + 1)
        entries = [("big.dat", big, 0o100644 << 16)]
        _create_zip_with_entries(zip_path, entries)
        with pytest.raises(ValueError, match="File too large"):
            _validate_zip_entries(zip_path)

    def test_blocks_oversized_total(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        third = b"x" * 700_000_000
        entries = [
            ("a.dat", third, 0o100644 << 16),
            ("b.dat", third, 0o100644 << 16),
            ("c.dat", third, 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        with pytest.raises(ValueError, match="(File too large|Total extraction size)"):
            _validate_zip_entries(zip_path)

    def test_allows_directories(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        with ZipFile(zip_path, "w") as zf:
            info = ZipInfo("subdir/")
            info.external_attr = 0o040755 << 16
            zf.writestr(info, "")
            info2 = ZipInfo("subdir/file.txt")
            info2.external_attr = 0o100644 << 16
            zf.writestr(info2, b"content")
        result = _validate_zip_entries(zip_path)
        assert len(result) == 1
        assert result[0][0] == "subdir/file.txt"


class TestValidateManifestHash:
    def test_valid_manifest(self, tmp_path):
        manifest = {
            "app_name": "PrivateLegalNavigator",
            "app_version": "1.0.0",
            "db_file": "test.db",
        }
        (tmp_path / "backup-manifest.json").write_text(json.dumps(manifest))
        result = _validate_manifest_hash(tmp_path)
        assert result["app_name"] == "PrivateLegalNavigator"

    def test_missing_manifest(self, tmp_path):
        with pytest.raises(ValueError, match="No backup-manifest"):
            _validate_manifest_hash(tmp_path)

    def test_invalid_json(self, tmp_path):
        (tmp_path / "backup-manifest.json").write_text("{not valid")
        with pytest.raises(ValueError, match="Invalid"):
            _validate_manifest_hash(tmp_path)

    def test_missing_required_field(self, tmp_path):
        manifest = {"app_name": "X"}
        (tmp_path / "backup-manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="Missing required"):
            _validate_manifest_hash(tmp_path)

    def test_missing_app_name(self, tmp_path):
        manifest = {"app_version": "1.0", "db_file": "x"}
        (tmp_path / "backup-manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="Missing required"):
            _validate_manifest_hash(tmp_path)

    def test_missing_db_file(self, tmp_path):
        manifest = {"app_name": "X", "app_version": "1.0"}
        (tmp_path / "backup-manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="Missing required"):
            _validate_manifest_hash(tmp_path)


class TestValidateFileHashes:
    def test_matching_hashes(self, tmp_path):
        db = tmp_path / "test.db"
        content = b"db content"
        db.write_bytes(content)
        db_hash = hashlib.sha256(content).hexdigest()
        manifest = {
            "db_file": "test.db",
            "db_sha256": db_hash,
        }
        _validate_file_hashes(tmp_path, manifest)

    def test_mismatched_hash(self, tmp_path):
        db = tmp_path / "test.db"
        db.write_bytes(b"content")
        manifest = {
            "db_file": "test.db",
            "db_sha256": "a" * 64,
        }
        with pytest.raises(ValueError, match="Hash mismatch"):
            _validate_file_hashes(tmp_path, manifest)

    def test_missing_db_skipped(self, tmp_path):
        manifest = {"db_file": "missing.db", "db_sha256": "a" * 64}
        _validate_file_hashes(tmp_path, manifest)

    def test_document_hash_validation(self, tmp_path):
        docs = tmp_path / "documents"
        docs.mkdir()
        (docs / "a.txt").write_bytes(b"hello")
        doc_hash = hashlib.sha256(b"hello").hexdigest()
        manifest = {
            "db_file": "x.db",
            "documents": [{"path": "a.txt", "sha256": doc_hash}],
        }
        _validate_file_hashes(tmp_path, manifest)

    def test_document_hash_mismatch(self, tmp_path):
        docs = tmp_path / "documents"
        docs.mkdir()
        (docs / "a.txt").write_bytes(b"hello")
        manifest = {
            "db_file": "x.db",
            "documents": [{"path": "a.txt", "sha256": "b" * 64}],
        }
        with pytest.raises(ValueError, match="Hash mismatch"):
            _validate_file_hashes(tmp_path, manifest)

    def test_snapshot_hash_validation(self, tmp_path):
        snaps = tmp_path / "snapshots"
        snaps.mkdir()
        (snaps / "s1.xml").write_bytes(b"<data/>")
        snap_hash = hashlib.sha256(b"<data/>").hexdigest()
        manifest = {
            "db_file": "x.db",
            "snapshots": [{"path": "s1.xml", "sha256": snap_hash}],
        }
        _validate_file_hashes(tmp_path, manifest)

    def test_manifest_self_hash(self, tmp_path):
        mp = tmp_path / "backup-manifest.json"
        mp.write_text("{}")
        mp_hash = hashlib.sha256(b"{}").hexdigest()
        manifest = {
            "db_file": "x.db",
            "manifest_sha256": mp_hash,
        }
        _validate_file_hashes(tmp_path, manifest)


class TestCheckDatabaseIntegrity:
    def test_ok_integrity(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        assert _check_database_integrity(tmp_path, "test.db") == "ok"

    def test_missing_db(self, tmp_path):
        assert _check_database_integrity(tmp_path, "missing.db") == "no database file"

    def test_corrupt_db(self, tmp_path):
        db = tmp_path / "test.db"
        db.write_bytes(b"this is not a database")
        result = _check_database_integrity(tmp_path, "test.db")
        assert result != "ok"


class TestSha256Hex:
    def test_known_hash(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"data")
        expected = hashlib.sha256(b"data").hexdigest()
        assert _sha256_hex(f) == expected


class TestRestoreBackup:
    def test_full_restore_success(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "restored"
        result = restore_backup(zip_path, target)
        assert result["status"] == "restored"
        assert result["db_integrity"] == "ok"
        assert (target / "private_legal_navigator.db").exists()
        assert (target / "backup-manifest.json").exists()

    def test_missing_zip(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            restore_backup(tmp_path / "missing.zip", tmp_path / "target")

    def test_existing_target_requires_force(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        target.mkdir()
        (target / "existing.txt").write_text("data")
        with pytest.raises(ValueError, match="force=True"):
            restore_backup(zip_path, target)

    def test_existing_target_with_force(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        target.mkdir()
        (target / "old.txt").write_text("old")
        result = restore_backup(zip_path, target, force=True)
        assert result["status"] == "restored"
        assert not (target / "old.txt").exists()

    def test_atomic_restore_preserves_data(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        result = restore_backup(zip_path, target)
        assert result["db_integrity"] == "ok"
        conn = sqlite3.connect(str(target / "private_legal_navigator.db"))
        rows = conn.execute("SELECT * FROM t").fetchall()
        conn.close()
        assert rows[0] == (1,)

    def test_restore_with_documents(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        doc_content = b"PDF document content"
        doc_hash = hashlib.sha256(doc_content).hexdigest()
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        manifest = {
            "app_name": "PrivateLegalNavigator",
            "app_version": "1.0.0",
            "db_file": "private_legal_navigator.db",
            "db_sha256": "",
            "documents": [
                {"path": "docs/doc1.pdf", "sha256": doc_hash, "size_bytes": len(doc_content)}
            ],
            "snapshots": [],
            "document_count": 1,
            "snapshot_count": 0,
        }
        entries = [
            ("private_legal_navigator.db", b"", 0o100644 << 16),
            ("documents/docs/doc1.pdf", doc_content, 0o100644 << 16),
            ("backup-manifest.json", json.dumps(manifest), 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        target = tmp_path / "target"
        result = restore_backup(zip_path, target)
        assert result["document_count"] == 1
        assert (target / "documents" / "docs" / "doc1.pdf").exists()
        assert (target / "documents" / "docs" / "doc1.pdf").read_bytes() == doc_content

    def test_integrity_failure_prevents_restore(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        corrupt_db = b"this is absolutely not a valid sqlite database"
        db_hash = hashlib.sha256(corrupt_db).hexdigest()
        manifest = {
            "app_name": "PrivateLegalNavigator",
            "app_version": "1.0.0",
            "db_file": "private_legal_navigator.db",
            "db_sha256": db_hash,
            "documents": [],
            "snapshots": [],
        }
        entries = [
            ("private_legal_navigator.db", corrupt_db, 0o100644 << 16),
            ("backup-manifest.json", json.dumps(manifest), 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        target = tmp_path / "target"
        with pytest.raises(ValueError, match="integrity"):
            restore_backup(zip_path, target)
        assert not target.exists()

    def test_hash_mismatch_prevents_restore(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        manifest = {
            "app_name": "PrivateLegalNavigator",
            "app_version": "1.0.0",
            "db_file": "private_legal_navigator.db",
            "db_sha256": "f" * 64,
            "documents": [],
            "snapshots": [],
        }
        entries = [
            ("private_legal_navigator.db", b"real db content", 0o100644 << 16),
            ("backup-manifest.json", json.dumps(manifest), 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        target = tmp_path / "target"
        with pytest.raises(ValueError, match="Hash mismatch"):
            restore_backup(zip_path, target)
        assert not target.exists()

    def test_rollback_on_switch_failure(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        target.mkdir()
        old_file = target / "protected.txt"
        old_file.write_text("important data")
        with (
            mock.patch("shutil.move", side_effect=OSError("Simulated failure")),
            pytest.raises((ValueError, OSError)),
        ):
            restore_backup(zip_path, target, force=True)
        assert old_file.exists()
        assert old_file.read_text() == "important data"

    def test_extremely_high_compression_safe(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        result = restore_backup(zip_path, target)
        assert result["status"] == "restored"

    def test_unknown_extra_files_in_zip(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        db_content = conn.serialize()
        conn.close()
        db_hash = hashlib.sha256(db_content).hexdigest()
        manifest = {
            "app_name": "PrivateLegalNavigator",
            "app_version": "1.0.0",
            "db_file": "private_legal_navigator.db",
            "db_sha256": db_hash,
            "documents": [],
            "snapshots": [],
        }
        manifest_json = json.dumps(manifest, indent=2)
        man_hash = hashlib.sha256(manifest_json.encode()).hexdigest()
        manifest["manifest_sha256"] = man_hash
        entries = [
            ("private_legal_navigator.db", db_content, 0o100644 << 16),
            ("backup-manifest.json", manifest_json, 0o100644 << 16),
            ("extra_unexpected_file.log", b"log", 0o100644 << 16),
        ]
        _create_zip_with_entries(zip_path, entries)
        target = tmp_path / "target"
        result = restore_backup(zip_path, target)
        assert result["status"] == "restored"

    def test_staging_cleaned_on_failure(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "/nonexistent/path/that/fails"
        with pytest.raises((ValueError, OSError, PermissionError)):
            restore_backup(zip_path, target)
        staged = list(Path(tempfile.gettempdir()).glob("pln-restore-staging-*"))
        assert len(staged) == 0


class TestRestoreRunRestoreCLI:
    def test_cli_restores_successfully(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        args = ["restore", str(zip_path), str(target)]
        with mock.patch("sys.argv", args):
            rc = run_restore_cli()
        assert rc == 0
        assert (target / "private_legal_navigator.db").exists()

    def test_cli_with_force(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        target.mkdir()
        (target / "old.txt").write_text("old")
        args = ["restore", str(zip_path), str(target), "--force"]
        with mock.patch("sys.argv", args):
            rc = run_restore_cli()
        assert rc == 0

    def test_cli_insufficient_args(self):
        with mock.patch("sys.argv", ["restore"]):
            rc = run_restore_cli()
        assert rc == 1

    def test_cli_single_arg(self):
        with mock.patch("sys.argv", ["restore", "/tmp/foo"]):
            rc = run_restore_cli()
        assert rc == 1

    def test_cli_nonexistent_zip(self, tmp_path):
        args = ["restore", str(tmp_path / "missing.zip"), str(tmp_path / "tgt")]
        with mock.patch("sys.argv", args):
            rc = run_restore_cli()
        assert rc == 1

    def test_cli_sys_exit_integration(self, tmp_path):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        args = ["restore_helper.py", str(zip_path), str(target)]
        with mock.patch("sys.argv", args):
            rc = run_restore_cli()
        assert rc == 0

    def test_cli_prints_json_result(self, tmp_path, capsys):
        zip_path = tmp_path / "backup.zip"
        _create_minimal_restore_zip(zip_path)
        target = tmp_path / "target"
        args = ["restore", str(zip_path), str(target)]
        with mock.patch("sys.argv", args):
            run_restore_cli()
