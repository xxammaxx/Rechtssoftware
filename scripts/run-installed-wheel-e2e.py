#!/usr/bin/env python3
"""Validate M6-UI and M7-B from an installed wheel, without remote requests.

The runner intentionally embeds one minimal synthetic GII fixture.  It never
contacts a public service and leaves its temporary data directory on failure
only when ``--keep-data`` is specified.  Invoke it from outside the checkout
with the fresh wheel-runtime interpreter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

SYNTH_CATALOG_URL = "https://www.gesetze-im-internet.de/gii-toc.xml"
# The planning layer normalizes catalog links to a canonical instrument URL before
# invoking ``download_with_headers``.  Keep this fixture aligned with that
# contract; the catalog itself deliberately retains the GII ``xml.zip`` link.
SYNTH_INSTRUMENT_URL = "https://www.gesetze-im-internet.de/bgb/"
SYNTH_CATALOG = b"""<?xml version="1.0" encoding="UTF-8"?>
<gii-toc stand="2026-07-26">
  <item><link>https://www.gesetze-im-internet.de/bgb/xml.zip</link>
  <title>B\xc3\xbcrgerliches Gesetzbuch</title><type>G</type></item>
</gii-toc>
"""
SYNTH_INSTRUMENT = b"""<?xml version="1.0" encoding="UTF-8"?>
<norm><metadaten><jurabk>BGB</jurabk><langue>B\xc3\xbcrgerliches Gesetzbuch</langue>
<kurzue>BGB</kurzue></metadaten><textdaten><text><Content><P>\xc2\xa7 1
SYNTHETISCH \xe2\x80\x93 Rechtsf\xc3\xa4higkeit beginnt mit der Vollendung der Geburt.</P>
</Content></text></textdaten></norm>
"""


class CheckError(RuntimeError):
    """Raised when one required E2E assertion does not hold."""


class SyntheticGiiClient:
    """Deterministic local source client compatible with the M7-B services."""

    def __init__(self, instrument_archive: bytes) -> None:
        self._instrument_archive = instrument_archive
        self.download_calls: list[str] = []
        self.download_with_headers_calls: list[str] = []

    def download(self, url: str) -> bytes:
        self.download_calls.append(url)
        if url == SYNTH_CATALOG_URL:
            return SYNTH_CATALOG
        if url == "https://www.gesetze-im-internet.de/bgb/xml.zip":
            return self._instrument_archive
        raise CheckError(f"unexpected synthetic download: {url}")

    def download_with_headers(self, url: str) -> Any:
        from private_legal_navigator.infrastructure.safe_source_client import DownloadResult

        self.download_with_headers_calls.append(url)
        if url != SYNTH_INSTRUMENT_URL:
            raise CheckError(f"unexpected synthetic instrument download: {url}")
        return DownloadResult(
            # The execution layer compares this normalized XML body with the
            # parsed snapshot hash.  The adapter separately downloads the ZIP
            # from the catalog link in ``download`` above.
            content=SYNTH_INSTRUMENT,
            http_status=200,
            etag='"SYNTHETISCH-etag"',
            last_modified="Sun, 26 Jul 2026 00:00:00 GMT",
            content_type="application/zip",
        )


def _zip_instrument() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("synthetisch-bgb.xml", SYNTH_INSTRUMENT)
    return buffer.getvalue()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _record(results: dict[str, Any], key: str, detail: Any) -> None:
    results["checks"][key] = detail
    print(f"[PASS] {key}: {detail}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def _count_rows(db_path: Path) -> dict[str, int]:
    tables = (
        "legal_source_snapshots",
        "legal_instruments",
        "legal_expressions",
        "legal_provisions",
        "legal_provisions_fts",
        "sync_runs",
        "sync_items",
    )
    conn = sqlite3.connect(db_path)
    try:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }
    finally:
        conn.close()


def _make_services(data_dir: Path, client: SyntheticGiiClient) -> tuple[Any, Any, Any]:
    from private_legal_navigator.application.legal_source_service import LegalSourceService
    from private_legal_navigator.application.sync_service import (
        SyncExecutionService,
        SyncPlanningService,
    )
    from private_legal_navigator.infrastructure.gii_adapter import GiiAdapter
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    db_path = data_dir / "private_legal_navigator.db"
    snapshots = data_dir / "snapshots"
    snapshots.mkdir(exist_ok=True)
    repo = SqliteLegalSourceRepository(db_path)
    repo.initialize_schema()
    legal_service = LegalSourceService(repo, client, snapshots)
    legal_service.register_default_sources()
    adapter = GiiAdapter(client, snapshots)
    planner = SyncPlanningService(repo, client, adapter)
    executor = SyncExecutionService(repo, legal_service, client, adapter)
    return repo, planner, executor


def _seed_m6_ui_data(data_dir: Path) -> dict[str, str]:
    import pymupdf

    from private_legal_navigator.application.case_service import CaseService
    from private_legal_navigator.application.document_service import DocumentService
    from private_legal_navigator.infrastructure.local_file_storage import LocalFileStorage
    from private_legal_navigator.infrastructure.pdf_text_extractor import PdfTextExtractor
    from private_legal_navigator.infrastructure.rule_based_classifier import RuleBasedClassifier
    from private_legal_navigator.infrastructure.sqlite_case_repository import (
        SqliteCaseRepository,
    )
    from private_legal_navigator.infrastructure.sqlite_document_repository import (
        SqliteDocumentRepository,
    )

    db_path = data_dir / "private_legal_navigator.db"
    cases = SqliteCaseRepository(db_path)
    documents = SqliteDocumentRepository(db_path)
    cases.initialize_schema()
    documents.initialize_schema()
    case = CaseService(cases).create_case("SYNTHETISCH – Wheel-E2E-Fall")
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "SYNTHETISCH – Frist bis 31.07.2026.", fontsize=11)
    content = pdf.tobytes()
    pdf.close()
    service = DocumentService(
        documents,
        LocalFileStorage(data_dir / "documents"),
        cases,
        PdfTextExtractor(),
        RuleBasedClassifier(),
    )
    document = service.upload_document(
        case_id=case.case_id,
        filename="SYNTHETISCH – Wheel-E2E.pdf",
        content=content,
        mime_type="application/pdf",
        size_bytes=len(content),
    )
    return {"case_id": str(case.case_id), "document_id": str(document.document_id)}


class LocalServer:
    """Start and stop the installed application on a random loopback port."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.port = _free_port()
        self.process: subprocess.Popen[bytes] | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> int:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.update(
            {
                "PLN_DATA_DIR": str(self.data_dir),
                "PLN_HOST": "127.0.0.1",
                "PLN_PORT": str(self.port),
                "PLN_CSRF_SECRET": "SYNTHETISCH-WHEEL-E2E-SECRET",
            }
        )
        self.process = subprocess.Popen(
            [sys.executable, "-m", "private_legal_navigator", "serve"],
            cwd=self.data_dir,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                import urllib.request

                with urllib.request.urlopen(f"{self.url}/health", timeout=1) as response:
                    if response.status == 200:
                        return self.process.pid
            except OSError:
                time.sleep(0.2)
        stderr = b"" if self.process is None else self.process.stderr.read(1000)
        raise CheckError(f"installed server did not start: {stderr.decode(errors='replace')}")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)


def _run_cli(data_dir: Path, *args: str) -> str:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PLN_DATA_DIR"] = str(data_dir)
    completed = subprocess.run(
        [sys.executable, "-m", "private_legal_navigator", *args],
        cwd=data_dir,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        raise CheckError(f"CLI {' '.join(args)} failed: {completed.stderr[:500]}")
    return completed.stdout


def _browser_and_axe(
    base_url: str,
    page_paths: list[str],
    axe_script_url: str,
    results: dict[str, Any],
) -> None:
    from playwright.sync_api import sync_playwright

    violations: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="de-DE")
        page = context.new_page()
        for path in page_paths:
            response = page.goto(f"{base_url}{path}", wait_until="networkidle", timeout=20_000)
            _require(response is not None and response.status < 400, f"browser page failed: {path}")
            # Load the packaged local asset from the tested application's own
            # origin.  CSP deliberately rejects inline script injection.
            page.add_script_tag(url=axe_script_url)
            scan = page.evaluate("async () => await axe.run()")
            violations.extend(scan["violations"])
        page.goto(f"{base_url}/ui/cases", wait_until="networkidle", timeout=20_000)
        page.keyboard.press("Tab")
        focus = page.evaluate(
            """() => {
                const active = document.activeElement;
                const style = window.getComputedStyle(active);
                return {
                    tag: active ? active.tagName : "",
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                };
            }"""
        )
        _require(focus["tag"] != "BODY", "keyboard Tab did not move focus")
        _require(
            focus["outlineStyle"] != "none" and focus["outlineWidth"] != "0px",
            f"focused element has no visible focus indicator: {focus}",
        )
        browser.close()
    critical = [item["id"] for item in violations if item.get("impact") == "critical"]
    serious = [item["id"] for item in violations if item.get("impact") == "serious"]
    _require(not critical, f"axe critical violations: {critical}")
    _require(not serious, f"axe serious violations: {serious}")
    _record(results, "browser_pages", len(page_paths))
    _record(results, "axe", {"critical": critical, "serious": serious})
    _record(results, "keyboard_focus", focus)


def _write_evidence(path: Path | None, results: dict[str, Any]) -> None:
    if path is None:
        return
    path.mkdir(parents=True, exist_ok=True)
    target = path / "installed-wheel-e2e.json"
    target.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evidence: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--keep-data", action="store_true")
    arguments = parser.parse_args()

    import private_legal_navigator

    package_path = Path(private_legal_navigator.__file__).resolve()
    _require(
        "site-packages" in package_path.parts,
        f"not imported from site-packages: {package_path}",
    )
    _require(private_legal_navigator.__version__ == "1.0.0rc2", "installed version is not 1.0.0rc2")
    _require("PYTHONPATH" not in os.environ, "PYTHONPATH must be unset for wheel E2E")
    axe_path = package_path.parent / "presentation" / "static" / "axe.min.js"
    _require(axe_path.is_file(), f"installed axe asset is missing: {axe_path}")
    results: dict[str, Any] = {
        "version": private_legal_navigator.__version__,
        "import_path": str(package_path),
        "started_at": datetime.now(UTC).isoformat(),
        "checks": {},
    }
    root = Path(tempfile.mkdtemp(prefix="pln-v021-wheel-e2e-"))
    data_dir = root / "data"
    data_dir.mkdir()
    (data_dir / "documents").mkdir()
    server = LocalServer(data_dir)
    try:
        archive = _zip_instrument()
        client = SyntheticGiiClient(archive)
        repo, planner, executor = _make_services(data_dir, client)
        db_path = data_dir / "private_legal_navigator.db"

        before_dry_run = _count_rows(db_path)
        dry_plan = planner.plan()
        dry_run = executor.execute(dry_plan, dry_run=True)
        after_dry_run = _count_rows(db_path)
        corpus_tables = (
            "legal_source_snapshots",
            "legal_instruments",
            "legal_expressions",
            "legal_provisions",
            "legal_provisions_fts",
        )
        _require(dry_run.dry_run and dry_run.status.value == "COMPLETED", "dry-run not completed")
        _require(
            all(before_dry_run[name] == after_dry_run[name] for name in corpus_tables),
            "dry-run mutated the legal corpus",
        )
        _require(not list((data_dir / "snapshots").iterdir()), "dry-run created a snapshot file")
        _record(results, "m7b_dry_run", {"before": before_dry_run, "after": after_dry_run})

        apply_plan = planner.plan(force=True)
        apply_run = executor.execute(apply_plan, dry_run=False)
        after_apply = _count_rows(db_path)
        _require(apply_run.status.value == "COMPLETED", "apply did not complete")
        _require(
            apply_run.new_count == 1 and apply_run.failed_count == 0,
            "apply counters incorrect",
        )
        _require(after_apply["legal_source_snapshots"] == 1, "apply did not create one snapshot")
        _require(after_apply["legal_instruments"] == 1, "apply did not create one instrument")
        _require(after_apply["legal_expressions"] == 1, "apply did not create one expression")
        _require(after_apply["legal_provisions"] > 0, "apply did not create provisions")
        _require(after_apply["legal_provisions_fts"] > 0, "apply did not create FTS rows")
        snapshots = repo.list_snapshots_for_source("gesetze-im-internet")
        _require(len(snapshots) == 1, "apply did not persist exactly one snapshot")
        snapshot = snapshots[0]
        snapshot_path = Path(snapshot.storage_path)
        _require(snapshot_path.is_file(), "snapshot file does not exist")
        _require(snapshot_path.stat().st_size == snapshot.byte_size, "snapshot byte size mismatch")
        _require(_sha256(snapshot_path) == snapshot.sha256, "snapshot SHA-256 mismatch")
        _record(results, "m7b_apply", {"run_id": apply_run.sync_run_id, "counts": after_apply})

        unchanged_plan = planner.plan(force=True)
        unchanged_run = executor.execute(unchanged_plan, dry_run=False)
        after_unchanged = _count_rows(db_path)
        statuses = [
            item["item_status"] for item in repo.get_items_for_run(unchanged_run.sync_run_id)
        ]
        _require(unchanged_run.unchanged_count == 1, "second apply is not truthful UNCHANGED")
        _require(statuses == ["UNCHANGED"], f"unexpected second item statuses: {statuses}")
        _require(
            all(after_apply[name] == after_unchanged[name] for name in corpus_tables),
            "idempotent apply mutated corpus rows",
        )
        _record(
            results,
            "m7b_idempotency",
            {"run_id": unchanged_run.sync_run_id, "counts": after_unchanged},
        )

        verify_output = _run_cli(data_dir, "legal-source", "verify", "--json")
        verified = json.loads(verify_output)
        _require(len(verified) == 1 and verified[0]["status"] == "VERIFIED", "CLI verify failed")
        _record(results, "snapshot_verify", verified[0])

        ui_data = _seed_m6_ui_data(data_dir)
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT provision_id FROM legal_provisions LIMIT 1").fetchone()
            _require(row is not None, "no provision was persisted")
            provision_id = str(row[0])
        finally:
            conn.close()

        old_pid = server.start()
        status_output = _run_cli(data_dir, "legal-source", "sync-status", "--last", "3")
        expected_cli = (
            unchanged_run.sync_run_id,
            unchanged_run.status.value,
            unchanged_run.started_at,
            unchanged_run.completed_at,
            str(unchanged_run.total_in_catalog),
            str(unchanged_run.new_count),
            str(unchanged_run.changed_count),
            str(unchanged_run.unchanged_count),
            str(unchanged_run.failed_count),
        )
        _require(
            all(value in status_output for value in expected_cli),
            "CLI sync-status lost core data",
        )
        import urllib.request

        with urllib.request.urlopen(f"{server.url}/ui/legal-sources", timeout=10) as response:
            ui_status = response.read().decode("utf-8")
        _require(unchanged_run.sync_run_id in ui_status, "UI sync status lost run ID")
        _require(
            "abgeschlossen" in ui_status and "Unver&auml;ndert" in ui_status,
            "UI sync status incomplete",
        )
        _record(
            results,
            "cli_ui_match",
            {"run_id": unchanged_run.sync_run_id, "status": "COMPLETED"},
        )

        page_paths = [
            "/ui/cases",
            f"/ui/cases/{ui_data['case_id']}",
            f"/ui/cases/{ui_data['case_id']}/documents/{ui_data['document_id']}",
            f"/ui/cases/{ui_data['case_id']}/documents/{ui_data['document_id']}/candidates/0",
            "/ui/legal-sources",
            "/ui/legal-sources/search?q=BGB",
            f"/ui/legal-sources/norm/{provision_id}",
            f"/ui/cases/{ui_data['case_id']}/legal-situation",
            f"/ui/cases/{ui_data['case_id']}/legal-timeline",
        ]
        _browser_and_axe(server.url, page_paths, f"{server.url}/static/axe.min.js", results)

        server.stop()
        new_pid = server.start()
        _require(new_pid != old_pid, "restart did not create a new process")
        with urllib.request.urlopen(f"{server.url}/ui/legal-sources", timeout=10) as response:
            restart_status = response.read().decode("utf-8")
        _require(unchanged_run.sync_run_id in restart_status, "sync history missing after restart")
        search_output = _run_cli(data_dir, "legal-search", "SYNTHETISCH")
        _require("SYNTHETISCH" in search_output, "FTS search failed after restart")
        _record(results, "restart", {"old_pid": old_pid, "new_pid": new_pid})
        results["result"] = "PASS"
        return 0
    except Exception as exc:
        results["result"] = "FAIL"
        results["error"] = f"{type(exc).__name__}: {exc}"
        print(f"[FAIL] {results['error']}", file=sys.stderr)
        return 1
    finally:
        server.stop()
        results["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(arguments.evidence_dir, results)
        if arguments.keep_data:
            print(f"Kept synthetic data: {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
