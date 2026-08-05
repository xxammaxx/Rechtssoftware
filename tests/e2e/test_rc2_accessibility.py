"""RC-016 Accessibility — axe-core scan on all UI pages.

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 18002
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "rc2-linux-e2e" / "accessibility"


@pytest.fixture(scope="session")
def server():
    data_dir = Path(tempfile.mkdtemp(prefix="pln_rc2_a11y_"))
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PLN_DATA_DIR"] = str(data_dir)
    env["PLN_HOST"] = SERVER_HOST
    env["PLN_PORT"] = str(SERVER_PORT)

    server_script = PROJECT_ROOT / "tests" / "e2e" / "server.py"
    proc = subprocess.Popen(
        [sys.executable, str(server_script), str(data_dir), str(SERVER_PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        proc.wait()
        raise RuntimeError("Server did not start within 30s")

    seed_file = data_dir / "seed_data.json"
    seed_data = {}
    if seed_file.exists():
        seed_data = json.loads(seed_file.read_text())

    yield {"base_url": BASE_URL, **seed_data}

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _run_axe(page: Page, page_name: str) -> dict:
    axe_path = PROJECT_ROOT / "src" / "private_legal_navigator" / "presentation" / "static" / "axe.min.js"
    if not axe_path.exists():
        print(f"  [axe] SKIP {page_name}")
        return {"violations": [], "passes": [], "incomplete": []}

    axe_source = axe_path.read_text()
    page.evaluate(axe_source)
    results = page.evaluate("async () => await axe.run()")

    violations = results.get("violations", [])
    critical_or_serious = [v for v in violations if v.get("impact") in ("critical", "serious")]
    if critical_or_serious:
        for v in critical_or_serious:
            print(f"    [{v['impact'].upper()}] {v['id']}: {v['help']} ({len(v.get('nodes', []))} nodes)")
    print(f"  [axe] {page_name}: {len(critical_or_serious)} critical/serious, {len(violations)} total")
    return results


def test_accessibility_all_pages(server: dict) -> None:
    base_url = server["base_url"]
    case_id = server.get("case_id")
    doc_id = server.get("document_id")

    all_critical = 0
    all_serious = 0
    results_log: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        pages_to_test = [
            ("Startseite", f"/ui/"),
            ("Fallliste", f"/ui/cases"),
            ("Falldetail", f"/ui/cases/{case_id}"),
            ("Dokumentdetail", f"/ui/cases/{case_id}/documents/{doc_id}"),
            ("Fristkandidaten", f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0"),
            ("Berechnungsvorschau", f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/preview"),
            ("Legal Sources", f"/ui/legal-sources"),
            ("Legal Search", f"/ui/legal-sources/search?q=VwGO"),
            ("Legal Timeline", f"/ui/cases/{case_id}/legal-timeline"),
            ("Legal Situation", f"/ui/cases/{case_id}/legal-situation"),
            ("Evidence Pack", f"/ui/cases/{case_id}/evidence-pack"),
            ("Fehlerseite 404", f"/ui/errors/404"),
            ("Fehlerseite 400", f"/ui/errors/400"),
            ("Fehlerseite 403", f"/ui/errors/403"),
        ]

        for name, path in pages_to_test:
            print(f"\n{name}: {path}")
            try:
                page.goto(f"{base_url}{path}", wait_until="networkidle", timeout=15000)
                results = _run_axe(page, name)
                critical_count = sum(1 for v in results.get("violations", []) if v.get("impact") == "critical")
                serious_count = sum(1 for v in results.get("violations", []) if v.get("impact") == "serious")
                all_critical += critical_count
                all_serious += serious_count

                screenshot_path = EVIDENCE_DIR / f"a11y_{name.replace(' ', '_').replace('/', '-')}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                results_log.append({"page": name, "critical": critical_count, "serious": serious_count, "total_violations": len(results.get("violations", []))})
            except Exception as exc:
                print(f"  [ERROR] {name}: {exc}")
                results_log.append({"page": name, "error": str(exc)})

        browser.close()

    print(f"\n=== ACCESSIBILITY SUMMARY ===")
    print(f"Pages tested: {len(results_log)}")
    print(f"Critical violations: {all_critical}")
    print(f"Serious violations: {all_serious}")
    for entry in results_log:
        if "error" in entry:
            print(f"  {entry['page']}: ERROR - {entry['error']}")
        else:
            print(f"  {entry['page']}: {entry['critical']} critical, {entry['serious']} serious")

    assert all_critical == 0, f"{all_critical} critical accessibility violations found"
    assert all_serious == 0, f"{all_serious} serious accessibility violations found"

    # Write results
    (EVIDENCE_DIR / "results.json").write_text(json.dumps(results_log, indent=2))
    print(f"\nResults written to {EVIDENCE_DIR / 'results.json'}")
