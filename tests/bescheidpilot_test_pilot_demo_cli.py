"""Tests for the Pilot Demo CLI."""

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bescheidpilot.cli.demo import main

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "validation"
FIXTURE = str(FIXTURES_DIR / "validation_001_jobcenter_mitwirkung.txt")
FIXTURE_NONE = str(FIXTURES_DIR / "nonexistent_file.txt")


class PilotDemoCLITests(unittest.TestCase):
    """Test the CLI demo runs correctly."""

    def _run(self, *args: str) -> tuple[int, str, str]:
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with (
            patch.object(sys, "stdout", captured_stdout),
            patch.object(sys, "stderr", captured_stderr),
        ):
            rc = main(list(args))
        return rc, captured_stdout.getvalue(), captured_stderr.getvalue()

    def test_basic_run(self) -> None:
        rc, out, err = self._run("--input", FIXTURE)
        self.assertEqual(rc, 0)
        self.assertIn("BESCHEIDPILOT PILOT-DEMO", out)
        self.assertIn("PRÜFUNG ERFORDERLICH", out)

    def test_shows_final_decision_no(self) -> None:
        rc, out, err = self._run("--input", FIXTURE)
        self.assertIn("Finale Entscheidung: NEIN", out)

    def test_shows_authority(self) -> None:
        rc, out, err = self._run("--input", FIXTURE)
        self.assertIn("Jobcenter", out)

    def test_shows_review_items(self) -> None:
        rc, out, err = self._run("--input", FIXTURE)
        self.assertIn("REVIEW-PFLICHT", out)
        self.assertIn("requires_review", out)

    def test_shows_evidence(self) -> None:
        rc, out, err = self._run("--input", FIXTURE)
        self.assertIn("FUNDSTELLEN", out)

    def test_shows_disclaimer(self) -> None:
        rc, out, err = self._run("--input", FIXTURE)
        self.assertIn("ersetzt keine Rechtsberatung", out)

    def test_export_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = str(Path(tmpdir) / "export.txt")
            rc, out, err = self._run(
                "--input",
                FIXTURE,
                "--export",
                export_path,
            )
            self.assertEqual(rc, 0)
            self.assertTrue(Path(export_path).is_file())
            content = Path(export_path).read_text(encoding="utf-8")
            self.assertIn("BESCHEIDPILOT ANALYSE-EXPORT", content)

    def test_export_with_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = str(Path(tmpdir) / "export_draft.txt")
            rc, out, err = self._run(
                "--input",
                FIXTURE,
                "--export",
                export_path,
                "--include-draft",
            )
            self.assertEqual(rc, 0)
            content = Path(export_path).read_text(encoding="utf-8")
            self.assertIn("ANTWORTENTWURF", content)
            self.assertIn("ENTWURF", content)

    def test_rejects_missing_file(self) -> None:
        rc, out, err = self._run("--input", FIXTURE_NONE)
        self.assertEqual(rc, 1)
        self.assertIn("FEHLER", err)

    def test_rejects_url_input(self) -> None:
        rc, out, err = self._run("--input", "https://example.com/doc.txt")
        self.assertEqual(rc, 1)

    def test_rejects_url_export(self) -> None:
        rc, out, err = self._run(
            "--input",
            FIXTURE,
            "--export",
            "https://example.com/out.txt",
        )
        self.assertEqual(rc, 1)

    def test_no_sensitive_data_direct_log(self) -> None:
        """The CLI output should not contain raw fixture text as direct output.
        Evidence quotes are expected to contain fixture text."""
        rc, out, err = self._run("--input", FIXTURE)
        # The output contains evidence quotes, but should NOT contain
        # the full fixture text verbatim as a standalone line
        lines = out.split("\n")
        for line in lines:
            if "VALIDIERUNGSFIXTURE" in line:
                continue  # expected in evidence
            # No line should be a full raw Bescheid text line on its own
            self.assertFalse(
                line.strip().startswith("Sehr geehrte"),
                f"Raw text line in output: {line}",
            )

    def test_no_network_imports(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src" / "bescheidpilot" / "cli" / "demo.py"
        content = source.read_text(encoding="utf-8")
        self.assertNotIn("import requests", content)
        self.assertNotIn("import openai", content)


if __name__ == "__main__":
    unittest.main()
