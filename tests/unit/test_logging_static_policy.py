"""Static policy guard: prevent unsafe logging patterns in product code.

The PrivacyRedactionFilter is key-based — it redacts specific field names
in extra dicts and mapping args. It CANNOT reliably detect:

1. f-string interpolation:  logger.info(f"id={sensitive_uuid}")
2. Positional %s args:       logger.info("id=%s", sensitive_uuid)
3. Sensitive data in exception messages

This module provides an AST-based guard that scans product code for these
unsafe patterns and enforces the structured logging policy:

    CORRECT:  logger.info("event", extra={"document_id": uuid})
    WRONG:    logger.info(f"document_id={uuid}")
    WRONG:    logger.info("document_id=%s", uuid)

The static check runs as a test so it gates CI/commits.
"""

from __future__ import annotations

import ast
import pathlib
from typing import NamedTuple

import pytest

# ── Configuration ──────────────────────────────────────────────────────────

PRODUCT_SRC = pathlib.Path("src/private_legal_navigator")

SENSITIVE_IDENTIFIERS: frozenset[str] = frozenset(
    {
        "confirmed_date",
        "reference_date",
        "calculated_date",
        "suggested_date",
        "evidence_text",
        "evidence_note",
        "source_text",
        "document_id",
        "confirmation_id",
        "case_id",
        "candidate_id",
        "deadline_candidate_id",
        "reference_event_candidate_id",
        "supersedes_confirmation_id",
    }
)

SAFE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "INVALID_CONFIRMATION_CONTEXT",
        "DOCUMENT_NOT_FOUND",
        "CASE_NOT_FOUND",
        "UNSUPPORTED_DURATION_UNIT",
        "AMBIGUOUS_DATE",
    }
)


class LoggingViolation(NamedTuple):
    """A detected unsafe logging pattern."""

    file: str
    line: int
    pattern: str
    detail: str


# ── AST Visitor ────────────────────────────────────────────────────────────


class LoggingPolicyVisitor(ast.NodeVisitor):
    """Walk AST and detect unsafe logger calls."""

    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[LoggingViolation] = []

    def _is_logger_call(self, node: ast.Call) -> bool:
        """Check if a call is a logger method call."""
        if not isinstance(node.func, ast.Attribute):
            return False
        method = node.func.attr
        if method not in {"debug", "info", "warning", "error", "exception", "critical"}:
            return False
        # Must be called on something named 'logger' (typical convention)
        return isinstance(node.func.value, ast.Name) and "log" in node.func.value.id.lower()

    def _has_sensitive_identifier(self, node: ast.expr) -> bool:
        """Check if an AST expression contains a sensitive identifier."""
        if isinstance(node, ast.Name):
            return node.id in SENSITIVE_IDENTIFIERS
        if isinstance(node, ast.Attribute):
            return node.attr in SENSITIVE_IDENTIFIERS
        # Tuple/list: check all elements
        if isinstance(node, ast.Tuple):
            return any(self._has_sensitive_identifier(elt) for elt in node.elts)
        return False

    def visit_Call(self, node: ast.Call) -> None:
        """Check logger calls for unsafe patterns."""
        if not self._is_logger_call(node):
            self.generic_visit(node)
            return

        # Pattern A: f-string in positional arg
        #   logger.info(f"document_id={uuid}")
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):  # f-string
                for value in arg.values:
                    if isinstance(value, ast.FormattedValue) and self._has_sensitive_identifier(
                        value.value
                    ):
                        self.violations.append(
                            LoggingViolation(
                                file=self.filename,
                                line=node.lineno,
                                pattern="FSTRING_WITH_SENSITIVE_IDENTIFIER",
                                detail=(
                                    f"f-string with sensitive identifier at line {node.lineno}"
                                ),
                            )
                        )

        # Pattern B: positional %s with sensitive identifier
        #   logger.info("document_id=%s", uuid)
        # Check if second+ args are sensitive identifiers
        if len(node.args) >= 2:
            # First arg is the message template string
            msg = node.args[0]
            if isinstance(msg, ast.Constant) and isinstance(msg.value, str) and "%" in msg.value:
                # Check remaining positional args for sensitive identifiers
                for arg in node.args[1:]:
                    if self._has_sensitive_identifier(arg):
                        self.violations.append(
                            LoggingViolation(
                                file=self.filename,
                                line=node.lineno,
                                pattern="POSITIONAL_ARG_WITH_SENSITIVE_IDENTIFIER",
                                detail=(
                                    f"%-format with sensitive identifier at line {node.lineno}"
                                ),
                            )
                        )
                        break

        # Pattern C: .format() call with sensitive identifier
        #   logger.info("id={}".format(uuid))
        for arg in node.args:
            if (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and arg.func.attr == "format"
            ):
                for kw in arg.keywords:
                    if self._has_sensitive_identifier(kw.value):
                        self.violations.append(
                            LoggingViolation(
                                file=self.filename,
                                line=node.lineno,
                                pattern="FORMAT_WITH_SENSITIVE_IDENTIFIER",
                                detail=(
                                    f".format() with sensitive identifier at line {node.lineno}"
                                ),
                            )
                        )

        # Pattern D: String concatenation with sensitive identifier
        #   logger.info("id=" + str(uuid))
        for arg in node.args:
            if (
                isinstance(arg, ast.BinOp)
                and isinstance(arg.op, ast.Add)
                and (
                    self._has_sensitive_identifier(arg.left)
                    or self._has_sensitive_identifier(arg.right)
                )
            ):
                self.violations.append(
                    LoggingViolation(
                        file=self.filename,
                        line=node.lineno,
                        pattern="CONCAT_WITH_SENSITIVE_IDENTIFIER",
                        detail=(
                            f"String concatenation with sensitive identifier at line {node.lineno}"
                        ),
                    )
                )

        self.generic_visit(node)


# ── Scanner ────────────────────────────────────────────────────────────────


def scan_product_code() -> list[LoggingViolation]:
    """Scan all product code for unsafe logging patterns."""
    violations: list[LoggingViolation] = []
    src_root = PRODUCT_SRC

    if not src_root.exists():
        return violations

    for py_file in src_root.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        source_lines = source.splitlines()
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        visitor = LoggingPolicyVisitor(str(py_file), source_lines)
        visitor.visit(tree)
        violations.extend(visitor.violations)

    return violations


# ── Pytest integration ─────────────────────────────────────────────────────


def test_no_unsafe_logging_patterns_in_product_code():
    """STATIC GUARD: Product code must not use unsafe logging patterns.

    This test fails if any product code file uses:
    - f-strings with sensitive identifiers in logger calls
    - positional %s with sensitive identifiers in logger calls
    - .format() with sensitive identifiers in logger calls
    - String concatenation with sensitive identifiers in logger calls

    The correct pattern is structured logging:
        logger.info("event_name", extra={"document_id": uuid})
    """
    violations = scan_product_code()

    if violations:
        msg_lines = ["Unsafe logging patterns detected in product code:"]
        for v in violations:
            msg_lines.append(f"  {v.file}:{v.line} — {v.pattern}: {v.detail}")
        msg_lines.append(
            '\nUse structured logging instead:\n  logger.info("event", extra={"document_id": uuid})'
        )
        pytest.fail("\n".join(msg_lines))

    # Test passes: no violations
    assert len(violations) == 0
