"""Local filesystem implementation of FileStorage."""

from pathlib import Path

from private_legal_navigator.application.file_storage import FileStorage


class LocalFileStorage(FileStorage):
    """Stores files in a local directory.

    Files are stored with UUID-based names (e.g., {uuid}.bin) to prevent
    path traversal and filename conflicts.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_path: str) -> Path:
        """Resolve storage path safely — only filename, no subdirectories."""
        # Extract just the filename to prevent path traversal
        safe_name = Path(storage_path).name
        return self._base_dir / safe_name

    def store(self, storage_path: str, content: bytes) -> None:
        """Write file content to disk."""
        target = self._resolve(storage_path)
        target.write_bytes(content)

    def retrieve(self, storage_path: str) -> bytes:
        """Read file content from disk."""
        target = self._resolve(storage_path)
        if not target.exists():
            raise FileNotFoundError("Datei nicht gefunden")
        return target.read_bytes()

    def exists(self, storage_path: str) -> bool:
        """Check if file exists."""
        return self._resolve(storage_path).exists()
