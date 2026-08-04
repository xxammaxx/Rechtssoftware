"""RC-017 Visible Desktop E2E — User Acceptance Test.

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, UTC
from pathlib import Path

from playwright.sync_api import Page, Browser, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
EVIDENCE_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = EVIDENCE_DIR / "screenshots"
VIDEO_DIR = EVIDENCE_DIR / "video"

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8082
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

CANDIDATE_COMMIT = "6a62460aaa798ede5784f07ac39a51953db5a0dd"
CANDIDATE_TREE = "15518e936c129566cb0159856bce62ed83b850cf"
CANDIDATE_WHEEL = "c59e5a6380b053bef6fc4b2317785fc00f108027d8a69d1e8fcca5b920a682a0"

SLOW_MO = 800
PAUSE_PAGE = 2.0
PAUSE_MUTATION = 3.0
PAUSE_WARNING = 5.0
PAUSE_HISTORY = 8.0

CASE_TITLE = "SYNTHETISCH – Sichtbarer Linux E2E Test RC-017"
PDF_TEXT = (
    "Musterbescheid — ausschliesslich Testdaten\n\n"
    "Aktenzeichen: TEST-RC2-2026-001\n"
    "Datum: 15. Juli 2026\n\n"
    "Beispieltext:\n"
    "Innerhalb von 14 Tagen nach Bekanntgabe kann eine Stellungnahme\n"
    "eingereicht werden.\n\n"
    "Keine reale Behoerde.\n"
    "Keine reale Person.\n"
    "Keine Rechtswirkung.\n"
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _screenshot(page: Page, name: str) -> None:
    path = SCREENSHOT_DIR / f"{name}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        print(f"  [SCREENSHOT] {name}")
    except Exception as exc:
        print(f"  [SCREENSHOT-ERROR] {name}: {exc}")


def _overlay(page: Page, text: str) -> None:
    try:
        page.evaluate(f"""
            const el = document.createElement('div');
            el.id = 'rc017-overlay';
            el.textContent = '{text}';
            el.style.cssText = 'position:fixed;bottom:8px;left:8px;background:#1a1a2e;color:#e0e0e0;'
                + 'padding:8px 16px;font-size:14px;font-family:monospace;z-index:99999;'
                + 'border-radius:4px;opacity:0.9;pointer-events:none;';
            document.body.appendChild(el);
        """)
    except Exception:
        pass


def _remove_overlay(page: Page) -> None:
    try:
        page.evaluate("const el = document.getElementById('rc017-overlay'); if(el) el.remove();")
    except Exception:
        pass


def _run_axe(page: Page, page_name: str) -> dict:
    axe_path = SRC_DIR / "private_legal_navigator" / "presentation" / "static" / "axe.min.js"
    if not axe_path.exists():
        print(f"  [AXE] SKIP — {page_name}")
        return {"violations": []}
    axe_source = axe_path.read_text()
    page.evaluate(axe_source)
    results = page.evaluate("async () => await axe.run()")
    violations = results.get("violations", [])
    critical_or_serious = [v for v in violations if v.get("impact") in ("critical", "serious")]
    status = "CLEAN" if not critical_or_serious else f"{len(critical_or_serious)} CRIT/SERIOUS"
    print(f"  [AXE] {page_name}: {status}")
    for v in critical_or_serious:
        print(f"    [{v['impact'].upper()}] {v['id']}: {v['help']}")
    return results


def _start_server(data_dir: Path) -> subprocess.Popen:
    server_script = EVIDENCE_DIR / "rc017_server.py"
    env = os.environ.copy()
    env["PLN_DATA_DIR"] = str(data_dir)
    env["PLN_HOST"] = SERVER_HOST
    env["PLN_PORT"] = str(SERVER_PORT)
    proc = subprocess.Popen(
        [sys.executable, str(server_script), str(data_dir), str(SERVER_PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
    )
    import requests

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
    return proc


def _stop_server(proc: subprocess.Popen) -> None:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _wait_for_user_confirmation(prompt: str, gate_file: Path, timeout_message: str = "") -> bool:
    """Wait for user to create a gate file to confirm."""
    print(f"\n{prompt}")
    print(f"\nBestätige durch:  touch {gate_file}")
    if timeout_message:
        print(timeout_message)
    print("\nWarte auf Bestätigung...")
    sys.stdout.flush()

    while not gate_file.exists():
        time.sleep(1)
    gate_file.unlink()
    print("Bestätigt!")
    return True


def step(step_id: str, description: str) -> None:
    print(f"\n--- {step_id}: {description} ---")


def main() -> None:
    print("=" * 60)
    print("RC-017 Visible Desktop E2E — User Acceptance Test")
    print(f"  Candidate: {CANDIDATE_COMMIT}")
    print(f"  DISPLAY: {os.environ.get('DISPLAY', 'NONE')}")
    print("=" * 60)

    data_dir = Path(tempfile.mkdtemp(prefix="pln_rc017_"))
    print(f"  Data directory: {data_dir}")

    proc = _start_server(data_dir)
    print(f"  Server PID: {proc.pid}")

    # ── Open visible Chrome ──
    print("\nOpening visible Chrome window...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            slow_mo=SLOW_MO,
            args=["--start-maximized"],
        )
        context = browser.new_context(
            no_viewport=True,
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.set_extra_http_headers({"Origin": BASE_URL})

        # ── Sichtbarkeitsgate ──
        page.goto(f"{BASE_URL}/ui/cases")
        time.sleep(1)

        gate_dir = EVIDENCE_DIR
        gate_visible = gate_dir / "GATE_VISIBLE_CONFIRMED"

        print("\n" + "=" * 60)
        print("SICHTBARKEITSGATE")
        print("=" * 60)
        _wait_for_user_confirmation(
            "Siehst du das Chrome-Fenster auf deinem aktuellen Desktop?",
            gate_visible,
        )

        evidence_log = {
            "candidate_commit": CANDIDATE_COMMIT,
            "candidate_tree": CANDIDATE_TREE,
            "candidate_wheel": CANDIDATE_WHEEL,
            "browser_headless": False,
            "xvfb_used": False,
            "visible_display": True,
            "user_confirmed_browser_visible": True,
            "display": os.environ.get("DISPLAY", ""),
            "xdg_session_type": os.environ.get("XDG_SESSION_TYPE", ""),
            "screenshots": [],
            "steps": [],
            "started_at": _now(),
        }

        # ═══ V00 — Startseite ═══
        step("V00", "Startseite — leere Fallliste")
        page.goto(f"{BASE_URL}/ui/cases")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V00  Startseite")
        _screenshot(page, "V00-startseite")
        _remove_overlay(page)

        # ═══ V01 — Fall erstellen über UI ═══
        step("V01", "Fall erstellen über UI")
        page.goto(f"{BASE_URL}/ui/cases/create")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V01  Fall erstellen")
        _screenshot(page, "V01-create-form")

        title_input = page.locator("#case_title")
        title_input.click()
        page.keyboard.type(CASE_TITLE, delay=60)
        time.sleep(1)

        desc_input = page.locator("#case_description")
        desc_input.click()
        page.keyboard.type(
            "Vollstaendiger synthetischer Nutzerpfad fuer RC-017 sichtbare Abnahme.",
            delay=40,
        )
        time.sleep(1)
        _screenshot(page, "V01-form-filled")

        page.locator('button[type="submit"]').click()
        time.sleep(PAUSE_MUTATION)
        try:
            page.wait_for_url(f"{BASE_URL}/ui/cases**", timeout=15000)
        except Exception:
            pass
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)
        _screenshot(page, "V01-case-list-after-create")
        _remove_overlay(page)

        # Navigate to the case
        try:
            page.wait_for_selector(".item-card", timeout=15000)
            page.locator(".item-card").first.click()
        except Exception as exc:
            print(f"  ERROR finding case: {exc}")
            print(f"  Current URL: {page.url}")
            print(f"  Body preview: {page.text_content('body')[:500]}")
            raise
        time.sleep(PAUSE_PAGE)
        _screenshot(page, "V01-case-detail")
        case_url = page.url
        case_id = case_url.rstrip("/").split("/")[-1]
        print(f"  Case ID: {case_id}")

        # ═══ V02 — PDF hochladen über UI ═══
        step("V02", "PDF hochladen")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V02  PDF hochladen")

        import io as io_m
        import pymupdf

        pdf_w = pymupdf.open()
        pg = pdf_w.new_page(width=595, height=842)
        pg.insert_text((72, 72), PDF_TEXT, fontsize=11)
        buf = io_m.BytesIO()
        pdf_w.save(buf)
        pdf_w.close()
        pdf_path = data_dir / "SYNTHETISCH-Testbescheid-RC2.pdf"
        pdf_path.write_bytes(buf.getvalue())

        page.locator('input[type="file"]').set_input_files(str(pdf_path))
        time.sleep(1)
        _screenshot(page, "V02-file-selected")

        # Find the upload form's submit button specifically
        upload_form = page.locator('form[action*="/upload"]')
        if upload_form.count() > 0:
            upload_form.locator('button[type="submit"]').click()
        else:
            btns = page.locator('button[type="submit"]')
            btn_count = btns.count()
            if btn_count > 1:
                btns.nth(btn_count - 1).click()
            else:
                btns.first.click()
        time.sleep(PAUSE_MUTATION)
        try:
            page.wait_for_url(f"{BASE_URL}/ui/cases/{case_id}**", timeout=15000)
        except Exception:
            pass
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)
        _screenshot(page, "V02-case-with-doc")
        _remove_overlay(page)

        # Get document ID
        doc_link = page.locator(".item-card").first
        doc_link.click()
        time.sleep(PAUSE_PAGE)
        doc_url = page.url
        doc_id = doc_url.rstrip("/").split("/")[-1]
        print(f"  Document ID: {doc_id}")

        # ═══ V03 — Dokument öffnen ═══
        step("V03", "Dokumentansicht")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V03  Dokumentansicht")
        _screenshot(page, "V03-document-view")
        _remove_overlay(page)

        # ═══ V04 — Fristkandidaten ═══
        step("V04", "Fristkandidaten")
        cand_links = page.locator(".item-card")
        if cand_links.count() > 0:
            cand_links.first.click()
        else:
            page.goto(f"{BASE_URL}/ui/cases/{case_id}/documents/{doc_id}/candidates/0")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V04  Fristkandidaten")
        _screenshot(page, "V04-candidates")
        _remove_overlay(page)

        candidate_url = page.url

        # ═══ V05 — Reference Event ═══
        step("V05", "Reference Event")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V05  Reference Event")
        time.sleep(PAUSE_WARNING)
        _screenshot(page, "V05-candidate-detail")
        _remove_overlay(page)

        # ═══ V06 — Bestätigen ═══
        step("V06", "Bestätigen")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V06  Bestätigen")
        confirm_btn = page.locator('form[action$="/confirm"] button[type="submit"]')
        if confirm_btn.count() > 0:
            confirm_btn.first.click()
            time.sleep(PAUSE_MUTATION)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
        _screenshot(page, "V06-confirmed")
        _remove_overlay(page)
        time.sleep(PAUSE_WARNING)

        # ═══ V07 — Korrektur ═══
        step("V07", "Korrigieren")
        page.goto(candidate_url)
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V07  Korrigieren")
        corr_date = page.locator('form[action$="/correct"] input[name="confirmed_date"]')
        if corr_date.count() > 0:
            corr_date.fill("2026-07-20")
            time.sleep(1)
            corr_btn = page.locator('form[action$="/correct"] button[type="submit"]')
            if corr_btn.count() > 0:
                corr_btn.first.click()
                time.sleep(PAUSE_MUTATION)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
        _screenshot(page, "V07-corrected")
        _remove_overlay(page)
        time.sleep(PAUSE_WARNING)

        # ═══ V08 — Widerruf ═══
        page.goto(candidate_url)
        time.sleep(PAUSE_PAGE)
        step("V08", "Widerrufen")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V08  Widerrufen")
        revoke_btn = page.locator('form[action$="/revoke"] button[type="submit"]')
        if revoke_btn.count() > 0:
            revoke_btn.first.click()
            time.sleep(PAUSE_MUTATION)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
        _screenshot(page, "V08-revoked")
        _remove_overlay(page)
        time.sleep(PAUSE_WARNING)

        # ═══ V09 — Erneut bestätigen ═══
        page.goto(candidate_url)
        time.sleep(PAUSE_PAGE)
        step("V09", "Erneut bestätigen")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V09  Erneut bestätigen")
        manual_date_input = page.locator(
            'form[action$="/manual-confirm"] input[name="manual_date"]'
        )
        if manual_date_input.count() > 0:
            manual_date_input.fill("2026-07-15")
            time.sleep(1)
            manual_btn = page.locator('form[action$="/manual-confirm"] button[type="submit"]')
            if manual_btn.count() > 0:
                manual_btn.first.click()
                time.sleep(PAUSE_MUTATION)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
        _screenshot(page, "V09-reconfirmed")
        _remove_overlay(page)
        time.sleep(PAUSE_HISTORY)
        page.goto(candidate_url)
        time.sleep(PAUSE_PAGE)
        _screenshot(page, "V09-history-final")

        # ═══ V10 — Berechnungsvorschau ═══
        page.goto(candidate_url)
        time.sleep(PAUSE_PAGE)
        step("V10", "Berechnungsvorschau")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V10  Berechnungsvorschau")
        preview_link = page.locator('a[href$="/preview"]')
        if preview_link.count() > 0:
            preview_link.first.click()
            time.sleep(PAUSE_PAGE)
            prev_btn = page.locator('button[type="submit"]')
            if prev_btn.count() > 0:
                prev_btn.first.click()
                time.sleep(PAUSE_MUTATION)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
            _screenshot(page, "V10-preview")
        _remove_overlay(page)

        # ═══ V11 — Rechenspur ═══
        step("V11", "Rechenspur")
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V11  Rechenspur")
        _screenshot(page, "V11-trace")
        _remove_overlay(page)
        time.sleep(PAUSE_HISTORY)

        # ═══ V12 — Rechtsquellen ═══
        step("V12", "Rechtsquellenstatus")
        page.goto(f"{BASE_URL}/ui/legal-sources")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V12  Rechtsquellen")
        _screenshot(page, "V12-legal-sources")
        _remove_overlay(page)

        # ═══ V13 — Rechtssuche ═══
        step("V13", "Rechtssuche")
        page.goto(f"{BASE_URL}/ui/legal-sources/search")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V13  Rechtssuche")
        srch = page.locator('input[name="q"]')
        if srch.count() > 0:
            srch.fill("Gericht")
            page.locator('button[type="submit"]').click()
            time.sleep(PAUSE_PAGE)
        _screenshot(page, "V13-search-results")
        _remove_overlay(page)

        # ═══ V14 — Zitationsauflösung ═══
        step("V14", "Zitationsauflösung")
        norm_links = page.locator('a[href*="/norm/"]')
        norm_url = ""
        if norm_links.count() > 0:
            norm_links.first.click()
            time.sleep(PAUSE_PAGE)
            norm_url = page.url
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V14  Zitation")
        _screenshot(page, "V14-citation")
        _remove_overlay(page)

        # ═══ V15 — Norm mit Fall verknüpfen ═══
        step("V15", "Normverknüpfung")
        page.goto(f"{BASE_URL}/ui/cases/{case_id}/legal-situation")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  V15  Normverknüpfung")
        if norm_url and "/norm/" in norm_url:
            prov_id = norm_url.rstrip("/").split("/")[-1]
            prov_input = page.locator('input[name="provision_id"]')
            select_el = page.locator('select[name="provision_id"]')
            if select_el.count() > 0:
                try:
                    select_el.select_option(prov_id)
                except Exception:
                    pass
            elif prov_input.count() > 0:
                prov_input.fill(prov_id)
            link_btn = page.locator('form button[type="submit"]')
            if link_btn.count() > 0:
                link_btn.first.click()
                time.sleep(PAUSE_MUTATION)
        _screenshot(page, "V15-legal-situation")
        _remove_overlay(page)

        # ═══ Timeline ═══
        step("TIMELINE", "Rechtsverlauf")
        page.goto(f"{BASE_URL}/ui/cases/{case_id}/legal-timeline")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  Timeline")
        tl_title = page.locator('input[name="title"]')
        if tl_title.count() > 0:
            tl_title.fill("SYNTHETISCH – Test-Ereignis")
            tl_occ = page.locator('input[name="occurred_at"]')
            if tl_occ.count() > 0:
                tl_occ.fill("2026-07-15")
            tl_type = page.locator('select[name="event_type"]')
            if tl_type.count() > 0:
                try:
                    tl_type.select_option("procedural")
                except Exception:
                    pass
            tl_submit = page.locator('form button[type="submit"]')
            if tl_submit.count() > 0:
                tl_submit.first.click()
                time.sleep(PAUSE_MUTATION)
        _screenshot(page, "TIMELINE")
        _remove_overlay(page)

        # ═══ Evidence Pack ═══
        step("EVIDENCE", "Evidence Pack")
        page.goto(f"{BASE_URL}/ui/cases/{case_id}/evidence-pack")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  Evidence Pack")
        _screenshot(page, "EVIDENCE-PACK")
        _remove_overlay(page)
        time.sleep(PAUSE_HISTORY)

        # ═══ Neustart ═══
        step("RESTART", "Neustart und Persistenz")
        _screenshot(page, "RESTART-before")
        _stop_server(proc)
        print("  Server gestoppt")

        _overlay(page, "RC-017 SICHTBARER E2E-TEST  RESTART  Server gestoppt")
        try:
            page.goto(f"{BASE_URL}/ui/cases", timeout=5000, wait_until="commit")
        except Exception:
            pass  # Expected — server is down
        time.sleep(3)
        _screenshot(page, "RESTART-connection-error")
        _remove_overlay(page)
        time.sleep(PAUSE_WARNING)

        proc = _start_server(data_dir)
        print("  Server neu gestartet")

        page.goto(f"{BASE_URL}/ui/cases")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  RESTART  Persistenz pruefen")
        _screenshot(page, "RESTART-case-list")

        page.goto(f"{BASE_URL}/ui/cases/{case_id}")
        time.sleep(PAUSE_PAGE)
        _screenshot(page, "RESTART-case-detail")
        _remove_overlay(page)
        time.sleep(PAUSE_WARNING)

        # ═══ Accessibility ═══
        step("ACCESSIBILITY", "Axe-Core Scans")
        pages_to_test = [
            ("Startseite", f"/ui/cases"),
            ("Falldetail", f"/ui/cases/{case_id}"),
            ("Dokumentdetail", f"/ui/cases/{case_id}/documents/{doc_id}"),
            ("Fristkandidaten", f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0"),
            ("Legal Sources", "/ui/legal-sources"),
            ("Legal Search", "/ui/legal-sources/search?q=Gericht"),
            ("Evidence Pack", f"/ui/cases/{case_id}/evidence-pack"),
            ("Legal Timeline", f"/ui/cases/{case_id}/legal-timeline"),
            ("Legal Situation", f"/ui/cases/{case_id}/legal-situation"),
        ]

        axe_results = {}
        for name, path in pages_to_test:
            try:
                page.goto(f"{BASE_URL}{path}")
                time.sleep(PAUSE_PAGE)
                _remove_overlay(page)
                results = _run_axe(page, name)
                crit_ser = [
                    v
                    for v in results.get("violations", [])
                    if v.get("impact") in ("critical", "serious")
                ]
                axe_results[name] = {"violations": len(crit_ser)}
                _screenshot(page, f"AXE-{name.replace(' ', '_')[:30]}")
            except Exception as exc:
                print(f"  [AXE-ERROR] {name}: {exc}")
                axe_results[name] = {"error": str(exc)}

        total_crit = sum(r.get("violations", 0) for r in axe_results.values())
        print(f"\n  AXE SUMMARY: {total_crit} critical/serious violations")

        # ═══ Final ═══
        page.goto(f"{BASE_URL}/ui/cases/{case_id}")
        time.sleep(PAUSE_PAGE)
        _overlay(page, "RC-017 SICHTBARER E2E-TEST  ABGESCHLOSSEN")
        _screenshot(page, "FINAL-state")
        _remove_overlay(page)

        # ═══ Freie Nutzerprüfung ═══
        print("\n" + "=" * 60)
        print("FREIE NUTZERPRÜFUNG")
        print("=" * 60)
        print("""
Der sichtbare E2E-Ablauf ist abgeschlossen.

Die Anwendung bleibt geoeffnet.

Bitte pruefe jetzt selbst:
- Fallliste
- Falldetail
- Dokument
- Fristkandidaten
- Reference-Event-History
- Berechnungsvorschau
- Rechenspur
- Timeline
- Rechtsquellen
- Normverküpfung
- Evidence

Druecke erst nach deiner Pruefung ENTER.
""")
        gate_review = EVIDENCE_DIR / "GATE_USER_REVIEW_DONE"
        _wait_for_user_confirmation("Hast du die Anwendung selbst geprueft?", gate_review)

        # ═══ Nutzerabnahme ═══
        print("\n" + "=" * 60)
        print("NUTZERABNAHME")
        print("=" * 60)
        print("Schreibe dein Urteil in eine Datei:")
        print(f"  echo ACCEPT > {EVIDENCE_DIR / 'GATE_VERDICT.txt'}")
        print(f"  echo ACCEPT_WITH_NOTES > {EVIDENCE_DIR / 'GATE_VERDICT.txt'}")
        print(f"  echo REJECT > {EVIDENCE_DIR / 'GATE_VERDICT.txt'}")
        print(f"  echo 'Deine Anmerkungen' > {EVIDENCE_DIR / 'GATE_NOTES.txt'}")
        print()

        verdict_file = EVIDENCE_DIR / "GATE_VERDICT.txt"
        notes_file = EVIDENCE_DIR / "GATE_NOTES.txt"

        while not verdict_file.exists():
            time.sleep(1)

        verdict = verdict_file.read_text().strip().upper()
        notes = notes_file.read_text().strip() if notes_file.exists() else ""
        verdict_file.unlink()
        if notes_file.exists():
            notes_file.unlink()

        print(f"\nNutzerurteil: {verdict}")
        if notes:
            print(f"Anmerkungen: {notes}")

        # ═══ Finalize evidence ═══
        evidence_log["user_verdict"] = verdict
        evidence_log["user_notes"] = notes
        evidence_log["browser_left_open_for_manual_review"] = True
        evidence_log["axe_results"] = axe_results
        evidence_log["completed_at"] = _now()
        evidence_log["classification"] = (
            "GREEN_VISIBLE_LINUX_USER_ACCEPTANCE_VERIFIED"
            if verdict == "ACCEPT"
            else "AMBER_USER_ACCEPTANCE_REJECTED"
            if verdict == "REJECT"
            else "AMBER_VISIBLE_LINUX_ACCEPTED_WITH_NOTES"
        )

        (EVIDENCE_DIR / "rc017-evidence.json").write_text(
            json.dumps(evidence_log, indent=2, ensure_ascii=False)
        )

        # ═══ Browser schließen? ═══
        gate_close = EVIDENCE_DIR / "GATE_CLOSE_NOW"
        print("\nBrowser bleibt erstmal geöffnet.")
        print(f"Zum Schliessen:  touch {gate_close}")
        print("Warte...")
        while not gate_close.exists():
            time.sleep(1)
        gate_close.unlink()
        browser.close()

        _stop_server(proc)
        print("Server gestoppt.")

    print("\n" + "=" * 60)
    print("RC-017 SICHTBARER LINUX E2E ABGESCHLOSSEN")
    print(f"Nutzerurteil: {verdict}")
    print(f"Klassifikation: {evidence_log.get('classification', 'N/A')}")
    print(f"Evidence: {EVIDENCE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    uvicorn_config = None
    main()
