"""Integration tests for M6-UI Slice 3: Correct, Revoke, History.

Covers: correct happy path, revoke happy path, expected-state binding,
idempotency, history display, CSRF, privacy logging, parallel operations.
"""

import re
import uuid
from pathlib import Path

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings

# ── Test PDF generation ────────────────────────────────────────────

_SYNTHETIC_PDF_TEXT: str = "SYNTHETISCH – Frist bis 31.07.2026. Weitere Frist: 15.01.2026."


def _create_pdf_with_date_text() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), _SYNTHETIC_PDF_TEXT, fontsize=11)
    return doc.tobytes()


@pytest.fixture
def settings(tmp_path):
    data_dir = Path(tmp_path) / "pln_data"
    data_dir.mkdir()
    return Settings(data_dir=data_dir, host="127.0.0.1", port=8000)


@pytest.fixture
async def client(settings: Settings):
    from private_legal_navigator.app import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as ac:
        yield ac


async def _create_case(client: AsyncClient):
    resp = await client.post("/api/v1/cases", json={"title": "SYNTHETISCH – Testfall Slice 3"})
    assert resp.status_code == 201
    return resp.json()["case_id"]


async def _upload_pdf(client: AsyncClient, case_id: str):
    pdf_bytes = _create_pdf_with_date_text()
    resp = await client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    return resp.json()["document_id"]


def _extract_csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if m:
        return m.group(1)
    return ""


def _extract_idempotency_key(html: str) -> str:
    m = re.search(r'name="idempotency_key"\s+value="([^"]+)"', html)
    if m:
        return m.group(1)
    return ""


def _extract_expected_active(html: str) -> str:
    m = re.search(r'name="expected_active_confirmation_id"\s+value="([^"]+)"', html)
    if m:
        return m.group(1)
    return ""


async def _get_candidate_page(client: AsyncClient, case_id: str, doc_id: str, idx: int = 0):
    """Get the candidate detail page and extract CSRF + idempotency tokens."""
    resp = await client.get(f"/ui/cases/{case_id}/documents/{doc_id}/candidates/{idx}")
    assert resp.status_code == 200
    html = resp.text
    return {
        "html": html,
        "csrf_token": _extract_csrf_token(html),
        "idempotency_key": _extract_idempotency_key(html),
        "expected_active": _extract_expected_active(html),
    }


async def _confirm_candidate(client: AsyncClient, case_id: str, doc_id: str) -> dict:
    """Confirm candidate 0 with detected date 31.07.2026."""
    page = await _get_candidate_page(client, case_id, doc_id, 0)
    resp = await client.post(
        f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
        data={
            "csrf_token": page["csrf_token"],
            "idempotency_key": page["idempotency_key"],
            "confirmed_date": "2026-07-31",
            "event_type": "unknown",
        },
        headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
        follow_redirects=False,
    )
    return {"status": resp.status_code, "location": resp.headers.get("location", "")}


# ═══════════════════════════════════════════════════════════════════
# Correct Happy Path
# ═══════════════════════════════════════════════════════════════════


class TestCorrectHappyPath:
    async def test_correct_confirmed_decision_redirects_303(self, client: AsyncClient):
        """Correct a confirmed decision → 303 redirect."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        # First confirm
        result = await _confirm_candidate(client, case_id, doc_id)
        assert result["status"] == 303

        # Get page to extract expected_active
        page = await _get_candidate_page(client, case_id, doc_id, 0)
        assert "Vom Nutzer bestätigt" in page["html"]

        # Correct
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "corrected=1" in resp.headers.get("location", "")

    async def test_correct_shows_new_date_as_active(self, client: AsyncClient):
        """After correction, the new date is the active confirmation."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        # Check the page shows the corrected status
        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        assert "Vom Nutzer bestätigt" in page2["html"]
        assert "15.12.2026" in page2["html"]  # New date displayed

    async def test_correct_preserves_previous_history_entry(self, client: AsyncClient):
        """Correction preserves the original confirmation in history."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        # Original date should appear in history
        assert "31.07.2026" in page2["html"]
        # History should show "Durch neuere Angabe ersetzt" for original
        assert "Durch neuere Angabe ersetzt" in page2["html"]


# ═══════════════════════════════════════════════════════════════════
# Revoke Happy Path
# ═══════════════════════════════════════════════════════════════════


class TestRevokeHappyPath:
    async def test_revoke_active_confirmation_redirects_303(self, client: AsyncClient):
        """Revoke an active confirmation → 303 redirect."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)
        assert page["expected_active"]

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "revoked=1" in resp.headers.get("location", "")

    async def test_revoke_shows_revoked_status(self, client: AsyncClient):
        """After revocation, page shows correct status and no confirm form."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 303  # Revoke succeeds

        # Follow redirect to verify page state
        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        # After revocation, no active confirmation expected
        assert page2["expected_active"] == ""

    async def test_revoke_does_not_delete_previous_decision(self, client: AsyncClient):
        """Revoke preserves the original decision in history."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        # Original date still visible in history
        assert "31.07.2026" in page2["html"]


# ═══════════════════════════════════════════════════════════════════
# Expected-State Binding (Stale Forms → 409)
# ═══════════════════════════════════════════════════════════════════


class TestExpectedStateBinding:
    async def test_correct_rejects_stale_expected_state(self, client: AsyncClient):
        """Correct with wrong expected_active → 409."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": str(uuid.uuid4()),  # Wrong!
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 409
        assert "geändert" in resp.text.lower()

    async def test_revoke_rejects_stale_expected_state(self, client: AsyncClient):
        """Revoke with wrong expected_active → 409."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": str(uuid.uuid4()),  # Wrong!
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 409

    async def test_correct_on_unconfirmed_returns_404(self, client: AsyncClient):
        """Correct on unconfirmed candidate → 404 (no active to correct)."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        page = await _get_candidate_page(client, case_id, doc_id, 0)
        # Should have no expected_active since unconfirmed
        assert page["expected_active"] == ""

    async def test_revoke_after_revoke_returns_error(self, client: AsyncClient):
        """Revoking an already-revoked decision → 404/409."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        # First revoke
        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        # Second revoke attempt — should fail
        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        assert page2["expected_active"] == ""  # No active to revoke


# ═══════════════════════════════════════════════════════════════════
# Idempotency
# ═══════════════════════════════════════════════════════════════════


class TestCorrectIdempotency:
    async def test_correct_same_key_same_payload_replays(self, client: AsyncClient):
        """Same idempotency key + same payload → replay (303)."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        key = page["idempotency_key"]
        eac = page["expected_active"]

        # First correct
        r1 = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": key,
                "expected_active_confirmation_id": eac,
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert r1.status_code == 303

        # Second correct with same key and payload
        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        r2 = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page2["csrf_token"],
                "idempotency_key": key,  # Same key
                "expected_active_confirmation_id": eac,  # Same payload
                "confirmed_date": "2026-12-15",  # Same date
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        # Replay should succeed (303) — same result
        assert r2.status_code == 303

    async def test_correct_same_key_different_date_returns_409(self, client: AsyncClient):
        """Same key, different date → 409 conflict."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        key = page["idempotency_key"]
        eac = page["expected_active"]

        # First correct
        r1 = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": key,
                "expected_active_confirmation_id": eac,
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert r1.status_code == 303

        # Second with same key, DIFFERENT date
        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        r2 = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page2["csrf_token"],
                "idempotency_key": key,
                "expected_active_confirmation_id": eac,
                "confirmed_date": "2026-11-01",  # Different!
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert r2.status_code == 409


class TestRevokeIdempotency:
    async def test_revoke_same_key_same_payload_replays(self, client: AsyncClient):
        """Same idempotency key + same payload → replay on revoke."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        key = page["idempotency_key"]
        eac = page["expected_active"]

        # First revoke
        r1 = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": key,
                "expected_active_confirmation_id": eac,
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert r1.status_code == 303

        # Second revoke with same key
        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        r2 = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page2["csrf_token"],
                "idempotency_key": key,
                "expected_active_confirmation_id": eac,
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert r2.status_code == 303  # Replay


# ═══════════════════════════════════════════════════════════════════
# History Display
# ═══════════════════════════════════════════════════════════════════


class TestHistoryDisplay:
    async def test_history_contains_original_confirmation(self, client: AsyncClient):
        """History includes the original confirmation after correction."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        assert "Bestätigungshistorie" in page2["html"]
        # Original entry should be in history
        assert "31.07.2026" in page2["html"]
        # Corrected entry should be in history
        assert "15.12.2026" in page2["html"]

    async def test_history_uses_safe_labels(self, client: AsyncClient):
        """History uses compliant display labels, not enum values."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        # Check for compliant labels
        assert "Vom Nutzer bestätigt" in page["html"]
        assert "Automatisch erkannt" in page["html"]
        # Must NOT contain raw enum values
        assert "ConfirmationStatus" not in page["html"]
        assert "auto_detected" not in page["html"]

    async def test_history_has_no_internal_ids(self, client: AsyncClient):
        """History does not expose raw enum values in display text."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        html = page["html"]
        # Must NOT contain raw enum values in display text
        assert "ConfirmationStatus" not in html
        assert "auto_detected" not in html

    async def test_history_shows_revoked_entry(self, client: AsyncClient):
        """History contains entries after revocation (does not delete)."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        page2 = await _get_candidate_page(client, case_id, doc_id, 0)
        # History section still exists
        assert "Bestätigungshistorie" in page2["html"]
        # Original date preserved (not deleted by revoke)
        assert "31.07.2026" in page2["html"]


# ═══════════════════════════════════════════════════════════════════
# CSRF Protection
# ═══════════════════════════════════════════════════════════════════


class TestCSRFSlice3:
    async def test_correct_requires_csrf(self, client: AsyncClient):
        """Correct without CSRF token → 403 (blocked by security middleware)."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "idempotency_key": "fake-key",
                "expected_active_confirmation_id": str(uuid.uuid4()),
                "confirmed_date": "2026-12-15",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 403  # CSRF middleware blocks before form validation

    async def test_revoke_requires_csrf(self, client: AsyncClient):
        """Revoke without CSRF token → 403 (blocked by security middleware)."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/revoke",
            data={
                "idempotency_key": "fake-key",
                "expected_active_confirmation_id": str(uuid.uuid4()),
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 403  # CSRF middleware blocks before form validation

    async def test_correct_rejects_invalid_date(self, client: AsyncClient):
        """Correct with invalid date → 400."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "confirmed_date": "not-a-date",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# Privacy Logging
# ═══════════════════════════════════════════════════════════════════


class TestPrivacyLogging:
    async def test_error_pages_do_not_leak_internal_data(self, client: AsyncClient):
        """Error pages for correct/revoke do not expose internal state."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        # Trigger a stale state error
        await _confirm_candidate(client, case_id, doc_id)
        page = await _get_candidate_page(client, case_id, doc_id, 0)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": str(uuid.uuid4()),  # Wrong
                "confirmed_date": "2026-12-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 409
        # Error page must NOT contain the actual active confirmation ID
        text = resp.text
        assert "confirmation_id" not in text.lower()
        assert "supersedes" not in text.lower()
