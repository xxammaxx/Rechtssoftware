#!/usr/bin/env python3
"""Fail when product code contains remote, upload, or telemetry paths."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

TEXT_SUFFIXES = {
    ".cjs",
    ".dart",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

PRODUCT_SUFFIXES = {
    ".cjs",
    ".dart",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".rs",
    ".ts",
    ".tsx",
}

PRODUCT_ROOTS = {"app", "bescheidpilot", "crates", "lib", "packages", "src"}
PRODUCT_MANIFESTS = {
    "Cargo.toml",
    "package.json",
    "pubspec.yaml",
    "pyproject.toml",
    "requirements.txt",
}

CONTROL_PATHS = {
    "scripts/guardrail_check.py",
    "src/core/network_guard.py",
}

NETWORK_MODULES = {
    "aiohttp",
    "axios",
    "ftplib",
    "http.client",
    "httpx",
    "requests",
    "smtplib",
    "socket",
    "urllib.request",
    "websocket",
    "websockets",
}

REMOTE_PROVIDER_MODULES = {
    "amplitude",
    "anthropic",
    "azure",
    "azure.ai",
    "boto3",
    "cohere",
    "firebase_admin",
    "genai",
    "google.cloud",
    "google.genai",
    "google.generativeai",
    "groq",
    "huggingface_hub",
    "mistral",
    "mistralai",
    "ollama",
    "openai",
    "perplexity",
    "posthog",
    "sentry_sdk",
    "supabase",
    "together",
}

REMOTE_CONFIGURATION_KEYS = {
    "ANTHROPIC_API_KEY",
    "API_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY",
    "BASE_URL",
    "BEDROCK_API_KEY",
    "COHERE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_API_TOKEN",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "MISTRAL_API_KEY",
    "ABBYY_API_KEY",
    "ADOBE_CLIENT_ID",
    "ADOBE_CLIENT_SECRET",
    "AZURE_COGNITIVE_SERVICES_KEY",
    "AZURE_COMPUTER_VISION_KEY",
    "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    "AZURE_FORM_RECOGNIZER_KEY",
    "CLOUD_OCR_URL",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "OCR_API_KEY",
    "OCR_BASE_URL",
    "OCR_SPACE_API_KEY",
    "OPENAI_API_KEY",
    "PERPLEXITY_API_KEY",
    "REMOTE_LLM_URL",
    "REMOTE_OCR_URL",
    "REMOTE_URL",
    "TOGETHER_API_KEY",
}

REMOTE_LLM_RISK_RULES = {
    "forbidden network/provider import",
    "remote URL literal",
    "remote configuration",
    "remote provider reference",
    "remote credential/configuration dependency",
    "remote configuration identifier",
    "remote HTTP method literal",
}

CLOUD_OCR_RISK_RULES = {
    "forbidden network/provider import",
    "remote URL literal",
    "remote configuration",
    "remote provider reference",
    "remote credential/configuration dependency",
    "remote configuration identifier",
    "multipart upload content type",
    "upload or telemetry call",
    "document upload pattern",
    "cloud OCR reference",
}

SENSITIVE_LOG_RISK_RULES = {
    "sensitive logging call",
    "sensitive variable reference",
    "telemetry or crash reference",
}

# Variable names that suggest sensitive Bescheid content when logged
SENSITIVE_VARIABLE_NAMES = {
    "address",
    "aktenzeichen",
    "answer_draft",
    "bescheid_text",
    "bg_nummer",
    "case_id",
    "customer_name",
    "document_text",
    "draft_response",
    "full_text",
    "iban",
    "image_text",
    "kundennummer",
    "ocr_text",
    "pdf_text",
    "raw_text",
}

OFFLINE_BLOCKER_PATTERN = re.compile(
    r"(?i)\b(?:required internet|requires network|remote required|"
    r"api key required|cloud required)\b"
)

CONTEXT_PATTERN = re.compile(
    r"(?i)(https?://|websocket|\bsocket\b|upload|multipart|form-data|"
    r"\b(?:api|base)_url\b|endpoint|telemetry|analytics|sentry|crashlytics|"
    r"firebase|supabase|amplitude|posthog|mixpanel|segment|openai|anthropic|"
    r"gemini|mistral|groq|cohere|perplexity|together|huggingface|"
    r"\bcloud\b|\bsync\b|\bbackup\b|\bs3\b|\bgcs\b|"
    r"\bazure\b|\bremote\b|"
    r"\bocr\b|tesseract|textract|form.recognizer|document.intelligence|"
    r"computer.vision|abbyy|ocr.space|adobe.pdf|pdf.services)"
)

GENERIC_PRODUCT_RULES = (
    (
        "network dependency",
        re.compile(
            r"(?i)[\"']?(?:axios|aiohttp|httpx|requests|websockets?|"
            r"reqwest|ureq|dio)[\"']?\s*[:=]"
        ),
    ),
    (
        "remote URL",
        re.compile(r"(?i)\b(?:https?|wss?)://"),
    ),
    (
        "network client",
        re.compile(
            r"(?i)\b(?:fetch|axios|aiohttp|httpx|requests|websockets?|"
            r"httpclient|reqwest|ureq|dio)"
            r"(?:\s*[\.(])"
        ),
    ),
    (
        "upload or telemetry operation",
        re.compile(
            r"(?i)\b(?:upload|send_telemetry|track_event|capture_event)"
            r"\w*\s*\("
        ),
    ),
    (
        "remote configuration",
        re.compile(
            r"\b(?:ABBYY_API_KEY|ADOBE_CLIENT_ID|ADOBE_CLIENT_SECRET|"
            r"ANTHROPIC_API_KEY|API_URL|AWS_ACCESS_KEY_ID|"
            r"AWS_SECRET_ACCESS_KEY|AZURE_COGNITIVE_SERVICES_KEY|"
            r"AZURE_COMPUTER_VISION_KEY|AZURE_DOCUMENT_INTELLIGENCE_KEY|"
            r"AZURE_FORM_RECOGNIZER_KEY|AZURE_OPENAI_API_KEY|BASE_URL|"
            r"BEDROCK_API_KEY|CLOUD_OCR_URL|COHERE_API_KEY|GEMINI_API_KEY|"
            r"GOOGLE_API_KEY|GOOGLE_APPLICATION_CREDENTIALS|"
            r"GOOGLE_CLOUD_PROJECT|GROQ_API_KEY|HF_TOKEN|"
            r"HUGGINGFACE_API_TOKEN|LLM_API_KEY|LLM_BASE_URL|"
            r"MISTRAL_API_KEY|OCR_API_KEY|OCR_BASE_URL|OCR_SPACE_API_KEY|"
            r"OPENAI_API_KEY|"
            r"PERPLEXITY_API_KEY|REMOTE_ENDPOINT|REMOTE_LLM_URL|"
            r"REMOTE_OCR_URL|REMOTE_URL|"
            r"TOGETHER_API_KEY|UPLOAD_ENDPOINT)\b"
        ),
    ),
    (
        "remote provider reference",
        re.compile(
            r"(?i)\b(?:openai|anthropic|gemini|mistral|groq|cohere|perplexity|"
            r"together|huggingface|ollama|firebase|"
            r"supabase|posthog|mixpanel|segment|sentry|crashlytics|"
            r"amplitude|boto3|azure)\b"
        ),
    ),
    (
        "remote infrastructure reference",
        re.compile(r"(?i)\b(?:cloud|sync|backup|s3|gcs)\b"),
    ),
    (
        "multipart upload content type",
        re.compile(r"(?i)\bmultipart/form-data\b"),
    ),
    (
        "offline blocker",
        OFFLINE_BLOCKER_PATTERN,
    ),
    (
        "document upload pattern",
        re.compile(
            r"(?i)\b(?:upload_document|upload_image|upload_pdf|"
            r"upload_scan|send_document|process_document_remote|"
            r"remote_ocr|cloud_ocr)\w*\s*\("
        ),
    ),
    (
        "cloud OCR reference",
        re.compile(
            r"(?i)\b(?:tesseract.cloud|ocr\.space|"
            r"abbyy|adobe.pdf|textract|"
            r"document.intelligence|form.recognizer|"
            r"computer.vision|documentai|"
            r"cloud.vision|image.annotator)\b"
        ),
    ),
    (
        "sensitive logging call",
        re.compile(
            r"(?i)\b(?:print|console\.log|console\.error|console\.warn|"
            r"logger\.info|logger\.debug|logger\.error|logger\.warn|"
            r"logging\.info|logging\.debug|logging\.error)\s*\("
            r"\s*(?:document_text|ocr_text|raw_text|bescheid_text|"
            r"full_text|pdf_text|image_text|draft_response|"
            r"answer_draft|aktenzeichen|kundennummer|bg_nummer|"
            r"case_id|customer_name|address|iban)"
            r"\s*\)"
        ),
    ),
    (
        "telemetry or crash reference",
        re.compile(
            r"(?i)\b(?:sentry|crashlytics|firebase\.crashlytics|"
            r"bugsnag|rollbar|datadog|new.?relic|"
            r"appcenter\.crashes)"
        ),
    ),
    (
        "external web asset reference",
        re.compile(
            r"(?i)\b(?:cdn\.jsdelivr|unpkg\.com|googleapis\.com|"
            r"gstatic\.com|cloudflare\.com|jsdelivr\.net)"
        ),
    ),
    (
        "public network bind address",
        re.compile(r"\b0\.0\.0\.0\b"),
    ),
)


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    rule: str
    snippet: str


@dataclass(slots=True)
class ScanReport:
    product_files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    context_hits: Counter[str] = field(default_factory=Counter)

    @property
    def passed(self) -> bool:
        return not self.findings

    @property
    def remote_llm_risks(self) -> list[Finding]:
        return [f for f in self.findings if f.rule in REMOTE_LLM_RISK_RULES]

    @property
    def remote_llm_risks_count(self) -> int:
        return len(self.remote_llm_risks)

    @property
    def cloud_ocr_risks(self) -> list[Finding]:
        return [f for f in self.findings if f.rule in CLOUD_OCR_RISK_RULES]

    @property
    def cloud_ocr_risks_count(self) -> int:
        return len(self.cloud_ocr_risks)

    @property
    def sensitive_log_risks(self) -> list[Finding]:
        return [f for f in self.findings if f.rule in SENSITIVE_LOG_RISK_RULES]

    @property
    def sensitive_log_risks_count(self) -> int:
        return len(self.sensitive_log_risks)


def _module_is_forbidden(module: str) -> bool:
    return any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for forbidden in NETWORK_MODULES | REMOTE_PROVIDER_MODULES
    )


def _classify_path(relative_path: Path) -> str:
    path = relative_path.as_posix()
    parts = relative_path.parts

    if path in CONTROL_PATHS:
        return "control"
    if not parts:
        return "other"
    if parts[0] in {"tests", "test"} or "tests" in parts or "fixtures" in parts:
        return "test"
    if parts[0] == "docs" or relative_path.suffix.lower() in {".md", ".txt"}:
        return "documentation"
    if parts[0] == "site":
        return "website"
    if parts[0] == ".github":
        return "workflow"
    if parts[0] == "scripts":
        return "tooling"
    if parts[0] in PRODUCT_ROOTS and relative_path.suffix.lower() in PRODUCT_SUFFIXES:
        return "product"
    if relative_path.name in PRODUCT_MANIFESTS:
        return "product"
    return "other"


def _iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in PRODUCT_MANIFESTS:
            files.append(path)
    return sorted(files)


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _scan_python(path: Path, relative_path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(text, filename=str(relative_path))
    except SyntaxError as error:
        return [
            Finding(
                relative_path.as_posix(),
                error.lineno or 1,
                "unparseable product Python",
                error.msg,
            )
        ]

    lines = text.splitlines()

    def add(node: ast.AST, rule: str, snippet: str | None = None) -> None:
        line_number = getattr(node, "lineno", 1)
        source = snippet
        if source is None and 0 < line_number <= len(lines):
            source = lines[line_number - 1].strip()
        findings.append(
            Finding(
                relative_path.as_posix(),
                line_number,
                rule,
                (source or "").strip()[:160],
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_is_forbidden(alias.name):
                    add(node, "forbidden network/provider import")
        elif isinstance(node, ast.ImportFrom):
            if node.module and _module_is_forbidden(node.module):
                add(node, "forbidden network/provider import")
        elif isinstance(node, ast.Call):
            call_name = _dotted_name(node.func).lower()
            if any(
                call_name == name or call_name.startswith(f"{name}.")
                for name in (
                    "aiohttp",
                    "httpx",
                    "requests",
                    "socket",
                    "urllib.request",
                    "websocket",
                    "websockets",
                )
            ):
                add(node, "forbidden network call")
            if any(
                token in call_name
                for token in (
                    "upload",
                    "send_telemetry",
                    "track_event",
                    "capture_event",
                )
            ):
                add(node, "upload or telemetry call")
            if any(
                token in call_name
                for token in (
                    "upload_document",
                    "upload_image",
                    "upload_pdf",
                    "upload_scan",
                    "send_document",
                    "remote_ocr",
                    "cloud_ocr",
                    "process_document_remote",
                )
            ):
                add(node, "document upload pattern")
            if "ImageAnnotatorClient" in call_name or "DocumentProcessorServiceClient" in call_name:
                add(node, "cloud OCR reference")
            if "textract" in call_name.lower() or "formrecognizer" in call_name.lower():
                add(node, "cloud OCR reference")
            for arg in node.args:
                if (
                    isinstance(arg, ast.Name)
                    and arg.id in SENSITIVE_VARIABLE_NAMES
                    and any(
                        token in call_name
                        for token in (
                            "print",
                            "log",
                            "debug",
                            "info",
                            "warn",
                            "error",
                            "trace",
                        )
                    )
                ):
                    add(node, "sensitive logging call")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if re.search(r"(?i)\b(?:https?|wss?)://", node.value):
                add(node, "remote URL literal", node.value)
            if node.value in NETWORK_MODULES | REMOTE_PROVIDER_MODULES:
                add(node, "dynamic network/provider reference", node.value)
            if node.value.upper() in {"POST", "PUT", "PATCH"}:
                add(node, "remote HTTP method literal", node.value)
            if "multipart/form-data" in node.value.lower():
                add(node, "multipart upload content type", node.value)
            if node.value.upper() in REMOTE_CONFIGURATION_KEYS:
                add(node, "remote credential/configuration dependency", node.value)
            if OFFLINE_BLOCKER_PATTERN.search(node.value):
                add(node, "offline blocker", node.value)
            if re.search(
                r"(?i)\b(?:ocr\.space|abbyy|adobe\.pdf|textract|"
                r"form.recognizer|document.intelligence|"
                r"cloud\.vision)\b",
                node.value,
            ):
                add(node, "cloud OCR reference", node.value)
        elif isinstance(node, ast.Name) and node.id.upper() in {
            "ABBYY_API_KEY",
            "ADOBE_CLIENT_ID",
            "ADOBE_CLIENT_SECRET",
            "ANTHROPIC_API_KEY",
            "API_URL",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AZURE_COGNITIVE_SERVICES_KEY",
            "AZURE_COMPUTER_VISION_KEY",
            "AZURE_DOCUMENT_INTELLIGENCE_KEY",
            "AZURE_FORM_RECOGNIZER_KEY",
            "AZURE_OPENAI_API_KEY",
            "BASE_URL",
            "BEDROCK_API_KEY",
            "CLOUD_OCR_URL",
            "COHERE_API_KEY",
            "ENDPOINT",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "GROQ_API_KEY",
            "HF_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "LLM_API_KEY",
            "LLM_BASE_URL",
            "MISTRAL_API_KEY",
            "OCR_API_KEY",
            "OCR_BASE_URL",
            "OCR_SPACE_API_KEY",
            "OPENAI_API_KEY",
            "PERPLEXITY_API_KEY",
            "REMOTE_ENDPOINT",
            "REMOTE_LLM_URL",
            "REMOTE_OCR_URL",
            "REMOTE_URL",
            "TOGETHER_API_KEY",
            "UPLOAD_ENDPOINT",
        }:
            add(node, "remote configuration identifier", node.id)

    return findings


def _scan_generic(
    relative_path: Path,
    text: str,
) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in GENERIC_PRODUCT_RULES:
            if pattern.search(line):
                findings.append(
                    Finding(
                        relative_path.as_posix(),
                        line_number,
                        rule,
                        line.strip()[:160],
                    )
                )
    return findings


def scan_repository(root: Path) -> ScanReport:
    root = root.resolve()
    report = ScanReport()

    for path in _iter_text_files(root):
        relative_path = path.relative_to(root)
        scope = _classify_path(relative_path)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if scope == "product":
            report.product_files_scanned += 1
            if path.suffix.lower() == ".py":
                report.findings.extend(_scan_python(path, relative_path, text))
            else:
                report.findings.extend(_scan_generic(relative_path, text))
        elif CONTEXT_PATTERN.search(text):
            report.context_hits[scope] += 1

    report.findings = sorted(
        set(report.findings),
        key=lambda finding: (finding.path, finding.line, finding.rule),
    )
    return report


def _print_report(report: ScanReport) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(f"Local-only static guardrail: {status}")
    print(f"Product files scanned: {report.product_files_scanned}")
    print(f"Blocking product findings: {len(report.findings)}")

    if report.remote_llm_risks_count:
        print(f"Remote LLM risks: {report.remote_llm_risks_count} finding(s)")
    if report.cloud_ocr_risks_count:
        print(f"Cloud OCR risks: {report.cloud_ocr_risks_count} finding(s)")
    if report.sensitive_log_risks_count:
        print(f"Sensitive log risks: {report.sensitive_log_risks_count} finding(s)")

    if report.context_hits:
        print("Non-blocking context references:")
        for scope, count in sorted(report.context_hits.items()):
            print(f"  - {scope}: {count} file(s)")

    for finding in report.findings:
        risk_level = (
            "CRITICAL"
            if finding.rule
            in REMOTE_LLM_RISK_RULES | CLOUD_OCR_RISK_RULES | SENSITIVE_LOG_RISK_RULES
            else "HIGH"
        )
        print(f"{finding.path}:{finding.line}: {risk_level}: {finding.rule}: {finding.snippet}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect network, upload, provider, and telemetry paths in product code."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to the parent of scripts/).",
    )
    args = parser.parse_args(argv)

    report = scan_repository(args.root)
    _print_report(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
