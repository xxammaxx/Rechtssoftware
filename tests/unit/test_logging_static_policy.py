"""Static boundary guard: enforce logging policy across ALL product code.

The guard scans every product Python file and blocks:
  1. Direct logger calls (logger.info, self.logger.error, audit.warning, ...)
     regardless of variable name or alias — NO logger method calls allowed
     outside explicitly authorized infrastructure files.
  2. safe_log_event / safe_log_failure with non-literal event_name/error_code
     (f-string, variable, expression).
  3. Exception creation (raise X(...)) with f-strings containing
     sensitive identifiers or UUID/date/path patterns.
  4. exc_info=True on any log call.

Authorized files (may call loggers directly):
  - infrastructure/safe_logging.py
  - infrastructure/log_redaction.py

This guard replaces the old name-based heuristic ("log" in variable name)
with a true boundary guard: ANY logger method call in product code is a
violation unless the file is explicitly authorized.
"""

from __future__ import annotations

import ast
import pathlib
from typing import NamedTuple

import pytest

# ── Configuration ──────────────────────────────────────────────────────────

PRODUCT_SRC = pathlib.Path("src/private_legal_navigator")

# Files authorized to call logging methods directly
AUTHORIZED_FILES: frozenset[str] = frozenset(
    {
        "src/private_legal_navigator/infrastructure/safe_logging.py",
        "src/private_legal_navigator/infrastructure/log_redaction.py",
    }
)

# Logger method names that are FORBIDDEN in unauthorized files
LOGGER_METHODS: frozenset[str] = frozenset(
    {"debug", "info", "warning", "error", "exception", "critical"}
)

# Sensitive identifiers — when found in f-string expressions inside
# raise statements, they indicate a potential leak
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
        "storage_path",
        "uuid",
        "uuid4",
        "uid",
    }
)

# Variable name patterns that suggest a logger instance
LOGGER_NAME_PATTERNS: tuple[str, ...] = ("logger", "log", "audit")


class LoggingViolation(NamedTuple):
    """A detected policy violation."""

    file: str
    line: int
    pattern: str
    detail: str


# ── AST Visitor ────────────────────────────────────────────────────────────


class BoundaryPolicyVisitor(ast.NodeVisitor):
    """Walk AST and enforce the logging boundary policy."""

    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[LoggingViolation] = []
        self._is_authorized = filename in AUTHORIZED_FILES
        self._imported_logging = False

    # ── Import tracking ───────────────────────────────────────────────────

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "logging":
                self._imported_logging = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "logging":
            self._imported_logging = True
        self.generic_visit(node)

    # ── Call detection ────────────────────────────────────────────────────

    def _is_logger_method_call(self, node: ast.Call) -> bool:
        """Check if a call is ANY logger method on ANY object."""
        if not isinstance(node.func, ast.Attribute):
            return False
        return node.func.attr in LOGGER_METHODS

    def _is_safe_logging_call(self, node: ast.Call) -> bool:
        """Check if a call is safe_log_event or safe_log_failure."""
        if isinstance(node.func, ast.Name):
            return node.func.id in {"safe_log_event", "safe_log_failure"}
        return False

    def _has_sensitive_expr(self, node: ast.expr) -> bool:
        """Check if an AST expression contains a sensitive identifier."""
        if isinstance(node, ast.Name):
            return node.id in SENSITIVE_IDENTIFIERS
        if isinstance(node, ast.Attribute):
            return node.attr in SENSITIVE_IDENTIFIERS
        if isinstance(node, ast.Tuple):
            return any(self._has_sensitive_expr(elt) for elt in node.elts)
        if isinstance(node, ast.JoinedStr):  # f-string
            for value in node.values:
                if isinstance(value, ast.FormattedValue) and self._has_sensitive_expr(value.value):
                    return True
        return False

    def _is_string_literal(self, node: ast.expr) -> bool:
        """Check if a node is a plain string literal (not f-string, not variable)."""
        return isinstance(node, ast.Constant) and isinstance(node.value, str)

    def visit_Call(self, node: ast.Call) -> None:
        """Check all call patterns for violations."""
        # ── Pattern A: Direct logger method call in unauthorized file ──
        if not self._is_authorized and self._is_logger_method_call(node):
            self.violations.append(
                LoggingViolation(
                    file=self.filename,
                    line=node.lineno,
                    pattern="DIRECT_LOGGER_CALL",
                    detail=(
                        f"Direct logger.{node.func.attr}() call at line {node.lineno}. "
                        f"Use safe_log_event() or safe_log_failure() instead."
                    ),
                )
            )

        # ── Pattern B: safe_log_event/safe_log_failure with non-literal event_name ──
        if self._is_safe_logging_call(node):
            func_name = node.func.id  # type: ignore[attr-defined]
            # First positional arg is event_name
            if len(node.args) >= 2:
                event_arg = node.args[1]  # after logger arg
                if not self._is_string_literal(event_arg):
                    self.violations.append(
                        LoggingViolation(
                            file=self.filename,
                            line=node.lineno,
                            pattern="NON_LITERAL_EVENT_NAME",
                            detail=(
                                f"{func_name}() with non-literal event_name "
                                f"at line {node.lineno}. Event names must be "
                                f"string literals."
                            ),
                        )
                    )
                # Check keyword error_code
                for kw in node.keywords:
                    if kw.arg == "error_code" and not self._is_string_literal(kw.value):
                        self.violations.append(
                            LoggingViolation(
                                file=self.filename,
                                line=node.lineno,
                                pattern="NON_LITERAL_ERROR_CODE",
                                detail=(
                                    f"safe_log_failure() with non-literal error_code "
                                    f"at line {node.lineno}. Error codes must be "
                                    f"string literals."
                                ),
                            )
                        )

        # ── Pattern C: exc_info=True ──
        for kw in node.keywords:
            if (
                kw.arg == "exc_info"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
            ):
                self.violations.append(
                    LoggingViolation(
                        file=self.filename,
                        line=node.lineno,
                        pattern="EXC_INFO_TRUE",
                        detail=(
                            f"exc_info=True at line {node.lineno}. "
                            f"Using exc_info emits full traceback with local variables."
                        ),
                    )
                )

        self.generic_visit(node)

    # ── Raise detection ───────────────────────────────────────────────────

    def visit_Raise(self, node: ast.Raise) -> None:
        """Check raise statements for sensitive f-string content."""
        if node.exc is None:
            return

        # Check raise X(f"...")
        if isinstance(node.exc, ast.Call):
            # Check all arguments for f-strings with sensitive identifiers
            for arg in node.exc.args:
                if isinstance(arg, ast.JoinedStr):  # f-string
                    for value in arg.values:
                        if isinstance(value, ast.FormattedValue) and self._has_sensitive_expr(
                            value.value
                        ):
                            self.violations.append(
                                LoggingViolation(
                                    file=self.filename,
                                    line=node.lineno,
                                    pattern="RAISE_FSTRING_WITH_SENSITIVE",
                                    detail=(
                                        f"raise with f-string containing sensitive "
                                        f"identifier at line {node.lineno}. Exception "
                                        f"messages must not contain case/reference data."
                                    ),
                                )
                            )
                        elif (
                            isinstance(value, ast.FormattedValue)
                            and isinstance(value.value, ast.Call)
                            and isinstance(value.value.func, ast.Name)
                            and value.value.func.id == "str"
                        ):
                            self.violations.append(
                                LoggingViolation(
                                    file=self.filename,
                                    line=node.lineno,
                                    pattern="RAISE_FSTRING_WITH_CONVERSION",
                                    detail=(
                                        f"raise with f-string containing str() conversion "
                                        f"at line {node.lineno}. Exception messages must "
                                        f"not contain converted values."
                                    ),
                                )
                            )

        self.generic_visit(node)


# ── Scanner ────────────────────────────────────────────────────────────────


def scan_product_code() -> list[LoggingViolation]:
    """Scan all product code for policy violations."""
    violations: list[LoggingViolation] = []
    src_root = PRODUCT_SRC

    if not src_root.exists():
        return violations

    for py_file in src_root.rglob("*.py"):
        file_str = str(py_file).replace("\\", "/")
        try:
            source = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        source_lines = source.splitlines()
        try:
            tree = ast.parse(source, filename=file_str)
        except SyntaxError:
            continue

        visitor = BoundaryPolicyVisitor(file_str, source_lines)
        visitor.visit(tree)
        violations.extend(visitor.violations)

    return violations


# ── Pytest integration ─────────────────────────────────────────────────────


def test_no_direct_logger_calls_in_product_code():
    """BOUNDARY GUARD: All product files outside authorized logging
    infrastructure must NOT call logger methods directly."""
    violations = scan_product_code()
    if violations:
        msg_lines = ["Logging policy violations in product code:"]
        for v in violations:
            msg_lines.append(f"  {v.file}:{v.line} — {v.pattern}: {v.detail}")
        pytest.fail("\n".join(msg_lines))
    assert len(violations) == 0


# ── Targeted negative tests (RED_TEST — prove guard catches violations) ────


def test_guard_blocks_logger_info():
    """The guard must detect logger.info() in product code."""
    code = "logger.info('msg', extra={'document_id': 'x'})"
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    assert len(visitor.violations) >= 1, "Guard failed to detect logger.info()"
    assert any(v.pattern == "DIRECT_LOGGER_CALL" for v in visitor.violations)


def test_guard_blocks_self_logger_error():
    """The guard must detect self.logger.error() in product code."""
    code = "self.logger.error('msg')"
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    assert len(visitor.violations) >= 1, "Guard failed to detect self.logger.error()"


def test_guard_blocks_logging_dot_error():
    """The guard must detect logging.error() in product code."""
    code = "import logging; logging.error('msg')"
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    assert len(visitor.violations) >= 1, "Guard failed to detect logging.error()"


def test_guard_blocks_audit_alias():
    """The guard must detect arbitrary alias logger calls."""
    code = "audit_logger.warning('msg')"
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    assert len(visitor.violations) >= 1, "Guard failed to detect audit_logger.warning()"


def test_guard_blocks_exc_info_true():
    """The guard must detect exc_info=True."""
    code = "logger.info('msg', exc_info=True)"
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    assert len(visitor.violations) >= 1, "Guard failed to detect exc_info=True"


def test_guard_blocks_raise_fstring_with_sensitive():
    """The guard must detect raise with f-string containing sensitive field."""
    code = 'raise ValueError(f"confirm_id={confirmation_id}")'
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    violations = [v for v in visitor.violations if v.pattern == "RAISE_FSTRING_WITH_SENSITIVE"]
    assert len(violations) >= 1, "Guard failed to detect raise f-string with sensitive identifier"


def test_guard_allows_authorized_files():
    """The guard must not flag safe_logging.py for direct logger calls."""
    code = "logger.info('msg', extra={'document_id': 'x'})"
    tree = ast.parse(code)
    # This file is in the AUTHORIZED set
    authorized_path = "src/private_legal_navigator/infrastructure/safe_logging.py"
    visitor = BoundaryPolicyVisitor(authorized_path, code.splitlines())
    visitor.visit(tree)
    direct_violations = [v for v in visitor.violations if v.pattern == "DIRECT_LOGGER_CALL"]
    assert len(direct_violations) == 0, (
        f"Guard incorrectly flagged authorized file: {direct_violations}"
    )


def test_guard_blocks_non_literal_event_name():
    """The guard must detect safe_log_event with variable event_name."""
    code = 'safe_log_event(logger, event_var, key="value")'
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    violations = [v for v in visitor.violations if v.pattern == "NON_LITERAL_EVENT_NAME"]
    assert len(violations) >= 1, "Guard failed to detect non-literal event_name"


def test_guard_blocks_non_literal_error_code():
    """The guard must detect safe_log_failure with variable error_code."""
    code = 'safe_log_failure(logger, "event", error_code=str(exc))'
    tree = ast.parse(code)
    visitor = BoundaryPolicyVisitor("src/private_legal_navigator/api/test.py", code.splitlines())
    visitor.visit(tree)
    violations = [v for v in visitor.violations if v.pattern == "NON_LITERAL_ERROR_CODE"]
    assert len(violations) >= 1, "Guard failed to detect non-literal error_code"
