"""Unit tests for M6-UI Slice 4 calculation preview DTOs and helpers."""

from private_legal_navigator.application.local_confirmation_workspace_service import (
    _OPERATION_LABELS,
    _WARNING_LABELS_PREVIEW,
    _build_trace_step_dto,
)
from private_legal_navigator.application.ui_view_models import (
    CalculationPreviewResultDTO,
    CalculationPreviewView,
    CalculationTraceStepDTO,
)
from private_legal_navigator.domain.reference_event import (
    CalculationOperation,
    CalculationStep,
)


class TestCalculationTraceStepDTO:
    def test_trace_step_contains_no_internal_ids(self):
        """Trace DTO has no UUID or internal ID fields."""
        dto = CalculationTraceStepDTO(
            step_number=1,
            operation_label="Addition von Kalendertagen",
            input_date_iso="2026-06-15",
            input_date_display="15.06.2026",
            amount=14,
            output_date_iso="2026-06-29",
            output_date_display="29.06.2026",
        )
        # Verify all fields are display-formatted strings, not internal IDs
        assert "UUID" not in str(dto.__dict__)
        assert "confirmation" not in str(dto.__dict__).lower()

    def test_trace_step_all_fields_set(self):
        """All DTO fields must be set on construction."""
        dto = CalculationTraceStepDTO(
            step_number=2,
            operation_label="Addition von Kalenderwochen",
            input_date_iso="2026-01-01",
            input_date_display="01.01.2026",
            amount=7,
            output_date_iso="2026-01-08",
            output_date_display="08.01.2026",
        )
        assert dto.step_number == 2
        assert dto.amount == 7
        assert dto.output_date_display == "08.01.2026"


class TestCalculationPreviewResultDTO:
    def test_preview_result_has_safety_flags(self):
        """Result DTO always has safety flags set."""
        result = CalculationPreviewResultDTO(
            calculated_date_iso="2026-08-14",
            calculated_date_display="14.08.2026",
            reference_date_iso="2026-07-31",
            reference_date_display="31.07.2026",
            duration_amount=14,
            duration_unit="Tag",
            duration_calendar_days=14,
        )
        assert result.human_review_required is True
        assert result.legal_validity_assessed is False
        assert result.is_preview_only is True

    def test_preview_result_with_trace_and_warnings(self):
        """Result DTO can hold trace steps and warnings."""
        steps = [
            CalculationTraceStepDTO(
                step_number=1,
                operation_label="Addition von Kalendertagen",
                input_date_iso="2026-07-31",
                input_date_display="31.07.2026",
                amount=14,
                output_date_iso="2026-08-14",
                output_date_display="14.08.2026",
            )
        ]
        result = CalculationPreviewResultDTO(
            calculated_date_iso="2026-08-14",
            calculated_date_display="14.08.2026",
            reference_date_iso="2026-07-31",
            reference_date_display="31.07.2026",
            duration_amount=14,
            duration_unit="Tag",
            duration_calendar_days=14,
            trace_steps=steps,
            warnings=["Testwarnung"],
        )
        assert len(result.trace_steps) == 1
        assert result.trace_steps[0].output_date_iso == "2026-08-14"
        assert len(result.warnings) == 1


class TestCalculationPreviewView:
    def test_preview_view_without_confirmation(self):
        """View without active confirmation shows correct flags."""
        view = CalculationPreviewView(
            case_id="case-uuid",
            document_id="doc-uuid",
            candidate_index=1,
            document_filename="test.pdf",
            case_label="Test Case",
            active_confirmation_id="",
            active_confirmation_date_display="",
            active_confirmation_status="",
        )
        assert view.has_active_confirmation is False
        assert view.preview_result is None
        assert view.human_review_required is True
        assert view.legal_validity_assessed is False

    def test_preview_view_with_result(self):
        """View with result keeps reference to the result DTO."""
        result = CalculationPreviewResultDTO(
            calculated_date_iso="2026-08-14",
            calculated_date_display="14.08.2026",
            reference_date_iso="2026-07-31",
            reference_date_display="31.07.2026",
            duration_amount=14,
            duration_unit="Tag",
            duration_calendar_days=14,
        )
        view = CalculationPreviewView(
            case_id="case-uuid",
            document_id="doc-uuid",
            candidate_index=1,
            document_filename="test.pdf",
            case_label="Test Case",
            active_confirmation_id="active-id",
            active_confirmation_date_display="31.07.2026",
            active_confirmation_status="confirmed",
            preview_result=result,
            has_active_confirmation=True,
        )
        assert view.preview_result is not None
        assert view.preview_result.calculated_date_display == "14.08.2026"
        assert view.active_confirmation_date_display == "31.07.2026"


class TestBuildTraceStepDTO:
    def test_build_trace_step_from_domain_step(self):
        """Domain CalculationStep transforms to display-safe DTO."""
        from datetime import date

        domain_step = CalculationStep(
            step=1,
            operation=CalculationOperation.ADD_CALENDAR_DAYS,
            input_date=date(2026, 7, 31),
            amount=14,
            output_date=date(2026, 8, 14),
        )
        dto = _build_trace_step_dto(domain_step)
        assert dto.step_number == 1
        assert dto.operation_label == "Addition von Kalendertagen"
        assert dto.input_date_display == "31.07.2026"
        assert dto.output_date_display == "14.08.2026"
        assert dto.amount == 14

    def test_build_trace_step_week_operation(self):
        """Week operation gets correct label."""
        from datetime import date

        domain_step = CalculationStep(
            step=1,
            operation=CalculationOperation.ADD_CALENDAR_WEEKS,
            input_date=date(2026, 1, 1),
            amount=7,
            output_date=date(2026, 1, 8),
        )
        dto = _build_trace_step_dto(domain_step)
        assert dto.operation_label == "Addition von Kalenderwochen"


class TestOperationLabels:
    def test_all_operations_have_labels(self):
        """Every CalculationOperation has a German label."""
        for op in CalculationOperation:
            assert op in _OPERATION_LABELS, f"Missing label for {op}"
            assert isinstance(_OPERATION_LABELS[op], str)
            assert len(_OPERATION_LABELS[op]) > 0


class TestWarningLabels:
    def test_warning_labels_are_german(self):
        """All warning labels are non-empty German strings."""
        assert len(_WARNING_LABELS_PREVIEW) > 0
        for key, value in _WARNING_LABELS_PREVIEW.items():
            assert isinstance(value, str), f"Label for {key} is not a string"
            assert len(value) > 0, f"Label for {key} is empty"
