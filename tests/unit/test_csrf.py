"""Unit tests for CSRF token service."""

import time

import pytest

from private_legal_navigator.middleware.csrf import CsrfConfig, CsrfTokenService


@pytest.fixture
def csrf_service() -> CsrfTokenService:
    config = CsrfConfig(secret="test-secret-key-for-csrf-tests", token_lifetime_seconds=3600)
    return CsrfTokenService(config)


class TestCsrfTokenGeneration:
    """Tests for CSRF token generation."""

    def test_csrf_token_is_cryptographically_random(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        assert len(nonce) == 64  # 32 bytes hex = 64 chars

        # Multiple calls should produce different nonces
        nonce2 = csrf_service.generate_browser_nonce()
        assert nonce != nonce2

    def test_form_token_is_not_empty(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        token = csrf_service.generate_form_token(nonce)
        assert token
        assert ":" in token

    def test_idempotency_key_is_random(self) -> None:
        key1 = CsrfTokenService.generate_idempotency_key()
        key2 = CsrfTokenService.generate_idempotency_key()
        assert len(key1) == 32
        assert key1 != key2


class TestCsrfValidation:
    """Tests for CSRF token validation."""

    def test_valid_token_passes(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        token = csrf_service.generate_form_token(nonce)
        assert csrf_service.validate_token(token, nonce) is True

    def test_missing_token_fails(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        assert csrf_service.validate_token("", nonce) is False

    def test_modified_token_fails(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        token = csrf_service.generate_form_token(nonce)
        # Flip a character in the signature
        modified = token[:-1] + ("0" if token[-1] != "0" else "1")
        assert csrf_service.validate_token(modified, nonce) is False

    def test_wrong_nonce_fails(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        token = csrf_service.generate_form_token(nonce)
        other_nonce = csrf_service.generate_browser_nonce()
        assert csrf_service.validate_token(token, other_nonce) is False

    def test_expired_token_fails(self) -> None:
        config = CsrfConfig(secret="key", token_lifetime_seconds=1)
        svc = CsrfTokenService(config)
        nonce = svc.generate_browser_nonce()
        token = svc.generate_form_token(nonce)
        # Wait for token to expire
        time.sleep(1.1)
        assert svc.validate_token(token, nonce) is False

    def test_token_with_extra_separators_fails(self, csrf_service: CsrfTokenService) -> None:
        assert csrf_service.validate_token("a:b:c:d", "nonce") is False

    def test_malformed_token_fails(self, csrf_service: CsrfTokenService) -> None:
        assert csrf_service.validate_token("garbage", "nonce") is False
        assert csrf_service.validate_token("not:a:token:structure", "nonce") is False


class TestCsrfSecurityProperties:
    """Tests for CSRF security properties."""

    def test_same_nonce_produces_reproducible_tokens_within_same_second(
        self, csrf_service: CsrfTokenService
    ) -> None:
        """Same nonce within same timestamp window produces the same token."""
        nonce = csrf_service.generate_browser_nonce()
        token1 = csrf_service.generate_form_token(nonce)
        token2 = csrf_service.generate_form_token(nonce)
        # Within same second, tokens should be identical (same timestamp + same nonce)
        assert token1 == token2

    def test_different_services_with_different_secrets_produce_incompatible_tokens(self) -> None:
        s1 = CsrfTokenService(CsrfConfig(secret="secret-a"))
        s2 = CsrfTokenService(CsrfConfig(secret="secret-b"))
        nonce = s1.generate_browser_nonce()
        token = s1.generate_form_token(nonce)
        assert s2.validate_token(token, nonce) is False

    def test_browser_nonce_length_is_sufficient(self, csrf_service: CsrfTokenService) -> None:
        nonce = csrf_service.generate_browser_nonce()
        # 256 bits of entropy (32 bytes × 8 = 256 bits)
        assert len(nonce) >= 64
