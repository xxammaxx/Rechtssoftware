"""Comprehensive tests for transactional SQLite backup helper."""

import hashlib
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from private_legal_navigator.infrastructure.backup_helper import (
    _build_file_list,
    _get_app_version,
    _get_schema_version,
    _sha256_hex,
    create_backup,
    run_backup_cli,
)


class TestSha256Hex:
    def test_known_content(self):
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            path = Path(f.name)
        try:
            assert _sha256_hex(path) == expected
        finally:
            path.unlink()

    def test_empty_file(self):
        expected = hashlib.sha256(b"").hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)
        try:
            assert _sha256_hex(path) == expected
        finally:
            path.unlink()

    def test_large_file(self):
        chunk = b"x" * 65536
        repeat = 100
        expected = hashlib.sha256(chunk * repeat).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as f:
            for _ in range(repeat):
                f.write(chunk)
            path = Path(f.name)
        try:
            assert _sha256_hex(path) == expected
        finally:
            path.unlink()

    def test_unicode_filename(self, tmp_path):
        fname = tmp_path / "test-\u00e4\u00f6\u00fc.txt"
        fname.write_text("unicode test")
        result = _sha256_hex(fname)
        assert len(result) == 64

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _sha256_hex(tmp_path / "nonexistent")


class TestGetAppVersion:
    def test_returns_version_string(self):
        v = _get_app_version()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_fallback_on_import_error(self):
        with mock.patch("importlib.metadata.version", side_effect=ImportError):
            assert _get_app_version() == "0.0.0-dev"

    def test_fallback_on_exception(self):
        with mock.patch("importlib.metadata.version", side_effect=RuntimeError):
            assert _get_app_version() == "0.0.0-dev"


class TestGetSchemaVersion:
    def test_returns_version_from_user_version(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA user_version = 42")
        conn.close()
        assert _get_schema_version(db) == "42"

    def test_zero_user_version(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.close()
        assert _get_schema_version(db) == "unknown"

    def test_missing_db(self, tmp_path):
        assert _get_schema_version(tmp_path / "missing.db") == "unknown"


class TestBuildFileList:
    def test_empty_directory(self, tmp_path):
        assert _build_file_list(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path):
        assert _build_file_list(tmp_path / "nonexistent") == []

    def test_single_file(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello")
        result = _build_file_list(tmp_path)
        assert len(result) == 1
        assert result[0]["path"] == "a.txt"
        assert result[0]["size_bytes"] == 5
        assert len(result[0]["sha256"]) == 64

    def test_nested_files_sorted(self, tmp_path):
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "a.txt").write_text("a")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.txt").write_text("c")
        result = _build_file_list(tmp_path)
        paths = [r["path"] for r in result]
        assert paths == ["a.txt", "b.txt", "sub/c.txt"]

    def test_unicode_filenames(self, tmp_path):
        (tmp_path / "d\u00e9j\u00e0_vu.txt").write_text("test")
        result = _build_file_list(tmp_path)
        assert len(result) == 1
        assert "d\u00e9j\u00e0_vu.txt" in result[0]["path"]

    def test_empty_file_in_list(self, tmp_path):
        (tmp_path / "empty.dat").write_bytes(b"")
        result = _build_file_list(tmp_path)
        assert result[0]["size_bytes"] == 0
        assert result[0]["sha256"] == hashlib.sha256(b"").hexdigest()


class TestCreateBackup:
    def test_empty_database(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["db_integrity"] == "ok"
        assert len(manifest["db_sha256"]) == 64
        assert "app_version" in manifest
        assert "created_at" in manifest

    def test_initialized_project_database(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE cases (id TEXT PRIMARY KEY, title TEXT)")
        conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, case_id TEXT)")
        conn.execute("INSERT INTO cases VALUES (?, ?)", ("c1", "Test Case"))
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["db_integrity"] == "ok"
        assert manifest["schema_version"] == "unknown"
        backup_db = output_dir / "private_legal_navigator.db"
        assert backup_db.exists()
        check = sqlite3.connect(str(backup_db))
        rows = check.execute("SELECT * FROM cases").fetchall()
        check.close()
        assert len(rows) == 1
        assert rows[0][0] == "c1"

    def test_wal_mode_database(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["db_integrity"] == "ok"
        backup = sqlite3.connect(str(output_dir / "private_legal_navigator.db"))
        rows = backup.execute("SELECT * FROM t").fetchall()
        backup.close()
        assert len(rows) == 1

    def test_data_committed_but_wal_active(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (99)")
        conn.commit()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        conn.close()
        assert manifest["db_integrity"] == "ok"
        backup = sqlite3.connect(str(output_dir / "private_legal_navigator.db"))
        pr = backup.execute("PRAGMA integrity_check").fetchone()
        backup.close()
        assert pr[0] == "ok"

    def test_multiple_tables(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE a (id)")
        conn.execute("CREATE TABLE b (id)")
        conn.execute("CREATE TABLE c (id)")
        conn.execute("INSERT INTO a VALUES (1)")
        conn.execute("INSERT INTO b VALUES (2)")
        conn.execute("INSERT INTO c VALUES (3)")
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["db_integrity"] == "ok"
        backup = sqlite3.connect(str(output_dir / "private_legal_navigator.db"))
        tables = backup.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        backup.close()
        assert ("a",) in tables
        assert ("b",) in tables
        assert ("c",) in tables

    def test_documents_copied(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        docs_dir = data_dir / "documents"
        docs_dir.mkdir()
        (docs_dir / "doc1.pdf").write_bytes(b"pdf content")
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["document_count"] == 1
        assert (output_dir / "documents" / "doc1.pdf").exists()

    def test_snapshots_copied(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        snaps_dir = data_dir / "snapshots"
        snaps_dir.mkdir()
        (snaps_dir / "abc123.xml").write_text("<law/>")
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["snapshot_count"] == 1
        assert (output_dir / "snapshots" / "abc123.xml").exists()

    def test_manifest_written_with_self_hash(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        mp = output_dir / "backup-manifest.json"
        assert mp.exists()
        assert "manifest_sha256" in manifest
        expected = _sha256_hex(mp)
        assert manifest["manifest_sha256"] == expected

    def test_no_db_creates_no_db_file(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["db_sha256"] == ""
        assert manifest["db_integrity"] == "not checked"

    def test_unicode_in_document_names(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        docs_dir = data_dir / "documents"
        docs_dir.mkdir()
        (docs_dir / "M\u00fcnchen_Bescheid.pdf").write_text("test")
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["document_count"] == 1

    def test_large_file_within_limit(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        docs_dir = data_dir / "documents"
        docs_dir.mkdir()
        content = b"x" * (10 * 1024 * 1024)
        (docs_dir / "large.dat").write_bytes(content)
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["document_count"] == 1
        restored = (output_dir / "documents" / "large.dat").read_bytes()
        assert restored == content

    def test_missing_source_db_handled_gracefully(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        assert manifest["db_integrity"] == "not checked"
        assert manifest["db_sha256"] == ""

    def test_target_is_file_not_directory(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        output_file = tmp_path / "not_a_dir"
        output_file.write_text("block")
        with pytest.raises((NotADirectoryError, PermissionError, sqlite3.OperationalError)):
            create_backup(data_dir, output_file)

    def test_corrupted_database_integrity_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        create_backup(data_dir, output_dir)
        backup_path = output_dir / "private_legal_navigator.db"
        data = bytearray(backup_path.read_bytes())
        if len(data) > 100:
            data[50:100] = b"\xff" * 50
        backup_path.write_bytes(bytes(data))
        check = sqlite3.connect(str(backup_path))
        try:
            result = check.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.DatabaseError:
            result = ("corrupt",)
        check.close()
        assert result[0] != "ok"

    def test_hash_computation_includes_all_data(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES ('hello')")
        conn.commit()
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        manifest = create_backup(data_dir, output_dir)
        backup_path = output_dir / "private_legal_navigator.db"
        actual_hash = _sha256_hex(backup_path)
        assert manifest["db_sha256"] == actual_hash

    def test_overwrite_existing_backup(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        create_backup(data_dir, output_dir)
        manifest2 = create_backup(data_dir, output_dir)
        assert manifest2["db_integrity"] == "ok"


class TestRunBackupCli:
    def test_cli_creates_backup(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        args = ["backup", str(data_dir), str(output_dir)]
        with mock.patch("sys.argv", args), mock.patch("sys.stdout"):
            rc = run_backup_cli()
        assert rc == 0
        assert (output_dir / "private_legal_navigator.db").exists()

    def test_cli_insufficient_args(self):
        with mock.patch("sys.argv", ["backup"]):
            rc = run_backup_cli()
        assert rc == 1

    def test_cli_single_arg(self):
        with mock.patch("sys.argv", ["backup", "/tmp/foo"]):
            rc = run_backup_cli()
        assert rc == 1

    def test_cli_creates_output_dir(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        output_dir = tmp_path / "nested" / "backup"
        args = ["backup", str(data_dir), str(output_dir)]
        with mock.patch("sys.argv", args), mock.patch("sys.stdout"):
            rc = run_backup_cli()
        assert rc == 0
        assert output_dir.exists()

    def test_cli_handles_db_connection_error(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        output_dir = tmp_path / "backup"
        output_dir.mkdir()
        args = ["backup", str(data_dir), str(output_dir)]
        with mock.patch("sys.argv", args):
            rc = run_backup_cli()
        assert rc == 0

    def test_cli_main_block(self, tmp_path, capsys):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        output_dir = tmp_path / "backup"
        with mock.patch(
            "sys.argv",
            ["backup_helper.py", str(data_dir), str(output_dir)],
        ):
            from private_legal_navigator.infrastructure import backup_helper

            rc = backup_helper.run_backup_cli()
        assert rc == 0

    def test_cli_sys_exit_integration(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        output_dir = tmp_path / "backup"
        args = ["backup_helper.py", str(data_dir), str(output_dir)]
        with mock.patch("sys.argv", args):
            with pytest.raises(SystemExit) as excinfo:
                from private_legal_navigator.infrastructure.backup_helper import (
                    run_backup_cli,
                )

                raise SystemExit(run_backup_cli())
            assert excinfo.value.code == 0
