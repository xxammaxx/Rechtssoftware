"""Transactional SQLite backup with integrity verification.

Uses sqlite3.Connection.backup() for safe WAL-mode database backup.
Never uses plain file copy on potentially active WAL databases.
"""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _sha256_hex(file_path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _get_app_version() -> str:
    """Read application version from package metadata."""
    try:
        from importlib.metadata import version

        return version("private-legal-navigator")
    except Exception:
        return "0.0.0-dev"


def _get_schema_version(db_path: Path) -> str:
    """Read schema_version from a user_version pragma or fallback."""
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute("PRAGMA user_version").fetchone()
            if row and row[0]:
                return str(row[0])
        finally:
            conn.close()
    except Exception:
        pass
    return "unknown"


def _build_file_list(directory: Path) -> list[dict[str, Any]]:
    """Recursively build a manifest of all files in a directory."""
    files: list[dict[str, Any]] = []
    if not directory.exists():
        return files
    for entry in sorted(directory.rglob("*")):
        if entry.is_file():
            files.append(
                {
                    "path": str(entry.relative_to(directory)),
                    "size_bytes": entry.stat().st_size,
                    "sha256": _sha256_hex(entry),
                }
            )
    return files


def create_backup(
    data_dir: Path,
    output_dir: Path,
    db_filename: str = "private_legal_navigator.db",
) -> dict[str, Any]:
    """Create a transactional backup of the application data.

    Args:
        data_dir: Path to the PLN data directory.
        output_dir: Directory where backup files will be written (must exist).
        db_filename: Database filename within data_dir.

    Returns:
        Manifest dictionary with app version, schema version, file hashes,
        integrity_check result, and file lists.
    """
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    app_version = _get_app_version()

    db_path = data_dir / db_filename
    docs_dir = data_dir / "documents"
    snaps_dir = data_dir / "snapshots"

    # ── Database backup via SQLite Backup API ──
    db_backup_path = output_dir / db_filename
    db_integrity = "not checked"
    db_sha256 = ""
    schema_version = "unknown"

    if db_path.exists():
        src_conn = sqlite3.connect(str(db_path))
        try:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dst_conn = sqlite3.connect(str(db_backup_path))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
            db_sha256 = _sha256_hex(db_backup_path)

            # Integrity check on backup copy
            check_conn = sqlite3.connect(str(db_backup_path))
            try:
                result = check_conn.execute("PRAGMA integrity_check").fetchone()
                db_integrity = result[0] if result else "no result"
            finally:
                check_conn.close()

            schema_version = _get_schema_version(db_backup_path)
        finally:
            src_conn.close()

    # ── Documents and snapshots ──
    doc_manifest = _build_file_list(docs_dir) if docs_dir.exists() else []
    snap_manifest = _build_file_list(snaps_dir) if snaps_dir.exists() else []

    # Copy documents and snapshots into output_dir
    import shutil

    if docs_dir.exists():
        dest_docs = output_dir / "documents"
        if dest_docs.exists():
            shutil.rmtree(dest_docs)
        shutil.copytree(docs_dir, dest_docs, symlinks=False)
    if snaps_dir.exists():
        dest_snaps = output_dir / "snapshots"
        if dest_snaps.exists():
            shutil.rmtree(dest_snaps)
        shutil.copytree(snaps_dir, dest_snaps, symlinks=False)

    # ── Manifest ──
    manifest: dict[str, Any] = {
        "app_name": "PrivateLegalNavigator",
        "app_version": app_version,
        "schema_version": schema_version,
        "created_at": created_at,
        "db_sha256": db_sha256,
        "db_integrity": db_integrity,
        "db_file": db_filename,
        "document_count": len(doc_manifest),
        "snapshot_count": len(snap_manifest),
        "documents": doc_manifest,
        "snapshots": snap_manifest,
    }

    manifest_path = output_dir / "backup-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Append manifest itself to manifest
    manifest["manifest_sha256"] = _sha256_hex(manifest_path)

    return manifest


def run_backup_cli() -> int:
    """CLI entry point: backup <data_dir> <output_dir>.

    Returns 0 on success, 1 on error.
    Prints manifest JSON to stdout.
    """
    import sys

    if len(sys.argv) < 3:
        print(
            (
                "Usage: python -m private_legal_navigator.infrastructure."
                "backup_helper <data_dir> <output_dir>"
            ),
            file=sys.stderr,
        )
        return 1

    data_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        manifest = create_backup(data_dir, output_dir)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"Backup failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_backup_cli())
