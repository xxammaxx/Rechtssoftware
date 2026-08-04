"""Integration tests for M6-UI routes — security and rendering."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings
from tests.fixtures.synthetic_pdf import MINIMAL_PDF_BYTES


@pytest.fixture
def settings(tmp_path):
    data_dir = tmp_path / "pln_data"
    data_dir.mkdir()
    return Settings(data_dir=data_dir, host="127.0.0.1", port=8000)


@pytest.fixture
async def client(settings: Settings) -> AsyncClient:
    from private_legal_navigator.app import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as ac:
        yield ac


async def _create_case(client: AsyncClient, title: str = "SYNTHETISCH – UI-Test") -> str:
    resp = await client.post("/api/v1/cases", json={"title": title})
    assert resp.status_code == 201
    return resp.json()["case_id"]


class TestUiIndex:
    """Tests for GET /ui/"""

    async def test_ui_index_redirects(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/ui/cases"


class TestUiCaseList:
    """Tests for GET /ui/cases"""

    async def test_ui_case_list_renders(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_ui_case_list_empty_state(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert "Keine Fälle vorhanden" in resp.text

    async def test_ui_case_list_shows_cases(self, client: AsyncClient) -> None:
        await _create_case(client, "SYNTHETISCH – Testfall 1")
        resp = await client.get("/ui/cases")
        assert resp.status_code == 200
        assert "SYNTHETISCH – Testfall 1" in resp.text

    async def test_ui_case_list_cache_control(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert "no-store" in resp.headers.get("cache-control", "")


class TestUiCaseDetail:
    """Tests for GET /ui/cases/{case_id}"""

    async def test_ui_case_detail_renders(self, client: AsyncClient) -> None:
        cid = await _create_case(client, "SYNTHETISCH – Detail")
        resp = await client.get(f"/ui/cases/{cid}")
        assert resp.status_code == 200
        assert "SYNTHETISCH – Detail" in resp.text

    async def test_ui_case_detail_no_documents(self, client: AsyncClient) -> None:
        cid = await _create_case(client)
        resp = await client.get(f"/ui/cases/{cid}")
        assert "Keine Dokumente im Fall" in resp.text

    async def test_ui_unknown_case_returns_404(self, client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/ui/cases/{fake_id}")
        assert resp.status_code == 404

    async def test_ui_invalid_uuid_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases/not-a-uuid")
        assert resp.status_code == 404

    async def test_ui_case_detail_cache_control(self, client: AsyncClient) -> None:
        cid = await _create_case(client)
        resp = await client.get(f"/ui/cases/{cid}")
        assert "no-store" in resp.headers.get("cache-control", "")


class TestUiCaseDetailChronology:
    """Tests for the chronology sidebar on the case detail page (RC-021)."""

    @pytest.fixture
    async def app_and_client(self, settings: Settings):
        from private_legal_navigator.app import create_app

        app = create_app(settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost:8000") as ac:
            yield app, ac

    async def test_sidebar_hidden_without_events(self, app_and_client) -> None:
        _, client = app_and_client
        cid = await _create_case(client)
        resp = await client.get(f"/ui/cases/{cid}")
        assert resp.status_code == 200
        assert "Chronologie" not in resp.text

    async def test_sidebar_shows_confirmed_event(self, app_and_client) -> None:
        from datetime import datetime

        from private_legal_navigator.domain.case_timeline import (
            CaseLegalEvent,
            LegalEventType,
            ReviewStatus,
        )

        app, client = app_and_client
        cid = await _create_case(client)
        timeline_repo = app.state.case_timeline_repository
        timeline_repo.save_event(
            CaseLegalEvent(
                event_id=None,
                case_id=uuid.UUID(cid),
                event_type=LegalEventType.DOCUMENT_RECEIVED,
                occurred_at=datetime(2026, 1, 15, 9, 30),
                title="SYNTHETISCH – Bescheid eingegangen",
                review_status=ReviewStatus.CONFIRMED,
            )
        )
        resp = await client.get(f"/ui/cases/{cid}")
        assert resp.status_code == 200
        assert "Chronologie" in resp.text
        assert "Bescheid eingegangen" in resp.text

    async def test_sidebar_shows_document_upload(self, app_and_client) -> None:
        _, client = app_and_client
        cid = await _create_case(client)
        resp = await client.post(
            f"/api/v1/cases/{cid}/documents",
            files={"file": ("vertrag.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
        )
        assert resp.status_code == 201
        resp = await client.get(f"/ui/cases/{cid}")
        assert resp.status_code == 200
        assert "Chronologie" in resp.text
        assert "Dokument hochgeladen" in resp.text


class TestUiDocumentDetail:
    """Tests for GET /ui/cases/{case_id}/documents/{document_id}"""

    async def _upload_doc(self, client: AsyncClient, case_id: str) -> str:
        resp = await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("test.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
        )
        assert resp.status_code == 201
        return resp.json()["document_id"]

    async def test_ui_document_detail_renders(self, client: AsyncClient) -> None:
        cid = await _create_case(client)
        did = await self._upload_doc(client, cid)
        resp = await client.get(f"/ui/cases/{cid}/documents/{did}")
        assert resp.status_code == 200
        assert "test.pdf" in resp.text

    async def test_ui_unknown_document_returns_404(self, client: AsyncClient) -> None:
        cid = await _create_case(client)
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/ui/cases/{cid}/documents/{fake_id}")
        assert resp.status_code == 404

    async def test_ui_cross_case_document_returns_404(self, client: AsyncClient) -> None:
        cid1 = await _create_case(client, "Fall 1")
        cid2 = await _create_case(client, "Fall 2")
        did = await self._upload_doc(client, cid2)
        # Try to access cid2's document via cid1
        resp = await client.get(f"/ui/cases/{cid1}/documents/{did}")
        assert resp.status_code == 404

    async def test_ui_document_detail_cache_control(self, client: AsyncClient) -> None:
        cid = await _create_case(client)
        did = await self._upload_doc(client, cid)
        resp = await client.get(f"/ui/cases/{cid}/documents/{did}")
        assert "no-store" in resp.headers.get("cache-control", "")


class TestUiSecurityHeaders:
    """Tests for security headers on UI responses."""

    async def test_security_headers_on_200(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("referrer-policy") == "no-referrer"
        assert "default-src" in resp.headers.get("content-security-policy", "")

    async def test_security_headers_on_404(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases/00000000-0000-0000-0000-000000000000")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_csp_contains_no_unsafe_inline(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        csp = resp.headers.get("content-security-policy", "")
        assert "unsafe-inline" not in csp

    async def test_csp_contains_no_unsafe_eval(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        csp = resp.headers.get("content-security-policy", "")
        assert "unsafe-eval" not in csp

    async def test_csp_has_none_default(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp


class TestUiTemplates:
    """Tests for template correctness."""

    async def test_templates_have_lang_de(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert 'lang="de"' in resp.text

    async def test_templates_have_skip_link(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert "skip-link" in resp.text
        assert "Zum Hauptinhalt" in resp.text

    async def test_templates_have_main_landmark(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert 'role="main"' in resp.text

    async def test_templates_have_single_h1(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert resp.text.count("<h1") == 1

    async def test_templates_show_human_review_notice(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert "Menschliche Prüfung erforderlich" in resp.text

    async def test_templates_show_legal_validity_not_assessed(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        assert "Rechtliche Gültigkeit nicht bewertet" in resp.text

    async def test_templates_contain_no_external_assets(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases")
        # Allow localhost (the static CSS link), but reject external CDN URLs
        assert "cdn." not in resp.text
        assert "googleapis" not in resp.text
        assert "fonts.googleapis" not in resp.text
        assert "https://" not in resp.text  # No HTTPS to external origins


class TestUiPrivacy:
    """Tests for UI privacy invariants."""

    async def test_ui_no_internal_exception(self, client: AsyncClient) -> None:
        """UI error pages must not contain stack traces or internal paths."""
        resp = await client.get("/ui/cases/not-a-uuid")
        assert "Traceback" not in resp.text
        assert "Exception" not in resp.text
        assert ".py" not in resp.text.lower()

    async def test_ui_no_sensitive_values_in_query(self, client: AsyncClient) -> None:
        """Query strings must not contain UUID-like patterns."""
        resp = await client.get("/ui/cases")
        # No case_id or document_id in URL params of the base page
        assert resp.status_code == 200

    async def test_ui_does_not_expose_internal_id_in_error(self, client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/ui/cases/{fake_id}/documents/{fake_id}")
        assert resp.status_code == 404
        assert fake_id not in resp.text


class TestUiCaseCreate:
    """Tests for GET/POST /ui/cases/create — case creation via UI."""

    async def _get_csrf_from_page(self, client: AsyncClient, url: str) -> tuple[str, str]:
        """Extract CSRF token and nonce from a page response."""
        resp = await client.get(url)
        assert resp.status_code == 200
        import re

        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
        token = match.group(1) if match else ""
        nonce = ""
        for c in resp.headers.get_list("set-cookie"):
            if "pln_csrf_nonce=" in c:
                nonce = c.split("pln_csrf_nonce=")[1].split(";")[0].strip()
        return token, nonce

    async def test_create_form_renders(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases/create")
        assert resp.status_code == 200
        assert "Neuen Fall anlegen" in resp.text
        assert "Fallname" in resp.text or 'name="title"' in resp.text

    async def test_create_form_has_csrf(self, client: AsyncClient) -> None:
        resp = await client.get("/ui/cases/create")
        assert 'name="csrf_token"' in resp.text

    async def test_create_case_success(self, client: AsyncClient) -> None:
        csrf_token, nonce = await self._get_csrf_from_page(client, "/ui/cases/create")
        client.cookies.set("pln_csrf_nonce", nonce, domain="localhost")
        resp = await client.post(
            "/ui/cases/create",
            data={"csrf_token": csrf_token, "title": "SYNTHETISCH – UI-Form-Test"},
            headers={"Origin": "http://localhost:8000"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "/ui/cases?created=1" in resp.headers.get("location", "")

        resp2 = await client.get("/ui/cases")
        assert "SYNTHETISCH – UI-Form-Test" in resp2.text

    async def test_create_case_empty_title_rejected(self, client: AsyncClient) -> None:
        csrf_token, nonce = await self._get_csrf_from_page(client, "/ui/cases/create")
        client.cookies.set("pln_csrf_nonce", nonce, domain="localhost")
        resp = await client.post(
            "/ui/cases/create",
            data={"csrf_token": csrf_token, "title": ""},
            headers={"Origin": "http://localhost:8000"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "Bitte geben Sie einen Fallnamen ein" in resp.text

    async def test_create_case_no_csrf_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/ui/cases/create",
            data={"title": "No CSRF"},
            follow_redirects=False,
        )
        assert resp.status_code in (403, 400)

    async def test_create_case_persists_on_reload(self, client: AsyncClient) -> None:
        csrf_token, nonce = await self._get_csrf_from_page(client, "/ui/cases/create")
        client.cookies.set("pln_csrf_nonce", nonce, domain="localhost")
        resp = await client.post(
            "/ui/cases/create",
            data={"csrf_token": csrf_token, "title": "SYNTHETISCH – Persistenz-Test"},
            headers={"Origin": "http://localhost:8000"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        resp2 = await client.get("/ui/cases")
        assert "SYNTHETISCH – Persistenz-Test" in resp2.text


class TestUiDocumentUpload:
    """Tests for POST /ui/cases/{case_id}/upload — document upload via UI."""

    async def _get_csrf_from_page(self, client: AsyncClient, url: str) -> tuple[str, str]:
        resp = await client.get(url)
        assert resp.status_code == 200
        import re

        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
        token = match.group(1) if match else ""
        nonce = ""
        for c in resp.headers.get_list("set-cookie"):
            if "pln_csrf_nonce=" in c:
                nonce = c.split("pln_csrf_nonce=")[1].split(";")[0].strip()
        return token, nonce

    async def _setup_case(self, client: AsyncClient) -> tuple[str, str, str]:
        resp = await client.post(
            "/api/v1/cases",
            json={"title": "SYNTHETISCH – Upload-Test"},
        )
        assert resp.status_code == 201
        case_id = resp.json()["case_id"]
        csrf_token, nonce = await self._get_csrf_from_page(client, f"/ui/cases/{case_id}")
        client.cookies.set("pln_csrf_nonce", nonce, domain="localhost")
        return case_id, csrf_token, nonce

    async def test_upload_form_present(self, client: AsyncClient) -> None:
        case_id, csrf_token, nonce = await self._setup_case(client)
        resp = await client.get(f"/ui/cases/{case_id}")
        assert resp.status_code == 200
        assert "PDF-Dokument hochladen" in resp.text or 'type="file"' in resp.text

    async def test_upload_valid_pdf(self, client: AsyncClient) -> None:
        case_id, csrf_token, nonce = await self._setup_case(client)
        resp = await client.post(
            f"/ui/cases/{case_id}/upload",
            data={"csrf_token": csrf_token},
            files={"file": ("test.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
            headers={"Origin": "http://localhost:8000"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "uploaded=1" in resp.headers.get("location", "")

    async def test_upload_rejects_no_csrf(self, client: AsyncClient) -> None:
        case_id, _, _ = await self._setup_case(client)
        resp = await client.post(
            f"/ui/cases/{case_id}/upload",
            data={},
            files={"file": ("test.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
            headers={"Origin": "http://localhost:8000"},
            follow_redirects=False,
        )
        assert resp.status_code in (403, 400)

    async def test_upload_persists_on_reload(self, client: AsyncClient) -> None:
        case_id, csrf_token, nonce = await self._setup_case(client)
        resp = await client.post(
            f"/ui/cases/{case_id}/upload",
            data={"csrf_token": csrf_token},
            files={"file": ("persist-test.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
            headers={"Origin": "http://localhost:8000"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        resp2 = await client.get(f"/ui/cases/{case_id}")
        assert "persist-test.pdf" in resp2.text
