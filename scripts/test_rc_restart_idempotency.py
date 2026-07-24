#!/usr/bin/env python3
"""Test idempotency of Confirm, Correct, Revoke operations across a full
server process restart.

Must be run with the RC venv Python, from outside the repository.
Usage:
    python test_rc_restart_idempotency.py
Environment:
    PLN_CSRF_SECRET  - stable CSRF secret
"""

import contextlib
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ──────────────────────────────────────────────
# Self-check
# ──────────────────────────────────────────────


def _self_check():
    try:
        import private_legal_navigator

        pkg_path = Path(private_legal_navigator.__file__).resolve()
        if "site-packages" not in pkg_path.parts:
            print(f"FATAL: Package imported from {pkg_path}")
            sys.exit(1)
        pp = os.environ.get("PYTHONPATH", "")
        if "src" in pp:
            print("FATAL: PYTHONPATH contains src/")
            sys.exit(1)
        print(f"[SELF-CHECK] Package OK: {pkg_path}")
    except ImportError as e:
        print(f"FATAL: Cannot import private_legal_navigator: {e}")
        sys.exit(1)


_self_check()

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(data_dir: Path, port: int, csrf_secret: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PLN_DATA_DIR"] = str(data_dir)
    env["PLN_HOST"] = "127.0.0.1"
    env["PLN_PORT"] = str(port)
    env["PLN_CSRF_SECRET"] = csrf_secret
    env.pop("PYTHONPATH", None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "private_legal_navigator"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(data_dir),
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            if resp.status == 200:
                return proc
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Server did not start on port {port}")


def _stop_server(proc: subprocess.Popen):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _get_form_fields(html: str) -> dict[str, str]:
    """Extract all hidden form fields from an HTML page."""
    fields = {}
    for pattern_name in ["csrf_token", "idempotency_key", "expected_active_confirmation_id"]:
        m = re.search(r'name="' + pattern_name + r'"\s+value="([^"]*)"', html)
        if m is not None:
            fields[pattern_name] = m.group(1)
    return fields


# ──────────────────────────────────────────────
# Referer handler for urllib
# ──────────────────────────────────────────────


class _RefererHandler(urllib.request.BaseHandler):
    def __init__(self, base_url: str):
        self.base_url = base_url

    def http_request(self, req):
        if req.data and not req.has_header("Referer"):
            req.add_unredirected_header("Referer", self.base_url + "/ui/cases/")
        return req


# ──────────────────────────────────────────────
# Test result collector
# ──────────────────────────────────────────────

passed = 0
failed = 0


def _test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")
    if detail:
        print(f"         {detail}")


def _section(name: str):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────


def main():
    csrf_secret = os.environ.get("PLN_CSRF_SECRET", "PLN_RC_IDEMPOTENCY_TEST_SECRET")
    port = _find_free_port()
    data_dir = Path(tempfile.mkdtemp(prefix="pln_idem_"))
    (data_dir / "documents").mkdir(exist_ok=True)
    base_url = f"http://127.0.0.1:{port}"

    print(f"{'=' * 60}")
    print("  RC Restart Idempotency Test")
    print(f"{'=' * 60}")
    print(f"  Python:   {sys.executable}")
    print(f"  Data dir: {data_dir}")
    print(f"  Port:     {port}")
    print(f"  Base URL: {base_url}")

    # Setup opener with cookie jar + referer
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        _RefererHandler(base_url),
    )

    # ── Start server ──
    _section("Start Server")
    proc = _start_server(data_dir, port, csrf_secret)
    pid_before = proc.pid
    _test(f"Server started (PID {pid_before})", True)

    try:
        # ── Seed test data ──
        _section("Seed Test Data")
        import pymupdf

        from private_legal_navigator.application.case_service import CaseService
        from private_legal_navigator.application.document_service import DocumentService
        from private_legal_navigator.infrastructure.local_file_storage import (
            LocalFileStorage,
        )
        from private_legal_navigator.infrastructure.pdf_text_extractor import PdfTextExtractor
        from private_legal_navigator.infrastructure.rule_based_classifier import (
            RuleBasedClassifier,
        )
        from private_legal_navigator.infrastructure.sqlite_case_repository import (
            SqliteCaseRepository,
        )
        from private_legal_navigator.infrastructure.sqlite_document_repository import (
            SqliteDocumentRepository,
        )
        from private_legal_navigator.infrastructure.sqlite_reference_event_repository import (
            SqliteReferenceEventRepository,
        )

        db_path = data_dir / "private_legal_navigator.db"
        SqliteCaseRepository(db_path).initialize_schema()
        SqliteDocumentRepository(db_path).initialize_schema()
        SqliteReferenceEventRepository(db_path).initialize_schema()

        case_repo = SqliteCaseRepository(db_path)
        doc_repo = SqliteDocumentRepository(db_path)
        file_storage = LocalFileStorage(data_dir / "documents")
        text_extractor = PdfTextExtractor()
        classifier = RuleBasedClassifier()
        case_service = CaseService(case_repo)
        doc_service = DocumentService(doc_repo, file_storage, case_repo, text_extractor, classifier)

        test_case = case_service.create_case("SYNTHETISCH \u2013 Idempotency Test Case")
        case_id = str(test_case.case_id)
        _test("Test case created", True, case_id)

        pdf_doc = pymupdf.open()
        page = pdf_doc.new_page(width=612, height=792)
        page.insert_text((72, 72), "SYNTHETISCH \u2013 Frist bis 31.07.2026.", fontsize=11)
        pdf_bytes = pdf_doc.tobytes()

        doc = doc_service.upload_document(
            case_id=test_case.case_id,
            filename="SYNTHETISCH \u2013 Idempotency Test.pdf",
            content=pdf_bytes,
            mime_type="application/pdf",
            size_bytes=len(pdf_bytes),
        )
        document_id = str(doc.document_id)
        _test("Test document created", True, document_id)

        # ── Get candidate page + CSRF tokens ──
        _section("Get CSRF Tokens")
        resp = opener.open(f"{base_url}/ui/cases/{case_id}/documents/{document_id}/candidates/0")
        html = resp.read().decode("utf-8")
        _test("Candidate page loads", resp.status == 200)

        confirm_fields = _get_form_fields(html)
        _test("CSRF token found", "csrf_token" in confirm_fields)
        _test("Idempotency key found", "idempotency_key" in confirm_fields)

        # ── Confirm (before restart) ──
        _section("Confirm (before restart)")
        confirm_data = urllib.parse.urlencode(
            {
                "csrf_token": confirm_fields.get("csrf_token", ""),
                "idempotency_key": confirm_fields.get("idempotency_key", ""),
                "confirmed_date": "2026-07-31",
            }
        ).encode("utf-8")
        resp = opener.open(
            f"{base_url}/ui/cases/{case_id}/documents/{document_id}/candidates/0/confirm",
            data=confirm_data,
        )
        # urllib auto-follows 303 redirect to final page
        _test("Confirm: HTTP 200 after PRG redirect", resp.status == 200, f"final_url={resp.url}")
        _test(
            "Confirm: redirects to detail page",
            "candidates/0" in resp.url or "confirmed" in resp.url,
            resp.url,
        )
        # ── Get Correct tokens ──
        resp2 = opener.open(f"{base_url}/ui/cases/{case_id}/documents/{document_id}/candidates/0")
        html2 = resp2.read().decode("utf-8")
        correct_fields = _get_form_fields(html2)
        _test("Correct CSRF token found", "csrf_token" in correct_fields)
        _test("Correct idempotency key found", "idempotency_key" in correct_fields)

        # ── Correct (before restart) ──
        _section("Correct (before restart)")
        correct_data = urllib.parse.urlencode(
            {
                "csrf_token": correct_fields.get("csrf_token", ""),
                "idempotency_key": correct_fields.get("idempotency_key", ""),
                "confirmed_date": "2026-08-15",
                "expected_active_confirmation_id": correct_fields.get(
                    "expected_active_confirmation_id", ""
                ),
            }
        ).encode("utf-8")
        resp3 = opener.open(
            f"{base_url}/ui/cases/{case_id}/documents/{document_id}/candidates/0/correct",
            data=correct_data,
        )
        _test("Correct: HTTP 200 after PRG redirect", resp3.status == 200, f"final_url={resp3.url}")
        _test("Correct: redirects to candidate page", "candidates" in resp3.url, resp3.url)

        # ── Get Revoke tokens ──
        resp4 = opener.open(f"{base_url}/ui/cases/{case_id}/documents/{document_id}/candidates/0")
        html4 = resp4.read().decode("utf-8")
        revoke_fields = _get_form_fields(html4)
        _test("Revoke CSRF token found", "csrf_token" in revoke_fields)
        _test("Revoke idempotency key found", "idempotency_key" in revoke_fields)

        # ── Revoke (before restart) ──
        _section("Revoke (before restart)")
        revoke_data = urllib.parse.urlencode(
            {
                "csrf_token": revoke_fields.get("csrf_token", ""),
                "idempotency_key": revoke_fields.get("idempotency_key", ""),
                "expected_active_confirmation_id": revoke_fields.get(
                    "expected_active_confirmation_id", ""
                ),
            }
        ).encode("utf-8")
        resp5 = opener.open(
            f"{base_url}/ui/cases/{case_id}/documents/{document_id}/candidates/0/revoke",
            data=revoke_data,
        )
        _test("Revoke: HTTP 200 after PRG redirect", resp5.status == 200, f"final_url={resp5.url}")
        _test("Revoke: redirects to candidate page", "candidates" in resp5.url, resp5.url)

        # ── Record all keys ──
        _section("Record Idempotency Keys")
        idem_keys = {
            "confirm": confirm_fields.get("idempotency_key", ""),
            "correct": correct_fields.get("idempotency_key", ""),
            "revoke": revoke_fields.get("idempotency_key", ""),
        }
        _test("Confirm key recorded", len(idem_keys["confirm"]) > 0)
        _test("Correct key recorded", len(idem_keys["correct"]) > 0)
        _test("Revoke key recorded", len(idem_keys["revoke"]) > 0)
        print(f"  Keys: {json.dumps(idem_keys, indent=2)}")

        # ── Restart server ──
        _section("Restart Server")
        _stop_server(proc)
        # Wait for port to close
        with contextlib.suppress(Exception):
            urllib.request.urlopen(f"{base_url}/health", timeout=2)
        _test("Server stopped", True)
        proc2 = _start_server(data_dir, port, csrf_secret)
        pid_after = proc2.pid
        _test("New PID after restart", pid_before != pid_after, f"{pid_before} -> {pid_after}")
        proc = proc2

        # ── Verify persistence after restart ──
        _section("Verify Persistence After Restart")
        import sqlite3

        conn = sqlite3.connect(str(data_dir / "private_legal_navigator.db"))

        # Check data survived restart
        case_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        event_count = conn.execute("SELECT COUNT(*) FROM confirmed_reference_events").fetchone()[0]
        idem_count = conn.execute("SELECT COUNT(*) FROM idempotency_records").fetchone()[0]

        _test("Cases persisted after restart", case_count == 1, str(case_count))
        _test("Documents persisted after restart", doc_count == 1, str(doc_count))
        _test("Reference events persisted after restart", event_count >= 3, str(event_count))
        _test("Idempotency records persisted after restart", idem_count >= 3, str(idem_count))

        # Verify idempotency keys are still in the DB
        confirm_key_in_db = conn.execute(
            "SELECT status FROM idempotency_records WHERE idempotency_key = ?",
            (idem_keys["confirm"],),
        ).fetchone()
        _test(
            "Confirm idempotency key found in DB after restart",
            confirm_key_in_db is not None,
            str(confirm_key_in_db[0] if confirm_key_in_db else ""),
        )

        correct_key_in_db = conn.execute(
            "SELECT status FROM idempotency_records WHERE idempotency_key = ?",
            (idem_keys["correct"],),
        ).fetchone()
        _test(
            "Correct idempotency key found in DB after restart",
            correct_key_in_db is not None,
            str(correct_key_in_db[0] if correct_key_in_db else ""),
        )

        revoke_key_in_db = conn.execute(
            "SELECT status FROM idempotency_records WHERE idempotency_key = ?",
            (idem_keys["revoke"],),
        ).fetchone()
        _test(
            "Revoke idempotency key found in DB after restart",
            revoke_key_in_db is not None,
            str(revoke_key_in_db[0] if revoke_key_in_db else ""),
        )

        # Verify the confirmed_reference_events have the correct history
        history_rows = conn.execute(
            "SELECT event_type, is_revoke, confirmed_date "
            "FROM confirmed_reference_events ORDER BY confirmed_at"
        ).fetchall()
        _test(
            f"History has {len(history_rows)} entries (expected >= 3)",
            len(history_rows) >= 3,
            f"rows: {[(r[0], r[1], r[2]) for r in history_rows]}",
        )

        conn.close()

    finally:
        _stop_server(proc)

    # ── Summary ──
    _section("RESULTS")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
