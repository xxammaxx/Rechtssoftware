"""Application configuration via environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Environment variables:
        PLN_DATA_DIR: Directory for the SQLite database (default: ~/.private-legal-navigator)
        PLN_HOST: Host to bind to (default: 127.0.0.1)
        PLN_PORT: Port to listen on (default: 8000)
    """

    data_dir: Path = field(default_factory=lambda: Settings._default_data_dir())
    host: str = field(default_factory=lambda: os.environ.get("PLN_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("PLN_PORT", "8000")))

    @property
    def database_path(self) -> Path:
        """Full path to the SQLite database file."""
        return self.data_dir / "private_legal_navigator.db"

    @staticmethod
    def _default_data_dir() -> Path:
        """Default data directory: PLN_DATA_DIR env var or ~/.private-legal-navigator."""
        if env_dir := os.environ.get("PLN_DATA_DIR"):
            return Path(env_dir)
        return Path.home() / ".private-legal-navigator"
