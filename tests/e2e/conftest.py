"""Persistent E2E test infrastructure for M6-UI Browser tests.

Provides:
- Temp database + FastAPI server fixture
- Seed data (synthetic test case + document + candidates)
- Server lifecycle management (start/stop)

Entry Gate: Does NOT introduce new product features.
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

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 18000  # Non-default port to avoid conflicts
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

# ──────────────────────────────────────────────
# Server Fixture
# ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def e2e_server():
    """Start a FastAPI test server with temp database and seed data.

    Returns dict with base_url, case_id, document_id.
    """
    data_dir = Path(tempfile.mkdtemp(prefix="pln_e2e_slice3_"))
    seed_file = data_dir / "seed_data.json"

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

    # Wait for server to be ready
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"http://{SERVER_HOST}:{SERVER_PORT}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        proc.wait()
        raise RuntimeError("E2E server did not start within 30s")

    # Read seed data
    seed_data = {}
    if seed_file.exists():
        seed_data = json.loads(seed_file.read_text())

    yield {
        "base_url": BASE_URL,
        "process": proc,
        "data_dir": str(data_dir),
        **seed_data,
    }

    # Teardown
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="session")
def base_url(e2e_server):
    """Convenience fixture for base URL."""
    return e2e_server["base_url"]
