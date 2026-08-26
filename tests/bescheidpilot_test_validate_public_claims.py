from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import bescheidpilot_validate_public_claims as validate_public_claims  # noqa: E402


class PublicClaimValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.site_root = Path(self.temp_dir.name) / "site"
        shutil.copytree(REPO_ROOT / "docs" / "modules" / "bescheidpilot" / "site", self.site_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_current_site_passes(self) -> None:
        self.assertEqual(validate_public_claims.validate_site(self.site_root), [])

    def test_forbidden_claim_fails(self) -> None:
        index = self.site_root / "index.html"
        index.write_text(
            index.read_text(encoding="utf-8") + "\n<p>garantiert korrekt</p>",
            encoding="utf-8",
        )
        errors = validate_public_claims.validate_site(self.site_root)
        self.assertTrue(any("forbidden public claim" in error for error in errors))

    def test_tracking_script_fails(self) -> None:
        index = self.site_root / "index.html"
        index.write_text(
            index.read_text(encoding="utf-8")
            + '\n<script src="https://www.googletagmanager.com/gtag/js"></script>',
            encoding="utf-8",
        )
        errors = validate_public_claims.validate_site(self.site_root)
        self.assertTrue(any("tracking marker" in error for error in errors))
        self.assertTrue(any("remote script asset" in error for error in errors))

    def test_missing_evidence_file_fails(self) -> None:
        (self.site_root / "data/evidence.json").unlink()
        errors = validate_public_claims.validate_site(self.site_root)
        self.assertTrue(any("Missing required site file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
