"""Exact fixture-label and source-span checks; deliberately no model-as-judge."""

from .contracts import Case, Extraction, Record, strict_json


def evaluate(case: Case, record: Record) -> dict:
    issues = []
    if record.status != "OK":
        return {"passed": False, "issues": [record.status], "actual": None}
    try:
        value = Extraction.model_validate(strict_json(record.raw or ""))
    except (ValueError, TypeError, RecursionError):
        return {"passed": False, "issues": ["OUTPUT_SCHEMA"], "actual": None}
    for field in ("action", "source", "target", "deadline", "review_required"):
        actual = getattr(value, field)
        expected = getattr(case.expected, field)
        if actual != expected:
            issues.append("LABEL_" + field.upper())
    for field in ("source", "target", "deadline"):
        actual = getattr(value, field)
        quote = getattr(value.evidence, field)
        if actual is None:
            if quote is not None:
                issues.append("UNEXPECTED_EVIDENCE_" + field.upper())
        elif quote is None or quote not in case.input or actual not in quote:
            issues.append("UNSUPPORTED_SPAN_" + field.upper())
    return {"passed": not issues, "issues": issues, "actual": value.model_dump()}
