"""CSRF protection service for M6-UI.

Implements token-based CSRF protection for future POST routes.
Uses HMAC-signed tokens with browser nonce cookies.

This module provides the TOKEN SERVICE only.
It is NOT wired into any middleware or route in Slice 1
(no POST routes exist yet).
"""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CsrfConfig:
    """Configuration for CSRF token generation and validation."""

    secret: str
    token_lifetime_seconds: int = 3600  # 1 hour


class CsrfTokenService:
    """Generates and validates CSRF tokens.

    Token format: base64(nonce + ":" + hmac_signature)
    Bound to a browser nonce stored in a cookie.

    Token rotation: new token generated on first access per nonce.
    Validation uses constant-time comparison.
    """

    def __init__(self, config: CsrfConfig) -> None:
        self._config = config
        self._key = config.secret.encode("utf-8")

    def generate_browser_nonce(self) -> str:
        """Generate a cryptographically random browser nonce.

        Returns a hex string suitable for use as a cookie value.
        """
        return secrets.token_hex(32)

    def generate_form_token(self, browser_nonce: str) -> str:
        """Generate a time-bound, signed form token for a browser nonce.

        Args:
            browser_nonce: The nonce from the browser's CSRF cookie.

        Returns:
            A base64-encoded token containing timestamp + nonce + HMAC.
        """
        now = int(time.time())
        payload = f"{now}:{browser_nonce}"
        signature = self._sign(payload)
        token_raw = f"{now}:{browser_nonce}:{signature}"
        return token_raw

    def validate_token(self, form_token: str, browser_nonce: str) -> bool:
        """Validate a form token against a browser nonce.

        Uses constant-time comparison for the HMAC.

        Args:
            form_token: The token from the hidden form field.
            browser_nonce: The nonce from the browser's CSRF cookie.

        Returns:
            True if the token is valid, not expired, and bound to the nonce.
        """
        try:
            parts = form_token.split(":", 2)
            if len(parts) != 3:
                return False

            timestamp_str, token_nonce, signature = parts
            timestamp = int(timestamp_str)

            # Check expiry
            if time.time() - timestamp > self._config.token_lifetime_seconds:
                return False

            # Check nonce binding
            if not hmac.compare_digest(token_nonce, browser_nonce):
                return False

            # Verify signature
            expected_sig = self._sign(f"{timestamp_str}:{browser_nonce}")
            return hmac.compare_digest(signature, expected_sig)

        except (ValueError, TypeError):
            return False

    def _sign(self, payload: str) -> str:
        """Create an HMAC-SHA256 signature for a payload."""
        return hmac.new(
            self._key,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def generate_idempotency_key() -> str:
        """Generate a unique idempotency key for form submissions.

        Used to prevent duplicate processing of state-changing operations.
        """
        return secrets.token_hex(16)
