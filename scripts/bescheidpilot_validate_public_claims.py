#!/usr/bin/env python3
"""Validate BescheidPilot's static public website without network access."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

FORBIDDEN_CLAIMS = (
    "garantiert korrekt",
    "ersetzt rechtsberatung",
    "vollautomatisch rechtssicher",
    "sendet automatisch an behörden",
    "cloud-ki verarbeitet",
    "alle fristen sicher",
    "fehlerfrei",
    "fertiges antwortschreiben",
    "rechtssicherer widerspruch",
    "automatisch rechtswirksam",
    "ersetzt anwalt",
    "garantiert korrekte antwort",
    "automatisch an behörde senden",
    "automatischer versand",
    "ohne prüfung verwendbar",
    "juristisch geprüft",
    "anwaltsgeprüft",
    "rechtsverbindlich",
)

TRACKING_MARKERS = (
    "google-analytics",
    "googletagmanager",
    "gtag(",
    "posthog",
    "mixpanel",
    "amplitude",
    "segment.io",
    "segment.com",
    "hotjar",
    "crashlytics",
    "sentry.io",
)

REQUIRED_FILES = (
    "index.html",
    "privacy.html",
    "roadmap.html",
    "evidence.html",
    "demo.html",
    "investor.html",
    "status.html",
    "assets/styles.css",
    "assets/app.js",
    "data/project-status.json",
    "data/roadmap.json",
    "data/evidence.json",
    "data/features.json",
)

ALLOWED_EVIDENCE_STATUSES = {
    "documented",
    "partial",
    "complete",
    "missing",
    "not-yet-proven",
}

ALLOWED_FEATURE_STATUSES = {
    "planned",
    "in-progress",
    "demo-ready",
    "validated",
    "pilot-ready",
    "deferred",
}

ALLOWED_ROADMAP_STATUSES = {
    "planned",
    "in-progress",
    "complete",
    "deferred",
}

REMOTE_ASSET_TAGS = {
    "script": ("src",),
    "img": ("src", "srcset"),
    "source": ("src", "srcset"),
    "iframe": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
}


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def is_remote_url(value: str) -> bool:
    value = value.strip()
    return value.startswith(("http://", "https://", "//"))


class SiteHTMLParser(HTMLParser):
    def __init__(self, file_path: Path, site_root: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.file_path = file_path
        self.site_root = site_root
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}

        for attribute in REMOTE_ASSET_TAGS.get(tag, ()):
            value = attributes.get(attribute, "")
            if is_remote_url(value):
                self.errors.append(f"{self.file_path}: remote {tag} asset is not allowed: {value}")

        if tag == "link":
            rel = set(attributes.get("rel", "").casefold().split())
            href = attributes.get("href", "")
            if rel.intersection({"stylesheet", "preload", "modulepreload"}) and is_remote_url(href):
                self.errors.append(f"{self.file_path}: remote linked asset is not allowed: {href}")

        if tag == "a":
            href = attributes.get("href", "")
            self._validate_internal_link(href)

    def _validate_internal_link(self, href: str) -> None:
        if not href or href.startswith(("#", "mailto:", "tel:")) or is_remote_url(href):
            return

        parsed = urlparse(href)
        relative_path = parsed.path
        if not relative_path:
            return

        target = (self.file_path.parent / relative_path).resolve()
        try:
            target.relative_to(self.site_root.resolve())
        except ValueError:
            self.errors.append(f"{self.file_path}: internal link escapes site root: {href}")
            return

        if relative_path.endswith("/") or target.suffix == "":
            target = target / "index.html"
        if not target.exists():
            self.errors.append(f"{self.file_path}: internal link target does not exist: {href}")


def read_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None


def validate_required_files(site_root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        path = site_root / relative
        if not path.is_file():
            errors.append(f"Missing required site file: {relative}")


def iter_text_files(site_root: Path) -> Iterable[Path]:
    for path in site_root.rglob("*"):
        if path.is_file() and path.suffix.casefold() in {
            ".html",
            ".css",
            ".js",
            ".json",
            ".txt",
            ".md",
        }:
            yield path


def validate_text_content(site_root: Path, errors: list[str]) -> None:
    css_remote_pattern = re.compile(
        r"(?:url\s*\(\s*|@import\s+)[\"']?(?:https?:)?//", re.IGNORECASE
    )

    for path in iter_text_files(site_root):
        content = path.read_text(encoding="utf-8")
        normalized = normalize(content)

        for claim in FORBIDDEN_CLAIMS:
            if claim in normalized:
                errors.append(f"{path}: forbidden public claim found: {claim}")

        for marker in TRACKING_MARKERS:
            if marker in normalized:
                errors.append(f"{path}: tracking marker found: {marker}")

        if path.suffix.casefold() == ".css" and css_remote_pattern.search(content):
            errors.append(f"{path}: remote CSS asset or import found")


def validate_html(site_root: Path, errors: list[str]) -> None:
    for path in site_root.rglob("*.html"):
        parser = SiteHTMLParser(path, site_root)
        parser.feed(path.read_text(encoding="utf-8"))
        errors.extend(parser.errors)


def require_keys(item: object, required: set[str], context: str, errors: list[str]) -> bool:
    if not isinstance(item, dict):
        errors.append(f"{context}: expected an object")
        return False

    missing = required.difference(item)
    if missing:
        errors.append(f"{context}: missing keys: {', '.join(sorted(missing))}")
        return False
    return True


def validate_evidence(site_root: Path, errors: list[str]) -> None:
    data = read_json(site_root / "data/evidence.json", errors)
    if data is None:
        return
    if not isinstance(data, list) or not data:
        errors.append("data/evidence.json: expected a non-empty list")
        return

    for index, item in enumerate(data):
        context = f"data/evidence.json[{index}]"
        if not require_keys(item, {"claim", "status", "evidence", "limitation"}, context, errors):
            continue
        if item["status"] not in ALLOWED_EVIDENCE_STATUSES:
            errors.append(f"{context}: invalid status: {item['status']}")
        if not str(item["evidence"]).strip():
            errors.append(f"{context}: evidence reference must not be empty")
        if item["status"] == "complete" and not str(item["limitation"]).strip():
            errors.append(
                f"{context}: complete claims still require an explicit limitation statement"
            )


def validate_features(site_root: Path, errors: list[str]) -> None:
    data = read_json(site_root / "data/features.json", errors)
    if data is None:
        return
    if not isinstance(data, list):
        errors.append("data/features.json: expected a list")
        return

    for index, item in enumerate(data):
        context = f"data/features.json[{index}]"
        if not require_keys(
            item, {"feature", "status", "description", "evidence"}, context, errors
        ):
            continue
        if item["status"] not in ALLOWED_FEATURE_STATUSES:
            errors.append(f"{context}: invalid status: {item['status']}")
        if item["status"] in {"validated", "pilot-ready"} and not str(item["evidence"]).strip():
            errors.append(f"{context}: verified feature lacks evidence")


def validate_roadmap(site_root: Path, errors: list[str]) -> None:
    data = read_json(site_root / "data/roadmap.json", errors)
    if data is None:
        return
    if not isinstance(data, list) or len(data) != 6:
        errors.append("data/roadmap.json: expected exactly six milestones")
        return

    for index, item in enumerate(data):
        context = f"data/roadmap.json[{index}]"
        if not require_keys(item, {"milestone", "status", "summary", "evidence"}, context, errors):
            continue
        if item["status"] not in ALLOWED_ROADMAP_STATUSES:
            errors.append(f"{context}: invalid status: {item['status']}")


def validate_project_status(site_root: Path, errors: list[str]) -> None:
    data = read_json(site_root / "data/project-status.json", errors)
    if data is None:
        return
    required = {
        "project",
        "status",
        "mvpPhase",
        "localOnlyStatus",
        "uploadRisk",
        "remoteLlmRisk",
        "demoStatus",
        "evidenceStatus",
        "deployStatus",
        "lastUpdated",
        "nextMilestone",
        "openBlockers",
    }
    if not require_keys(data, required, "data/project-status.json", errors):
        return
    if data["localOnlyStatus"] == "GREEN":
        errors.append(
            "data/project-status.json: GREEN Local-only status is forbidden without "
            "implemented guardrail evidence"
        )
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data["lastUpdated"])):
        errors.append("data/project-status.json: lastUpdated must use YYYY-MM-DD")
    if not isinstance(data["openBlockers"], list):
        errors.append("data/project-status.json: openBlockers must be a list")


def validate_site(site_root: Path) -> list[str]:
    errors: list[str] = []
    site_root = site_root.resolve()

    if not site_root.is_dir():
        return [f"Site root does not exist: {site_root}"]

    validate_required_files(site_root, errors)
    validate_text_content(site_root, errors)
    validate_html(site_root, errors)
    validate_evidence(site_root, errors)
    validate_features(site_root, errors)
    validate_roadmap(site_root, errors)
    validate_project_status(site_root, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "site",
        help="Path to the static site directory.",
    )
    args = parser.parse_args()

    errors = validate_site(args.site_root)
    if errors:
        print("Public website validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Public website validation passed: {args.site_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
