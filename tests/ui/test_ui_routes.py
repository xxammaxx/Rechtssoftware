"""Integration tests for M6-UI routes — security and rendering."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings


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


class TestUiDocumentDetail:
    """Tests for GET /ui/cases/{case_id}/documents/{document_id}"""

    async def _upload_doc(self, client: AsyncClient, case_id: str) -> str:
        resp = await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 content", "application/pdf")},
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
        assert resp.text.count("<h1>") == 1

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
        # Error message should be generic
        assert fake_id not in resp.text
