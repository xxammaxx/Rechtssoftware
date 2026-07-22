"""Secure HTTP client for legal source downloads (M7-A).

Implements host allowlist filtering, redirect validation, TLS enforcement,
response size limits, timeouts, and atomic writes with SHA-256 hashing.

No credentials, no cookies, no case data ever sent to remote sources.
"""

import hashlib
import logging
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger("private_legal_navigator.source_client")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

DEFAULT_ALLOWED_HOSTS: tuple[str, ...] = ("gesetze-im-internet.de",)

DEFAULT_ALLOWED_SCHEMES: tuple[str, ...] = ("https",)

DEFAULT_USER_AGENT = "PrivateLegalNavigator/0.2.0 (+https://github.com/xxammaxx/Rechtssoftware)"


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
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.allowed_schemes = allowed_schemes
        self.user_agent = user_agent
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.tls_verify = tls_verify


# ──────────────────────────────────────────────
# Client
# ──────────────────────────────────────────────


class SourceClientError(Exception):
    """Base error for source client operations."""


class HostNotAllowedError(SourceClientError):
    """The requested host is not in the allowlist."""


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
    - HTTPS-only (no plain HTTP)
    - Redirect validation (each hop checked against allowlist)
    - Response size limit (200 MB default)
    - Connection and read timeouts
    - No cookies, no credentials
    - TLS certificate verification enforced
    """

    def __init__(self, config: SourceClientConfig | None = None) -> None:
        self._config = config or SourceClientConfig()

    def is_host_allowed(self, url: str) -> bool:
        """Check if the URL's host is in the allowlist."""
        parsed = urlparse(url)
        if parsed.scheme not in self._config.allowed_schemes:
            return False
        hostname = parsed.hostname
        if hostname is None:
            return False
        for pattern in self._config.allowed_hosts:
            if hostname == pattern or hostname.endswith("." + pattern):
                return True
        return False

    def download(self, url: str) -> bytes:
        """Download content from a legal source with all guardrails."""
        if not self.is_host_allowed(url):
            raise HostNotAllowedError(f"Host not in allowlist: {urlparse(url).hostname}")
        return self._get_with_redirects(url, self._config.max_redirects)

    def download_to_file(self, url: str, target_dir: Path) -> tuple[bytes, Path, str]:
        """Download and save to a file atomically.

        Returns (content, file_path, sha256_hex).
        """
        content = self.download(url)
        sha256 = hashlib.sha256(content).hexdigest()
        file_path = _atomic_write(content, target_dir)
        return content, file_path, sha256

    def _get_with_redirects(self, url: str, redirects_left: int) -> bytes:
        """Follow redirects with allowlist validation at each hop."""
        if redirects_left <= 0:
            raise TooManyRedirectsError(f"Too many redirects for {url}")

        if not self.is_host_allowed(url):
            raise HostNotAllowedError(f"Host not in allowlist: {urlparse(url).hostname}")

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
