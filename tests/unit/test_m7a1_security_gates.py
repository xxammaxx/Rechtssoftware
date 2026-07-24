"""M7-A.1 Security Gate Tests — CSRF Protection & Cross-Case Isolation.

Verifies at the HTTP level that:
1. CSRF-1: Requests without a CSRF token are rejected (form validation gate)
2. CSRF-2: Requests with an invalid CSRF token are rejected (CSRF gate)
3. CSRF-3: Tokens from a different CSRF secret (cross-session) are rejected
4. CSRF-4: Valid control request succeeds (proof that rejections are CSRF-based)
5. Cross-case: Events/links from Case A cannot be mutated via Case B routes
   even with a valid CSRF token for Case B. State verified before and after.

All data is synthetic. Prefix: SYNTHETISCH –
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings
from private_legal_navigator.middleware.csrf import CsrfConfig, CsrfTokenService

# ── Constants ────────────────────────────────────

KNOWN_SECRET = "test-csrf-secret-m7a1-security-gates-2026"
OTHER_SECRET = "different-csrf-secret-attacker-2026"


# ── Helpers ──────────────────────────────────────


def _make_token(secret: str, scope: str) -> str:
    """Create a valid CSRF token for the given scope and secret."""
    svc = CsrfTokenService(CsrfConfig(secret=secret))
    return svc.create_token(scope)


def _make_bad_token(scope: str) -> str:
    """Create a syntactically valid but wrong-signature CSRF token."""
    import time

    now = int(time.time())
    return f"{now}:{scope}:wrongsignaturedeadbeef"


# ── Fixtures ─────────────────────────────────────


@pytest.fixture(autouse=True)
def _allow_testserver_host():
    """Allow the testserver host header used by TestClient."""
    os.environ["PLN_ALLOWED_HOSTS"] = "testserver"
    yield
    os.environ.pop("PLN_ALLOWED_HOSTS", None)


@pytest.fixture
def client(tmp_path):
    """Create a test client with a known CSRF secret and isolated database."""
    data_dir = tmp_path / "data"
    docs_dir = data_dir / "documents"
    docs_dir.mkdir(parents=True)

    settings = Settings(
        data_dir=data_dir,
        host="127.0.0.1",
        port=8000,
        csrf_secret=KNOWN_SECRET,
    )
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture
def case_a(client):
    """Create Case A via the API."""
    resp = client.post(
        "/api/v1/cases",
        json={"title": "SYNTHETISCH – Case A Security Gate Test"},
    )
    assert resp.status_code == 201, f"Failed to create case A: {resp.text}"
    return resp.json()["case_id"]


@pytest.fixture
def case_b(client):
    """Create Case B via the API."""
    resp = client.post(
        "/api/v1/cases",
        json={"title": "SYNTHETISCH – Case B Security Gate Test"},
    )
    assert resp.status_code == 201, f"Failed to create case B: {resp.text}"
    return resp.json()["case_id"]


def _get_timeline_repo(client):
    """Get the CaseTimelineRepository from the app state."""
    return client.app.state.case_timeline_repository


def _get_legal_repo(client):
    """Get the LegalSourceRepository from the app state."""
    return client.app.state.legal_source_repository


@pytest.fixture
def event_in_a(client, case_a):
    """Create a legal event in Case A via the API."""
    token = _make_token(KNOWN_SECRET, case_a)
    resp = client.post(
        f"/ui/cases/{case_a}/legal-timeline/event",
        data={
            "event_type": "OBJECTION_FILED",
            "title": "SYNTHETISCH – Event in Case A",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, (
        f"Failed to create event in A: status={resp.status_code} body={resp.text[:200]}"
    )
    events = _get_timeline_repo(client).list_events(uuid.UUID(case_a))
    assert len(events) >= 1, "No events found in case A"
    return str(events[0].event_id)


@pytest.fixture
def event_in_b(client, case_b):
    """Create a legal event in Case B via the API."""
    token = _make_token(KNOWN_SECRET, case_b)
    resp = client.post(
        f"/ui/cases/{case_b}/legal-timeline/event",
        data={
            "event_type": "OBJECTION_FILED",
            "title": "SYNTHETISCH – Event in Case B",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, f"Failed to create event in B: {resp.text[:200]}"
    events = _get_timeline_repo(client).list_events(uuid.UUID(case_b))
    assert len(events) >= 1
    return str(events[0].event_id)


@pytest.fixture
def link_in_a(client, case_a):
    """Create a norm link in Case A via direct repository seeding.

    Seeds a synthetic Source → Instrument → Expression → Provision chain,
    then links the provision to Case A.
    """
    from private_legal_navigator.domain.legal_source import (
        AuthorityTier,
        InstrumentType,
        LegalExpression,
        LegalInstrument,
        LegalProvision,
        LegalSource,
        ProvisionType,
        SourceSnapshot,
    )

    repo = _get_legal_repo(client)
    repo.initialize_schema()

    # 1. Create source
    source = LegalSource(
        source_id=uuid.uuid4(),
        source_key="synthetic-test-gii",
        display_name="SYNTHETISCH – Test GII for Security Gates",
        authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
        jurisdiction="DE",
    )
    repo.save_source(source)

    # 2. Create instrument
    instrument = LegalInstrument(
        instrument_id=uuid.uuid4(),
        jurisdiction="DE",
        instrument_type=InstrumentType.STATUTE,
        official_title="SYNTHETISCH – Testgesetz",
        short_title="TestG",
        source_identifier=source.source_key,
    )
    repo.save_instrument(instrument)

    # 3. Create a snapshot
    import hashlib

    content = b"SYNTHETISCH - test content"
    snapshot = SourceSnapshot(
        snapshot_id=uuid.uuid4(),
        source_id=source.source_id,
        source_locator="https://example.com/test-snap",
        retrieved_at=__import__("datetime").datetime(2025, 1, 1),
        content_type="application/xml",
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        storage_path="/tmp/synthetic.snap",
    )
    repo.save_snapshot(snapshot)

    # 4. Create expression
    expression = LegalExpression(
        expression_id=uuid.uuid4(),
        instrument_id=instrument.instrument_id,
        source_snapshot_id=snapshot.snapshot_id,
    )
    repo.save_expression(expression)

    # 5. Create provision
    provision = LegalProvision(
        provision_id=uuid.uuid4(),
        expression_id=expression.expression_id,
        provision_type=ProvisionType.SECTION,
        provision_number="§ 1 TestG",
        heading="SYNTHETISCH – Geltungsbereich",
        text_content="<norm><p>SYNTHETISCH – Text.</p></norm>",
        sort_key="1",
    )
    repo.save_provision(provision)

    # 6. Link provision to case via the service
    timeline_service = client.app.state.case_timeline_service
    link = timeline_service.link_provision_to_case(
        case_id=uuid.UUID(case_a),
        provision_id=provision.provision_id,
        relevance_note="SYNTHETISCH – Security gate test link",
    )
    return str(link.link_id), str(provision.provision_id)


# ── State inspection helpers ─────────────────────


def _event_status(client, event_id: str) -> str:
    event = _get_timeline_repo(client).get_event(uuid.UUID(event_id))
    if event is None:
        return "NOT_FOUND"
    return event.review_status.value


def _link_status(client, link_id: str) -> str:
    link = _get_timeline_repo(client).get_link(uuid.UUID(link_id))
    if link is None:
        return "NOT_FOUND"
    return link.status.value


def _event_count(client, case_id: str) -> int:
    return len(_get_timeline_repo(client).list_events(uuid.UUID(case_id)))


def _link_count(client, case_id: str) -> int:
    return len(_get_timeline_repo(client).list_links(uuid.UUID(case_id)))


# ══════════════════════════════════════════════════
# CSRF Tests
# ══════════════════════════════════════════════════


class TestCsrfMissingToken:
    """CSRF-1: Requests without a CSRF token are rejected.

    Note: Omitting the required csrf_token form field triggers FastAPI's
    RequestValidationError (422) — the framework-level rejection gate.
    This is NOT a 405 (wrong method/route) as previously reported.
    """

    def test_confirm_event_without_csrf_token_field_returns_422(self, client, case_a, event_in_a):
        """POST without csrf_token field → FastAPI form validation rejects (422).

        Evidence: Request does NOT reach application logic. No data mutation.
        """
        status_before = _event_status(client, event_in_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/confirm",
            data={"event_id": event_in_a},
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code == 422, (
            f"Expected 422 (missing required field), got {resp.status_code}: {resp.text[:200]}"
        )
        assert status_after == status_before, (
            f"Event status changed from {status_before} to {status_after}!"
        )

    def test_create_event_without_csrf_token_field_returns_422(self, client, case_a):
        """POST to create event without csrf_token → 422."""
        count_before = _event_count(client, case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/event",
            data={"event_type": "OBJECTION_FILED", "title": "No CSRF test"},
            follow_redirects=False,
        )
        count_after = _event_count(client, case_a)

        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"
        assert count_after == count_before, "Event count changed despite rejection!"


class TestCsrfInvalidToken:
    """CSRF-2: Requests with a present but invalid CSRF token are rejected.

    This is the actual CSRF protection layer: the token reaches the
    CSRF validation logic and is rejected with HTTP 403.
    """

    def test_confirm_event_with_bad_signature_token_returns_403(self, client, case_a, event_in_a):
        """POST with syntactically valid but wrong-signature token → CSRF 403."""
        status_before = _event_status(client, event_in_a)
        bad_token = _make_bad_token(case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/confirm",
            data={"event_id": event_in_a, "csrf_token": bad_token},
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code == 403, (
            f"Expected 403 (CSRF rejection), got {resp.status_code}: {resp.text[:200]}"
        )
        assert status_after == status_before, (
            f"Event status changed from {status_before} to {status_after}!"
        )

    def test_confirm_event_with_empty_csrf_token_returns_422(self, client, case_a, event_in_a):
        """POST with empty csrf_token → FastAPI rejects as validation error (422).

        FastAPI's Form(…) validation rejects empty strings before the CSRF
        middleware can check. This is an additional security layer: malformed
        requests never reach application logic.
        """
        status_before = _event_status(client, event_in_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/confirm",
            data={"event_id": event_in_a, "csrf_token": ""},
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"
        assert status_after == status_before, (
            f"Event status changed from {status_before} to {status_after}!"
        )

    def test_create_event_with_wrong_scope_token_returns_403(self, client, case_a):
        """POST with token scoped to wrong case_id → CSRF 403."""
        count_before = _event_count(client, case_a)
        token = _make_token(KNOWN_SECRET, "wrong-case-id")
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/event",
            data={
                "event_type": "OBJECTION_FILED",
                "title": "Wrong scope CSRF test",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        count_after = _event_count(client, case_a)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"
        assert count_after == count_before, "Event count changed despite rejection!"


class TestCsrfCrossSessionToken:
    """CSRF-3: Token from a different CSRF secret (different session/process)
    is rejected with HTTP 403. No data mutation."""

    def test_token_from_different_secret_returns_403(self, client, case_a, event_in_a):
        """Token signed with a different secret → 403."""
        status_before = _event_status(client, event_in_a)
        token = _make_token(OTHER_SECRET, case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/confirm",
            data={"event_id": event_in_a, "csrf_token": token},
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"
        assert status_after == status_before, (
            f"Event status changed from {status_before} to {status_after}!"
        )

    def test_different_secret_rejected_for_event_creation(self, client, case_a):
        """Create event with token from different secret → 403."""
        count_before = _event_count(client, case_a)
        token = _make_token(OTHER_SECRET, case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/event",
            data={
                "event_type": "OBJECTION_FILED",
                "title": "Different secret CSRF test",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        count_after = _event_count(client, case_a)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"
        assert count_after == count_before, "Event count changed!"


class TestCsrfValidControl:
    """CSRF-4: Valid control request succeeds (303 redirect).

    Proves the above rejections were due to CSRF protection and NOT
    due to routing, method, or payload errors (no HTTP 405).
    """

    def test_valid_token_confirm_event_succeeds(self, client, case_a, event_in_a):
        """POST with valid token for case_a → 303 redirect (success)."""
        token = _make_token(KNOWN_SECRET, case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/confirm",
            data={"event_id": event_in_a, "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303, (
            f"Expected 303 (success redirect), got {resp.status_code}: {resp.text[:200]}"
        )
        assert resp.headers["location"].endswith("/legal-timeline"), (
            f"Expected redirect to /legal-timeline, got {resp.headers.get('location')}"
        )
        # Verify state changed
        assert _event_status(client, event_in_a) == "CONFIRMED", (
            "Event was not confirmed despite valid control request!"
        )

    def test_valid_token_create_event_succeeds(self, client, case_a):
        """Create event with valid token → 303 redirect."""
        count_before = _event_count(client, case_a)
        token = _make_token(KNOWN_SECRET, case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-timeline/event",
            data={
                "event_type": "OBJECTION_FILED",
                "title": "SYNTHETISCH – Valid CSRF create event",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        count_after = _event_count(client, case_a)

        assert resp.status_code == 303, f"Expected 303, got {resp.status_code}: {resp.text[:200]}"
        assert count_after == count_before + 1, (
            f"Event count went from {count_before} to {count_after}"
        )

    def test_valid_token_confirm_link_succeeds(self, client, case_a, link_in_a):
        """POST to confirm a link with valid token → 303 redirect."""
        link_id, _prov_id = link_in_a
        token = _make_token(KNOWN_SECRET, case_a)
        resp = client.post(
            f"/ui/cases/{case_a}/legal-situation/confirm",
            data={"link_id": link_id, "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303, f"Expected 303, got {resp.status_code}: {resp.text[:200]}"
        assert _link_status(client, link_id) == "CONFIRMED", (
            "Link was not confirmed despite valid control request!"
        )


# ══════════════════════════════════════════════════
# Cross-Case Isolation Tests
# ══════════════════════════════════════════════════


class TestCrossCaseEventIsolation:
    """Verify: events in Case A cannot be mutated via Case B routes,
    even with a valid CSRF token for Case B. State verified before/after."""

    def test_confirm_event_a_via_case_b_rejected(self, client, case_a, case_b, event_in_a):
        """Attempt to confirm event in A through case B's route."""
        status_before = _event_status(client, event_in_a)
        count_before = _event_count(client, case_a)

        # Valid CSRF token — but for Case B, not Case A
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-timeline/confirm",
            data={"event_id": event_in_a, "csrf_token": token},
            follow_redirects=False,
        )

        status_after = _event_status(client, event_in_a)
        count_after = _event_count(client, case_a)

        # Cross-case rejection: 404 (not found) or 409 (service conflict)
        assert resp.status_code in (404, 409), (
            f"Expected 404/409 for cross-case confirm, got {resp.status_code}: {resp.text[:200]}"
        )
        assert status_after == status_before, (
            f"Event status changed from '{status_before}' "
            f"to '{status_after}' — CROSS-CASE MUTATION!"
        )
        assert count_after == count_before, (
            f"Event count changed from {count_before} to {count_after}"
        )

    def test_revoke_event_a_via_case_b_rejected(self, client, case_a, case_b, event_in_a):
        """Attempt to revoke event in A through case B's route."""
        status_before = _event_status(client, event_in_a)
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-timeline/revoke",
            data={"event_id": event_in_a, "csrf_token": token},
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code in (404, 409), f"Expected 404/409, got {resp.status_code}"
        assert status_after == status_before, (
            f"Event status changed from '{status_before}' to '{status_after}'"
        )

    def test_correct_event_a_via_case_b_rejected(self, client, case_a, case_b, event_in_a):
        """Attempt to correct event in A through case B's route."""
        status_before = _event_status(client, event_in_a)
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-timeline/correct",
            data={
                "event_id": event_in_a,
                "new_title": "SYNTHETISCH – Cross-case injected title",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code in (404, 409), f"Expected 404/409, got {resp.status_code}"
        assert status_after == status_before, (
            f"Event status changed from '{status_before}' to '{status_after}'"
        )

    def test_reject_event_a_via_case_b_rejected(self, client, case_a, case_b, event_in_a):
        """Attempt to reject event in A through case B's route."""
        status_before = _event_status(client, event_in_a)
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-timeline/reject",
            data={"event_id": event_in_a, "csrf_token": token},
            follow_redirects=False,
        )
        status_after = _event_status(client, event_in_a)

        assert resp.status_code in (404, 409), f"Expected 404/409, got {resp.status_code}"
        assert status_after == status_before, (
            f"Event status changed from '{status_before}' to '{status_after}'"
        )


class TestCrossCaseLinkIsolation:
    """Verify: links in Case A cannot be mutated via Case B routes,
    even with a valid CSRF token for Case B. State verified before/after."""

    def test_confirm_link_a_via_case_b_rejected(self, client, case_a, case_b, link_in_a):
        """Attempt to confirm link in A through case B's route."""
        link_id, _prov_id = link_in_a
        status_before = _link_status(client, link_id)
        count_before = _link_count(client, case_a)

        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-situation/confirm",
            data={"link_id": link_id, "csrf_token": token},
            follow_redirects=False,
        )

        status_after = _link_status(client, link_id)
        count_after = _link_count(client, case_a)

        assert resp.status_code in (404, 409), (
            f"Expected 404/409, got {resp.status_code}: {resp.text[:200]}"
        )
        assert status_after == status_before, (
            f"Link status changed from '{status_before}' to '{status_after}' — CROSS-CASE MUTATION!"
        )
        assert count_after == count_before, (
            f"Link count changed from {count_before} to {count_after}"
        )

    def test_revoke_link_a_via_case_b_rejected(self, client, case_a, case_b, link_in_a):
        """Attempt to revoke link in A through case B's route."""
        link_id, _prov_id = link_in_a
        status_before = _link_status(client, link_id)
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-situation/revoke",
            data={"link_id": link_id, "csrf_token": token},
            follow_redirects=False,
        )
        status_after = _link_status(client, link_id)

        assert resp.status_code in (404, 409), f"Expected 404/409, got {resp.status_code}"
        assert status_after == status_before, (
            f"Link status changed from '{status_before}' to '{status_after}'"
        )

    def test_reject_link_a_via_case_b_rejected(self, client, case_a, case_b, link_in_a):
        """Attempt to reject link in A through case B's route."""
        link_id, _prov_id = link_in_a
        status_before = _link_status(client, link_id)
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-situation/reject",
            data={"link_id": link_id, "csrf_token": token},
            follow_redirects=False,
        )
        status_after = _link_status(client, link_id)

        assert resp.status_code in (404, 409), f"Expected 404/409, got {resp.status_code}"
        assert status_after == status_before, (
            f"Link status changed from '{status_before}' to '{status_after}'"
        )

    def test_correct_link_a_via_case_b_rejected(self, client, case_a, case_b, link_in_a):
        """Attempt to correct link in A through case B's route."""
        link_id, prov_id = link_in_a
        status_before = _link_status(client, link_id)
        token = _make_token(KNOWN_SECRET, case_b)
        resp = client.post(
            f"/ui/cases/{case_b}/legal-situation/correct",
            data={
                "link_id": link_id,
                "new_provision_id": str(prov_id),
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        status_after = _link_status(client, link_id)

        assert resp.status_code in (404, 409), f"Expected 404/409, got {resp.status_code}"
        assert status_after == status_before, (
            f"Link status changed from '{status_before}' to '{status_after}'"
        )
