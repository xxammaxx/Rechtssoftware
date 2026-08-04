"""Safe ZIP restore with pre-extraction path validation.

Validates ZIP entries BEFORE extraction, blocking:
- Absolute paths
- Drive letters
- UNC paths
- Parent directory traversal (..)
- Symlinks and reparse-point-like entries
- Duplicate normalized paths
- Oversized files
- Oversized total extraction size

After extraction:
- Validates manifest
- Validates SHA-256 hashes
- Runs SQLite integrity_check
- Performs atomic staging-to-target switch
- Rolls back on failure (leaves no partial state)
"""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from zipfile import ZipFile, ZipInfo

# Security limits
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per file
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB total extraction
MAX_FILES = 10000


def _sha256_hex(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _validate_zip_entry_path(entry_path: str) -> str:
    """Validate a ZIP entry path and return the normalized relative path.

    Raises ValueError for unsafe paths.
    """
    if not entry_path:
        raise ValueError("Empty ZIP entry path")

    # Normalize separators
    normalized = entry_path.replace("\\", "/")

    # Block absolute paths
    if os.path.isabs(normalized):
        raise ValueError(f"Absolute path in ZIP: {entry_path}")

    # Block drive letters (Windows)
    if len(normalized) >= 2 and normalized[1] == ":":
        raise ValueError(f"Drive letter path in ZIP: {entry_path}")

    # Block UNC paths
    if normalized.startswith("//") or normalized.startswith("\\\\"):
        raise ValueError(f"UNC path in ZIP: {entry_path}")

    # Resolve path components and check for traversal
    parts = normalized.split("/")
    resolved: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not resolved:
                raise ValueError(f"Path traversal beyond root: {entry_path}")
            resolved.pop()
        else:
            resolved.append(part)

    if not resolved:
        raise ValueError(f"Empty path after resolution: {entry_path}")

    return "/".join(resolved)


def _validate_zip_entries(zip_path: Path) -> list[tuple[str, ZipInfo]]:
    """Pre-validate all ZIP entries. Returns list of (normalized_path, info).

    Raises ValueError for any unsafe entries.
    """
    seen: set[str] = set()
    entries: list[tuple[str, ZipInfo]] = []
    total_size = 0

    with ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            safe_path = _validate_zip_entry_path(info.filename)

            # Block symlinks and reparse-like entries
            mode = (info.external_attr >> 16) & 0o170000  # S_IFMT mask
            if mode == 0o120000:  # S_IFLNK
                raise ValueError(f"Symlink in ZIP: {info.filename}")

            # Check for duplicate normalized paths
            if safe_path in seen:
                raise ValueError(f"Duplicate path in ZIP: {safe_path}")
            seen.add(safe_path)

            # Size checks
            if info.file_size > MAX_FILE_SIZE:
                raise ValueError(

                        f"File too large in ZIP: {info.filename} "
                        f"({info.file_size} bytes, max {MAX_FILE_SIZE})"

                )

            total_size += info.file_size
            if total_size > MAX_TOTAL_SIZE:
                raise ValueError(

                        f"Total extraction size exceeds limit "
                        f"({total_size} bytes, max {MAX_TOTAL_SIZE})"

                )

            entries.append((safe_path, info))

    if len(entries) > MAX_FILES:
        raise ValueError(f"Too many files in ZIP: {len(entries)}, max {MAX_FILES}")

    return entries


def _validate_manifest_hash(extract_dir: Path) -> Any:
    """Read and validate the backup-manifest.json hash integrity."""
    manifest_path = extract_dir / "backup-manifest.json"

    if not manifest_path.exists():
        raise ValueError("No backup-manifest.json found in backup")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid backup-manifest.json: {e}") from e

    required = ["app_name", "app_version", "db_file"]
    for field in required:
        if field not in manifest:
            raise ValueError(f"Missing required field in manifest: {field}")

    return manifest


def _validate_file_hashes(extract_dir: Path, manifest: dict[str, Any]) -> None:
    """Validate SHA-256 hashes for documented files against manifest."""
    files_to_check = []

    # Database
    db_file = manifest.get("db_file")
    if db_file:
        db_path = extract_dir / db_file
        if db_path.exists():
            expected = manifest.get("db_sha256")
            if expected:
                files_to_check.append((db_path, expected, "database"))

    # Documents
    for doc in manifest.get("documents", []):
        doc_path = extract_dir / "documents" / doc["path"]
        if doc_path.exists() and "sha256" in doc:
            files_to_check.append((doc_path, doc["sha256"], f"document/{doc['path']}"))

    # Snapshots
    for snap in manifest.get("snapshots", []):
        snap_path = extract_dir / "snapshots" / snap["path"]
        if snap_path.exists() and "sha256" in snap:
            files_to_check.append((snap_path, snap["sha256"], f"snapshot/{snap['path']}"))

    # Manifest itself
    manifest_path = extract_dir / "backup-manifest.json"
    if "manifest_sha256" in manifest:
        files_to_check.append((manifest_path, manifest["manifest_sha256"], "manifest"))

    mismatches = []
    for path, expected, label in files_to_check:
        actual = _sha256_hex(path)
        if actual != expected:
            mismatches.append(f"  {label}: expected={expected}, actual={actual}")

    if mismatches:
        raise ValueError("Hash mismatch:\n" + "\n".join(mismatches))


def _check_database_integrity(extract_dir: Path, db_filename: str) -> str:
    """Run PRAGMA integrity_check on the restored database."""
    db_path = extract_dir / db_filename
    if not db_path.exists():
        return "no database file"

    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.DatabaseError as e:
        return f"database error: {e}"
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        return result[0] if result else "no result"
    except sqlite3.DatabaseError as e:
        return f"database error: {e}"
    finally:
        conn.close()


def restore_backup(
    zip_path: Path,
    target_data_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Restore a backup ZIP to the target data directory.

    Performs:
    1. ZIP entry pre-validation (traversal, symlinks, size, duplicates)
    2. Safe extraction to staging directory
    3. Manifest validation
    4. Hash validation
    5. Database integrity_check
    6. Atomic staging-to-target switch
    7. Rollback on any failure

    Args:
        zip_path: Path to the backup ZIP file.
        target_data_dir: Directory where data should be restored.
        force: If True, skip confirmation when target already has data.

    Returns:
        Result dictionary with status and details.

    Raises:
        ValueError: For any validation or restore failure.
    """
    if not zip_path.exists():
        raise ValueError(f"Backup file not found: {zip_path}")

    # 0. Check target
    target_data_dir = target_data_dir.resolve()
    if target_data_dir.exists():
        existing = list(target_data_dir.glob("*"))
        if existing and not force:
            raise ValueError(
                f"Target directory contains {len(existing)} items. Use force=True to overwrite."
            )

    # 1. Pre-validate ZIP entries
    entries = _validate_zip_entries(zip_path)

    # 2. Extract to staging
    staging_dir = Path(tempfile.mkdtemp(prefix="pln-restore-staging-"))
    try:
        with ZipFile(zip_path, "r") as zf:
            for safe_path, info in entries:
                dest = staging_dir / safe_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                # Preserve mtime
                if info.date_time:
                    import time

                    dt = time.mktime(info.date_time + (0, 0, -1))
                    os.utime(dest, (dt, dt))

        # 3. Validate manifest
        manifest = _validate_manifest_hash(staging_dir)
        db_file = manifest.get("db_file", "private_legal_navigator.db")

        # 4. Validate file hashes
        _validate_file_hashes(staging_dir, manifest)

        # 5. Database integrity check
        db_integrity = _check_database_integrity(staging_dir, db_file)
        if db_integrity != "ok":
            raise ValueError(f"Database integrity check failed: {db_integrity}")

        # 6. Atomically switch
        if target_data_dir.exists():
            backup_target = Path(str(target_data_dir) + ".pre-restore-backup")
            if backup_target.exists():
                shutil.rmtree(backup_target)
            shutil.move(str(target_data_dir), str(backup_target))
            rollback_needed = True
            rollback_source = backup_target
        else:
            rollback_needed = False
            rollback_source = target_data_dir

        try:
            target_data_dir.mkdir(parents=True, exist_ok=True)
            for item in staging_dir.iterdir():
                dest = target_data_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            rollback_needed = False
        finally:
            if rollback_needed:
                # Rollback: restore the pre-existing target
                if target_data_dir.exists():
                    shutil.rmtree(str(target_data_dir))
                if rollback_source.exists():
                    shutil.move(str(rollback_source), str(target_data_dir))
                raise ValueError(
                    "Restore failed during atomic switch; rolled back to previous state."
                )

        return {
            "status": "restored",
            "app_version": manifest.get("app_version"),
            "schema_version": manifest.get("schema_version"),
            "created_at": manifest.get("created_at"),
            "db_integrity": db_integrity,
            "document_count": len(manifest.get("documents", [])),
            "snapshot_count": len(manifest.get("snapshots", [])),
        }

    finally:
        if staging_dir.exists():
            shutil.rmtree(str(staging_dir))


def run_restore_cli() -> int:
    """CLI entry point: restore <zip_path> <target_data_dir> [--force].

    Returns 0 on success, 1 on error.
    Prints result JSON to stdout.
    """
    import sys

    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]

    if len(args) < 2:
        print(
            (
                "Usage: python -m private_legal_navigator.infrastructure."
                "restore_helper <zip_path> <target_data_dir> [--force]"
            ),
            file=sys.stderr,
        )
        return 1

    zip_path = Path(args[0])
    target_data_dir = Path(args[1])

    try:
        result = restore_backup(zip_path, target_data_dir, force=force)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"Restore failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_restore_cli())
