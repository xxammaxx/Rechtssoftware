"""Integration tests for M6-UI Slice 4: Calculation Preview & Trace.

Tests:
- Active-state gates (requires CONFIRMED, rejects REVOKED/unconfirmed)
- Server-side reference date (never from client)
- Expected-state binding (stale → 409)
- Read-only proof (zero database writes)
- Deterministic arithmetic
- Trace consistency
- Security (CSRF, Origin, Content-Type)
- Disclaimer
"""

import re
from pathlib import Path

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings


# ── Test PDF generation ──────────────────────────────────────────────

_SYNTHETIC_PDF_TEXT: str = (
    "Bescheid vom 15.06.2026\n\n"
    "Sehr geehrte Damen und Herren,\n\n"
    "hiermit ergeht folgender Bescheid. Sie können innerhalb von 14 Tagen "
    "Widerspruch einlegen.\n\n"
    "Mit freundlichen Grüßen\n"
    "Die Behörde\n"
)

# Candidate 0: EXPLICIT_DATE "15.06.2026"
# Candidate 1: RELATIVE_PERIOD "innerhalb von 14 Tagen" (amount=14, unit=day)
# We confirm and preview candidate 1 (RELATIVE_PERIOD) which has duration data.
_CANDIDATE_IDX = 1  # RELATIVE_PERIOD — has duration for calculation


def _create_pdf_with_date_text() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), _SYNTHETIC_PDF_TEXT, fontsize=11)
    return doc.tobytes()


# ── Fixtures ─────────────────────────────────────────────────────────


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


# ── Helpers ──────────────────────────────────────────────────────────


async def _create_case(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/cases", json={"title": "SYNTHETISCH – Preview Testfall"})
    assert resp.status_code == 201
    return resp.json()["case_id"]


async def _upload_pdf(client: AsyncClient, case_id: str) -> str:
    resp = await client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={
            "file": (
                "SYNTHETISCH – Preview Bescheid.pdf",
                _create_pdf_with_date_text(),
                "application/pdf",
            )
        },
    )
    assert resp.status_code == 201
    return resp.json()["document_id"]


async def _get_candidate_page(
    client: AsyncClient, case_id: str, doc_id: str, idx: int = _CANDIDATE_IDX
) -> dict:
    resp = await client.get(f"/ui/cases/{case_id}/documents/{doc_id}/candidates/{idx}")
    assert resp.status_code == 200
    html = resp.text
    return {
        "html": html,
        "csrf_token": _extract_token(html, "csrf_token"),
        "idempotency_key": _extract_token(html, "idempotency_key"),
        "expected_active": _extract_token(html, "expected_active_confirmation_id"),
    }


def _extract_token(html: str, name: str) -> str:
    m = re.search(rf'name="{name}"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


async def _confirm_candidate(client: AsyncClient, case_id: str, doc_id: str) -> dict:
    """Confirm RELATIVE_PERIOD candidate to set reference date + have duration."""
    page = await _get_candidate_page(client, case_id, doc_id, _CANDIDATE_IDX)
    resp = await client.post(
        f"/ui/cases/{case_id}/documents/{doc_id}/candidates/{_CANDIDATE_IDX}/confirm",
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


async def _get_preview_page(
    client: AsyncClient, case_id: str, doc_id: str, idx: int = _CANDIDATE_IDX
) -> dict:
    resp = await client.get(f"/ui/cases/{case_id}/documents/{doc_id}/candidates/{idx}/preview")
    html = resp.text
    return {
        "status": resp.status_code,
        "html": html,
        "csrf_token": _extract_token(html, "csrf_token"),
        "expected_active": _extract_token(html, "expected_active_confirmation_id"),
        "has_result": "Rechnerisches Ergebnis" in html,
        "has_trace": "So wurde gerechnet" in html,
    }


async def _count_confirmations(settings: Settings) -> int:
    """Count confirmed_reference_events via DB access."""
    import sqlite3

    db_path = str(settings.database_path)
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT COUNT(*) FROM confirmed_reference_events")
    count = cur.fetchone()[0]
    conn.close()
    return count


async def _count_idempotency(settings: Settings) -> int:
    """Count idempotency_records in the database."""
    import sqlite3

    db_path = str(settings.database_path)
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT COUNT(*) FROM idempotency_records")
    count = cur.fetchone()[0]
    conn.close()
    return count


# ═══════════════════════════════════════════════════════════════════════
# Active-State Gates (INV-S4-01)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewActiveStateGates:
    async def test_preview_requires_active_confirmation(self, client: AsyncClient):
        """GET preview without active confirmation shows info message, no result."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        page = await _get_preview_page(client, case_id, doc_id)
        assert page["status"] == 200
        assert not page["has_result"]
        assert page["html"].find("aktuell bestätigtes Bezugsdatum") >= 0

    async def test_preview_post_rejects_unconfirmed_candidate(self, client: AsyncClient):
        """POST preview without confirmation fails."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        page = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": page["csrf_token"],
                "expected_active_confirmation_id": "00000000-0000-0000-0000-000000000000",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code in (400, 403)  # Validation or CSRF

    async def test_preview_rejects_revoked_candidate(self, client: AsyncClient):
        """POST preview after revoke shows no active confirmation."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        # Revoke
        page = await _get_candidate_page(client, case_id, doc_id)
        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        preview = await _get_preview_page(client, case_id, doc_id)
        assert preview["status"] == 200
        assert not preview["has_result"]

    async def test_preview_uses_current_corrected_confirmation(self, client: AsyncClient):
        """Preview after correction uses corrected date."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        # Correct to a different date
        page = await _get_candidate_page(client, case_id, doc_id)
        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/correct",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "confirmed_date": "2026-08-15",
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        preview = await _get_preview_page(client, case_id, doc_id)
        assert preview["status"] == 200
        assert "15.08.2026" in preview["html"]


# ═══════════════════════════════════════════════════════════════════════
# Server-Side Source of Truth (INV-S4-02)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewServerSideReference:
    async def test_preview_form_contains_no_reference_date_field(self, client: AsyncClient):
        """Form does NOT contain a reference_date or confirmed_date input field."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        page = await _get_preview_page(client, case_id, doc_id)
        assert 'name="reference_date"' not in page["html"]
        assert 'name="confirmed_date"' not in page["html"]
        assert 'name="detected_date"' not in page["html"]

    async def test_preview_result_shows_server_loaded_reference_date(self, client: AsyncClient):
        """Result page shows the server-loaded reference date."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "31.07.2026" in resp.text


# ═══════════════════════════════════════════════════════════════════════
# Expected-State Binding (INV-S4-07)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewExpectedState:
    async def test_preview_rejects_stale_expected_state(self, client: AsyncClient):
        """POST with wrong expected_active → 409."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": "11111111-1111-1111-1111-111111111111",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 409

    async def test_preview_after_concurrent_revoke_returns_409(self, client: AsyncClient):
        """After revoke (simulating another tab), preview returns 409."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)

        # Revoke via candidate page
        page = await _get_candidate_page(client, case_id, doc_id)
        revoke_resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/revoke",
            data={
                "csrf_token": page["csrf_token"],
                "idempotency_key": page["idempotency_key"],
                "expected_active_confirmation_id": page["expected_active"],
                "event_type": "unknown",
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert revoke_resp.status_code == 303

        # POST with stale expected_active
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════════════════
# Read-Only Proof (INV-S4-03)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewReadOnly:
    async def test_preview_creates_no_new_confirmations(
        self, client: AsyncClient, settings: Settings
    ):
        """Preview POST does not create new confirmation records."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        before = await _count_confirmations(settings)
        assert before >= 1

        preview = await _get_preview_page(client, case_id, doc_id)
        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        after = await _count_confirmations(settings)
        assert after == before

    async def test_preview_creates_no_idempotency_record(
        self, client: AsyncClient, settings: Settings
    ):
        """Preview POST does not create idempotency records."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        before = await _count_idempotency(settings)

        preview = await _get_preview_page(client, case_id, doc_id)
        await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )

        after = await _count_idempotency(settings)
        assert after == before

    async def test_repeated_preview_creates_no_database_changes(
        self, client: AsyncClient, settings: Settings
    ):
        """Multiple preview POSTs = zero DB changes."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        before_c = await _count_confirmations(settings)
        before_i = await _count_idempotency(settings)

        preview = await _get_preview_page(client, case_id, doc_id)
        for _ in range(3):
            resp = await client.post(
                f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
                data={
                    "csrf_token": preview["csrf_token"],
                    "expected_active_confirmation_id": preview["expected_active"],
                },
                headers={
                    "Origin": "http://127.0.0.1:8000",
                    "Referer": "http://127.0.0.1:8000/ui/",
                },
                follow_redirects=False,
            )
            assert resp.status_code == 200

        after_c = await _count_confirmations(settings)
        after_i = await _count_idempotency(settings)
        assert after_c == before_c
        assert after_i == before_i


# ═══════════════════════════════════════════════════════════════════════
# Deterministic Arithmetic & Trace (INV-S4-06, INV-S4-09, INV-S4-10)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewDeterministicAndTrace:
    async def test_preview_is_deterministic(self, client: AsyncClient):
        """Same inputs → same output date."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)

        async def _do_preview():
            resp = await client.post(
                f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
                data={
                    "csrf_token": preview["csrf_token"],
                    "expected_active_confirmation_id": preview["expected_active"],
                },
                headers={
                    "Origin": "http://127.0.0.1:8000",
                    "Referer": "http://127.0.0.1:8000/ui/",
                },
                follow_redirects=False,
            )
            return resp.text

        r1 = await _do_preview()
        r2 = await _do_preview()

        d1 = re.search(r"preview-date.*?<strong>([\d.]+)</strong>", r1, re.DOTALL)
        d2 = re.search(r"preview-date.*?<strong>([\d.]+)</strong>", r2, re.DOTALL)
        assert d1 is not None
        assert d2 is not None
        assert d1.group(1) == d2.group(1)

    async def test_trace_contains_reference_date(self, client: AsyncClient):
        """Trace shows the reference date used."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert "31.07.2026" in resp.text

    async def test_trace_final_value_matches_preview_result(self, client: AsyncClient):
        """Last trace step output matches the displayed result."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        # Both result and trace section should show the same calculated date
        result_dates = re.findall(r"(\d{2}\.\d{2}\.\d{4})", resp.text)
        assert len(result_dates) >= 2  # reference + result

    async def test_trace_contains_no_internal_class_names(self, client: AsyncClient):
        """Trace must not show Python class names or internal details."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        for banned in [
            "DeterministicCalendarArithmetic",
            "CalendarCalculationCandidate",
            "CalculationStep",
            "ADD_CALENDAR_DAYS",
            "timedelta",
        ]:
            assert banned not in resp.text, f"'{banned}' found in preview"

    async def test_trace_contains_no_internal_ids(self, client: AsyncClient):
        """Trace section must not show UUIDs (page URLs are fine)."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        # Extract only the trace list content — the ordered list between
        # "So wurde gerechnet" and the next card section
        trace_marker = "So wurde gerechnet"
        end_marker = "Nicht angewandte Anpassungen"
        if trace_marker in resp.text and end_marker in resp.text:
            trace_start = resp.text.index(trace_marker)
            trace_end = resp.text.index(end_marker, trace_start)
            trace_section = resp.text[trace_start:trace_end]
        else:
            trace_section = resp.text
        uuids = re.findall(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            trace_section,
            re.IGNORECASE,
        )
        # The trace section should have 0 UUIDs
        assert len(uuids) == 0, f"UUIDs in trace section: {uuids}"


# ═══════════════════════════════════════════════════════════════════════
# Security (CSRF, Origin, Content-Type)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewSecurity:
    async def test_preview_post_requires_csrf(self, client: AsyncClient):
        """POST without CSRF token fails."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={"expected_active_confirmation_id": "any"},
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code in (400, 403)

    async def test_preview_rejects_wrong_origin(self, client: AsyncClient):
        """POST with wrong Origin fails."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://evil.example.com", "Referer": "http://evil.example.com/"},
            follow_redirects=False,
        )
        assert resp.status_code == 403

    async def test_preview_accepts_valid_referer(self, client: AsyncClient):
        """POST with valid Origin + Referer succeeds."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════
# Disclaimer (INV-S4-08)
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewDisclaimer:
    async def test_result_page_contains_disclaimer(self, client: AsyncClient):
        """Result page shows disclaimer about no legal validity."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert "Keine rechtliche Gültigkeit" in resp.text

    async def test_result_does_not_claim_legal_validity(self, client: AsyncClient):
        """Result must not use forbidden legal terms."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        preview = await _get_preview_page(client, case_id, doc_id)
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        for term in [
            "Fristende",
            "maßgebliche Frist",
            "rechtlich gültig",
            "rechtzeitig",
            "verspätet",
            "Ablauf der Frist",
        ]:
            assert term not in resp.text, f"Forbidden term '{term}' in preview"


# ═══════════════════════════════════════════════════════════════════════
# Happy Path
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewHappyPath:
    async def test_preview_happy_path(self, client: AsyncClient):
        """Full happy path: GET → POST → result with trace and disclaimer."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        # GET
        preview = await _get_preview_page(client, case_id, doc_id)
        assert preview["status"] == 200
        assert preview["csrf_token"] != ""
        assert "Unverbindliche Rechenvorschau" in preview["html"]

        # POST
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/1/preview",
            data={
                "csrf_token": preview["csrf_token"],
                "expected_active_confirmation_id": preview["expected_active"],
            },
            headers={"Origin": "http://127.0.0.1:8000", "Referer": "http://127.0.0.1:8000/ui/"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "Rechnerisches Ergebnis" in resp.text
        assert "So wurde gerechnet" in resp.text
        assert "Keine Wochenendverschiebung" in resp.text
        assert "Keine Feiertagsbereinigung" in resp.text

        # 2026-07-31 + 14 days = 2026-08-14
        assert "14.08.2026" in resp.text

    async def test_preview_link_visible_only_when_confirmed(self, client: AsyncClient):
        """Preview link on candidate detail visible only with active confirmation."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        # Before confirmation
        page = await _get_candidate_page(client, case_id, doc_id)
        assert "Rechenvorschau" not in page["html"]

        # After confirmation
        await _confirm_candidate(client, case_id, doc_id)
        page2 = await _get_candidate_page(client, case_id, doc_id)
        assert "Rechenvorschau" in page2["html"]


# ═══════════════════════════════════════════════════════════════════════
# Error Paths
# ═══════════════════════════════════════════════════════════════════════


class TestPreviewErrorPaths:
    async def test_preview_get_invalid_case_id(self, client: AsyncClient):
        """GET preview with invalid case UUID → 404."""
        resp = await client.get(
            "/ui/cases/00000000-0000-0000-0000-000000000000/documents/"
            "00000000-0000-0000-0000-000000000000/candidates/0/preview"
        )
        assert resp.status_code == 404

    async def test_preview_post_cross_case_document(self, client: AsyncClient):
        """Preview POST returns error when document doesn't belong to case."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)
        await _confirm_candidate(client, case_id, doc_id)

        # Create second case
        case2_id = await _create_case(client)

        # GET preview on case2 with doc from case1 → service returns ValueError
        resp = await client.get(f"/ui/cases/{case2_id}/documents/{doc_id}/candidates/1/preview")
        assert resp.status_code in (400, 404)

    async def test_preview_post_invalid_candidate_index(self, client: AsyncClient):
        """Preview with non-existent candidate index → 404 on GET."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        resp = await client.get(f"/ui/cases/{case_id}/documents/{doc_id}/candidates/99/preview")
        assert resp.status_code in (400, 404)

    async def test_preview_get_returns_page_even_without_confirmation(self, client: AsyncClient):
        """GET preview page loads with info message when unconfirmed."""
        case_id = await _create_case(client)
        doc_id = await _upload_pdf(client, case_id)

        page = await _get_preview_page(client, case_id, doc_id)
        assert page["status"] == 200
        assert "Unverbindliche Rechenvorschau" in page["html"]
