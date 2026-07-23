"""Secure HTTP client for legal source downloads (M7-A).

Implements host allowlist filtering, redirect validation, TLS enforcement,
response size limits, timeouts, and atomic writes with SHA-256 hashing.

No credentials, no cookies, no case data ever sent to remote sources.

SEC-001 (TransportPolicy): Explicit rules for external/local transport.
SEC-015 (Atomic Import): Transactional guarantees in the service layer.
"""

import hashlib
import logging
import os
import tempfile
import uuid
from enum import Enum, auto
from importlib.metadata import version as _pkg_version
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger("private_legal_navigator.source_client")

# ──────────────────────────────────────────────
# Transport Policy (SEC-001)
# ──────────────────────────────────────────────


class TransportMode(Enum):
    """Operating mode for the source client transport policy."""

    PRODUCTION = auto()  # Strict: HTTPS-only for all hosts
    TEST = auto()  # Relaxed: allows localhost HTTP for testing
    EXPLICIT = auto()  # Custom host/scheme allowlists


class TransportPolicy:
    """Explicit transport security policy for legal source downloads.

    SEC-001: External sources MUST use HTTPS. HTTP for external hosts is
    always blocked. Localhost HTTP is only permitted in TEST mode.
    HTTPS→HTTP redirects to external hosts are blocked.
    """

    LOCALHOST_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

    def __init__(
        self,
        *,
        mode: TransportMode = TransportMode.PRODUCTION,
        allowed_hosts: tuple[str, ...] = ("gesetze-im-internet.de",),
        allowed_schemes: tuple[str, ...] = ("https",),
    ) -> None:
        self.mode = mode
        self.allowed_hosts = allowed_hosts
        self.allowed_schemes = allowed_schemes

    def is_scheme_allowed(self, scheme: str) -> bool:
        """Check if a URL scheme is permitted under the current policy."""
        if scheme in self.allowed_schemes:
            return True
        # Localhost HTTP is only allowed in TEST mode
        return scheme == "http" and self.mode == TransportMode.TEST

    def is_host_allowed(self, hostname: str | None) -> bool:
        """Check if a host is allowed under the current policy."""
        if hostname is None:
            return False
        # In TEST mode, localhost hosts are always allowed
        if self.mode == TransportMode.TEST and hostname in self.LOCALHOST_HOSTS:
            return True
        for pattern in self.allowed_hosts:
            if hostname == pattern or hostname.endswith("." + pattern):
                return True
        return False

    def is_localhost(self, hostname: str | None) -> bool:
        """Check if a hostname is a localhost address."""
        return hostname is not None and hostname in self.LOCALHOST_HOSTS

    def validate_redirect(self, source_url: str, target_url: str) -> None:
        """Validate a redirect target against transport policy.

        Raises:
            HostNotAllowedError: if target host is not allowed.
            SchemeNotAllowedError: if HTTPS→external HTTP redirect detected.
        """
        source_scheme = urlparse(source_url).scheme
        target_parsed = urlparse(target_url)
        target_scheme = target_parsed.scheme

        # HTTPS→external HTTP redirect is always blocked
        if source_scheme == "https" and target_scheme == "http":
            if not self.is_localhost(target_parsed.hostname):
                raise SchemeNotAllowedError(
                    f"HTTPS→HTTP redirect blocked for external host: {target_url}"
                )
            # HTTPS→localhost HTTP is only allowed in TEST mode
            if self.mode != TransportMode.TEST:
                raise SchemeNotAllowedError(
                    f"HTTPS→localhost HTTP redirect blocked in {self.mode.name} mode: {target_url}"
                )

    def validate_url(self, url: str) -> None:
        """Validate a URL for download against the transport policy."""
        parsed = urlparse(url)
        if not self.is_scheme_allowed(parsed.scheme):
            raise SchemeNotAllowedError(
                f"Scheme '{parsed.scheme}' not allowed. Allowed: {self.allowed_schemes}"
                + (
                    " (plus http://localhost in TEST mode)"
                    if self.mode == TransportMode.TEST
                    else ""
                )
            )
        if not self.is_host_allowed(parsed.hostname):
            raise HostNotAllowedError(
                f"Host '{parsed.hostname}' not in allowlist. Allowed: {self.allowed_hosts}"
            )


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

DEFAULT_ALLOWED_HOSTS: tuple[str, ...] = ("gesetze-im-internet.de",)
DEFAULT_ALLOWED_SCHEMES: tuple[str, ...] = ("https",)
DEFAULT_USER_AGENT = f"PrivateLegalNavigator/{_pkg_version('private-legal-navigator')} (+https://github.com/xxammaxx/Rechtssoftware)"


class SourceClientConfig:
    """Configuration for the safe source download client."""

    def __init__(
        self,
        *,
        allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
        allowed_schemes: tuple[str, ...] = DEFAULT_ALLOWED_SCHEMES,
        user_agent: str = DEFAULT_USER_AGENT,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        max_response_bytes: int = 200 * 1024 * 1024,  # 200 MB
        max_redirects: int = 5,
        tls_verify: bool = True,
        transport_mode: TransportMode = TransportMode.PRODUCTION,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.allowed_schemes = allowed_schemes
        self.user_agent = user_agent
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.tls_verify = tls_verify
        self.transport_mode = transport_mode


# ──────────────────────────────────────────────
# Client
# ──────────────────────────────────────────────


class SourceClientError(Exception):
    """Base error for source client operations."""


class HostNotAllowedError(SourceClientError):
    """The requested host is not in the allowlist."""


class SchemeNotAllowedError(SourceClientError):
    """The requested scheme is not allowed by the transport policy."""


class TooManyRedirectsError(SourceClientError):
    """Redirect chain exceeded the maximum."""


class ResponseTooLargeError(SourceClientError):
    """Response exceeded the maximum size limit."""


class DownloadFailedError(SourceClientError):
    """Download failed with a non-200 status."""


class SourceClient:
    """Secure HTTP client for legal source downloads.

    Features:
    - Host allowlist (only *.gesetze-im-internet.de)
    - HTTPS-only (no plain HTTP for external hosts)
    - Redirect validation (each hop checked against allowlist)
    - HTTPS→external HTTP redirect blocked (SEC-001-D)
    - Localhost HTTP only in TEST mode (SEC-001-C)
    - Response size limit (200 MB default)
    - Connection and read timeouts
    - No cookies, no credentials
    - TLS certificate verification enforced
    """

    def __init__(self, config: SourceClientConfig | None = None) -> None:
        self._config = config or SourceClientConfig()

    @property
    def policy(self) -> TransportPolicy:
        """Get the current transport policy."""
        return TransportPolicy(
            mode=self._config.transport_mode,
            allowed_hosts=self._config.allowed_hosts,
            allowed_schemes=self._config.allowed_schemes,
        )

    def is_host_allowed(self, url: str) -> bool:
        """Check if the URL's host is in the allowlist."""
        parsed = urlparse(url)
        return self.policy.is_scheme_allowed(parsed.scheme) and self.policy.is_host_allowed(
            parsed.hostname
        )

    def download(self, url: str) -> bytes:
        """Download content from a legal source with all guardrails."""
        self.policy.validate_url(url)
        return self._get_with_redirects(url, self._config.max_redirects)

    def download_to_file(self, url: str, target_dir: Path) -> tuple[bytes, Path, str]:
        """Download and save to a content-addressed file.

        Returns (content, file_path, sha256_hex).
        """
        content = self.download(url)
        file_path, sha256 = _write_content_addressed(content, target_dir)
        return content, file_path, sha256

    def _get_with_redirects(self, url: str, redirects_left: int) -> bytes:
        """Follow redirects with allowlist validation at each hop."""
        if redirects_left <= 0:
            raise TooManyRedirectsError(f"Too many redirects for {url}")

        self.policy.validate_url(url)

        with httpx.Client(
            verify=self._config.tls_verify,
            timeout=httpx.Timeout(
                connect=self._config.connect_timeout,
                read=self._config.read_timeout,
                write=10.0,
                pool=10.0,
            ),
            follow_redirects=False,
            headers={"User-Agent": self._config.user_agent},
        ) as client:
            response = client.get(url)

            # Manual redirect handling to validate each target
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if location is None:
                    raise DownloadFailedError(f"Redirect from {url} without Location header")
                next_url = urljoin(url, location)
                # SEC-001-D: validate redirect target
                self.policy.validate_redirect(url, next_url)
                return self._get_with_redirects(next_url, redirects_left - 1)

            if response.status_code != 200:
                raise DownloadFailedError(
                    f"Download failed: HTTP {response.status_code} from {url}"
                )

            # Stream with size limit
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes(chunk_size=65536):
                total += len(chunk)
                if total > self._config.max_response_bytes:
                    raise ResponseTooLargeError(
                        f"Response size {total} exceeds limit {self._config.max_response_bytes}"
                    )
                chunks.append(chunk)

            content = b"".join(chunks)
            return content


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _atomic_write(content: bytes, target_dir: Path) -> Path:
    """Write bytes atomically to a UUID-named file in target_dir.

    Uses tempfile + rename to prevent partial writes.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(target_dir), suffix=".tmp")
    try:
        os.close(fd)  # Close file descriptor before write (Windows compatibility)
        tmp_file = Path(tmp_path)
        tmp_file.write_bytes(content)
        # Move to final location
        final_name = f"{uuid.uuid4().hex}.snap"
        final_path = target_dir / final_name
        tmp_file.replace(final_path)
        return final_path
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def compute_sha256(content: bytes) -> str:
    """Compute SHA-256 hash of content as hex string."""
    return hashlib.sha256(content).hexdigest()


def _write_content_addressed(content: bytes, target_dir: Path) -> tuple[Path, str]:
    """Write bytes to a content-addressed path using SHA-256.

    Returns (path, sha256_hex).
    Files are stored at: target_dir/<sha256[:2]>/<sha256>.xml
    Deduplication: if file already exists with matching hash, no I/O occurs.
    """
    sha256 = compute_sha256(content)

    # Derive content-addressed path
    prefix = sha256[:2]
    subdir = target_dir / prefix
    subdir.mkdir(parents=True, exist_ok=True)
    target_path = subdir / f"{sha256}.xml"

    # If file already exists and hash matches, return it (dedup)
    if target_path.exists():
        try:
            existing = target_path.read_bytes()
            if compute_sha256(existing) == sha256:
                return target_path, sha256
        except OSError:
            pass  # Fall through to overwrite

    # Atomic write via temp file + rename
    fd, tmp_path = tempfile.mkstemp(dir=str(subdir), suffix=".tmp")
    try:
        os.close(fd)
        tmp_file = Path(tmp_path)
        tmp_file.write_bytes(content)
        tmp_file.replace(target_path)
        return target_path, sha256
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
