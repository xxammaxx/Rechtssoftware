"""Regression tests for v1.0.0rc2 local UI security hardening."""

import tomllib
from pathlib import Path

import pytest
from starlette.requests import Request

from private_legal_navigator.middleware.security_dependencies import _is_same_origin

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _local_request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/ui/cases",
            "raw_path": b"/ui/cases",
            "query_string": b"",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 8000),
        }
    )


@pytest.mark.parametrize(
    ("header_value", "expected"),
    [
        ("http://127.0.0.1.evil.example", False),
        ("http://localhost.evil.example", False),
        ("http://127.0.0.1:8000.evil.example", False),
        ("http://127.0.0.1:8000", True),
        ("http://localhost:8000", True),
        ("http://127.0.0.1:8001", False),
        ("", False),
        ("http://127.0.0.1:bad-port", False),
        ("not-a-url", False),
    ],
)
def test_structured_local_origin_validation_rejects_prefix_and_invalid_inputs(
    header_value: str, expected: bool
) -> None:
    """Only structurally valid local headers may pass the CSRF origin gate."""
    assert _is_same_origin(header_value, _local_request()) is expected


def test_explicit_template_autoescape_escapes_controlled_html_payload(tmp_path) -> None:
    """The named autoescape callable must protect dynamic HTML in templates."""
    from private_legal_navigator.app import create_app, template_autoescape
    from private_legal_navigator.config import Settings

    app = create_app(Settings(data_dir=tmp_path))
    rendered = app.state.templates.env.from_string("<p>{{ payload }}</p>").render(
        payload='<img src=x onerror="alert(1)">'
    )

    assert template_autoescape("m7a/norm_detail.html") is True
    assert template_autoescape("plain.txt") is False
    assert '<img src=x onerror="alert(1)">' not in rendered
    assert "&lt;img src=x onerror=&#34;alert(1)&#34;&gt;" in rendered


def test_norm_detail_has_no_inline_script_and_uses_local_asset() -> None:
    """Norm detail behavior is supplied by a local CSP-compatible script."""
    template = (
        PROJECT_ROOT / "src/private_legal_navigator/presentation/templates/m7a/norm_detail.html"
    ).read_text(encoding="utf-8")
    script = PROJECT_ROOT / "src/private_legal_navigator/presentation/static/js/norm-detail.js"

    assert "<script>" not in template
    assert "onchange=" not in template
    assert "static', path='js/norm-detail.js'" in template
    assert script.is_file()


def test_package_metadata_includes_local_norm_detail_script() -> None:
    """The wheel declaration contains the truthful v1.0.0rc2 static JS asset."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]

    version = pyproject["project"]["version"]
    assert isinstance(version, str) and len(version) > 0
    assert "static/**/*.js" in package_data["private_legal_navigator.presentation"]
