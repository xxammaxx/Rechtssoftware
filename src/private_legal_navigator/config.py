"""Application configuration via environment variables."""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path


def _generate_csrf_secret() -> str:
    """Generate a random CSRF secret on first access.

    Persisted across app restarts via environment variable.
    If not set, generates a new secret per process (acceptable for local use).
    """
    env_secret = os.environ.get("PLN_CSRF_SECRET")
    if env_secret:
        return env_secret
    return secrets.token_hex(32)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Environment variables:
        PLN_DATA_DIR: Directory for the SQLite database (default: ~/.private-legal-navigator)
        PLN_HOST: Host to bind to (default: 127.0.0.1)
        PLN_PORT: Port to listen on (default: 8000)
        PLN_CSRF_SECRET: Shared secret for CSRF token signing (auto-generated if not set)
        PLN_ALLOWED_HOSTS: Comma-separated list of allowed Host header values
    """

    data_dir: Path = field(default_factory=lambda: Settings._default_data_dir())
    host: str = field(default_factory=lambda: os.environ.get("PLN_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("PLN_PORT", "8000")))
    csrf_secret: str = field(default_factory=_generate_csrf_secret)

    @property
    def database_path(self) -> Path:
        """Full path to the SQLite database file."""
        return self.data_dir / "private_legal_navigator.db"

    @property
    def allowed_hosts(self) -> list[str]:
        """Explicit host allowlist derived from host and port.

        Returns exact host:port combinations. No wildcards, no subdomains.
        """
        env_hosts = os.environ.get("PLN_ALLOWED_HOSTS")
        if env_hosts:
            return [h.strip() for h in env_hosts.split(",") if h.strip()]

        hosts: list[str] = []
        hosts.append(f"127.0.0.1:{self.port}")
        hosts.append(f"localhost:{self.port}")
        # IPv6 loopback optional
        hosts.append(f"[::1]:{self.port}")
        return hosts

    @property
    def template_dir(self) -> Path:
        """Absolute path to the Jinja2 template directory."""
        return Path(__file__).parent / "presentation" / "templates"

    @property
    def static_dir(self) -> Path:
        """Absolute path to the static assets directory."""
        return Path(__file__).parent / "presentation" / "static"

    @staticmethod
    def _default_data_dir() -> Path:
        """Default data directory: PLN_DATA_DIR env var or ~/.private-legal-navigator."""
        if env_dir := os.environ.get("PLN_DATA_DIR"):
            return Path(env_dir)
        return Path.home() / ".private-legal-navigator"
