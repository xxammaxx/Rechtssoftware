"""Unit tests for typed form-data extractors (form_helpers.py)."""

import io

import pytest
from starlette.datastructures import FormData, UploadFile

from private_legal_navigator.api.form_helpers import (
    DuplicateFormField,
    InvalidFormField,
    MissingFormField,
    optional_form_string,
    require_form_string,
)


def _make_form(**kwargs: str) -> FormData:
    """Create a FormData instance from keyword arguments."""
    return FormData(list(kwargs.items()))


def _make_file_form(key: str, filename: str, content: bytes) -> FormData:
    """Create a FormData with an UploadFile value."""
    upload = UploadFile(file=io.BytesIO(content), filename=filename, size=len(content))
    return FormData([(key, upload)])


def _make_duplicate_form(key: str, value1: str, value2: str) -> FormData:
    """Create a FormData with duplicate values for a key."""
    return FormData([(key, value1), (key, value2)])


class TestRequireFormString:
    def test_returns_trimmed_string(self):
        form = _make_form(name="  hello  ")
        result = require_form_string(form, "name")
        assert result == "hello"

    def test_raises_missing_when_absent(self):
        form = _make_form(other="value")
        with pytest.raises(MissingFormField):
            require_form_string(form, "name")

    def test_raises_missing_when_empty(self):
        form = _make_form(name="   ")
        with pytest.raises(MissingFormField):
            require_form_string(form, "name")

    def test_raises_invalid_for_upload_file(self):
        form = _make_file_form("name", "test.txt", b"content")
        with pytest.raises(InvalidFormField):
            require_form_string(form, "name")

    def test_raises_invalid_when_too_long(self):
        form = _make_form(name="A" * 5000)
        with pytest.raises(InvalidFormField):
            require_form_string(form, "name", max_length=100)

    def test_accepts_value_within_limit(self):
        form = _make_form(name="A" * 50)
        result = require_form_string(form, "name", max_length=100)
        assert len(result) == 50

    def test_raises_duplicate_for_multiple_values(self):
        form = _make_duplicate_form("name", "first", "second")
        with pytest.raises(DuplicateFormField):
            require_form_string(form, "name")


class TestOptionalFormString:
    def test_returns_trimmed_string(self):
        form = _make_form(name="  world  ")
        result = optional_form_string(form, "name")
        assert result == "world"

    def test_returns_none_when_absent(self):
        form = _make_form(other="value")
        result = optional_form_string(form, "name")
        assert result is None

    def test_returns_none_when_empty(self):
        form = _make_form(name="   ")
        result = optional_form_string(form, "name")
        assert result is None

    def test_raises_invalid_for_upload_file(self):
        form = _make_file_form("note", "note.txt", b"uploaded")
        with pytest.raises(InvalidFormField):
            optional_form_string(form, "note")

    def test_raises_invalid_when_too_long(self):
        form = _make_form(note="B" * 5000)
        with pytest.raises(InvalidFormField):
            optional_form_string(form, "note", max_length=100)

    def test_accepts_value_within_limit(self):
        form = _make_form(note="B" * 80)
        result = optional_form_string(form, "note", max_length=100)
        assert len(result) == 80

    def test_raises_duplicate_for_multiple_values(self):
        form = _make_duplicate_form("note", "first", "second")
        with pytest.raises(DuplicateFormField):
            optional_form_string(form, "note")
