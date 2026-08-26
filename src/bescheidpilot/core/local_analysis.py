"""Local analysis functions for BescheidPilot — no I/O, no network, no cloud."""

from dataclasses import dataclass

from .extraction import extract_bescheid_facts
from .models import BescheidAnalysisResult
from .review import build_review_gate


@dataclass(frozen=True, slots=True)
class LocalAnalysisResult:
    """Non-sensitive structural facts derived from local text."""

    analysis_mode: str
    execution_mode: str
    network_required: bool
    character_count: int
    line_count: int
    paragraph_count: int
    has_content: bool


def analyze_local_text(text: str) -> LocalAnalysisResult:
    """Return local structural metadata without retaining or transmitting text.

    This function is used by the guardrail test harness and must remain
    side-effect-free, network-free, and log-free.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return _analyze_structure(text)


def _analyze_structure(text: str) -> LocalAnalysisResult:
    lines = text.splitlines()
    paragraph_count = 0
    inside_paragraph = False

    for line in lines:
        if line.strip():
            if not inside_paragraph:
                paragraph_count += 1
            inside_paragraph = True
        else:
            inside_paragraph = False

    return LocalAnalysisResult(
        analysis_mode="local-structure-baseline",
        execution_mode="offline",
        network_required=False,
        character_count=len(text),
        line_count=len(lines),
        paragraph_count=paragraph_count,
        has_content=bool(text.strip()),
    )


def analyze_bescheid_text(text: str) -> BescheidAnalysisResult:
    """Analyse a Bescheid document and return structured facts with evidence.

    This is the first real product Vertical Slice: deterministic,
    local-only extraction of authority, document type, deadlines,
    required actions, missing documents, and risk level — each
    anchored by source evidence.

    No network, no remote LLM, no cloud OCR, no telemetry.
    Sensitive content is not logged.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return build_review_gate(extract_bescheid_facts(text))


def safe_analyze_bescheid_text(text: str) -> BescheidAnalysisResult:
    """Same as analyze_bescheid_text but with redacted logging safety.

    In case a future logging path needs to emit diagnostic information,
    this wrapper ensures sensitive content is redacted first.
    """
    result = analyze_bescheid_text(text)

    # If we ever add logging here, redact first:
    # log_safe = redact_sensitive_text(str(result))
    # logger.info(log_safe)

    return result
