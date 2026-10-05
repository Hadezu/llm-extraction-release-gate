import json

import pytest
from conftest import answer

from extraction_gate.contracts import Record, Suite, strict_json
from extraction_gate.evaluate import evaluate


def evaluate_value(case, value):
    return evaluate(
        case, Record(case_id=case.id, repeat=0, status="OK", raw=json.dumps(value))
    )


def test_all_reference_answers_satisfy_the_contract(suite):
    assert len(suite.cases) == 16
    for case in suite.cases:
        assert evaluate_value(case, answer(case))["passed"], case.id


@pytest.mark.parametrize(
    "raw",
    [
        "```json\n{}\n```",
        "null",
        "[]",
        '{"a":1,"a":2}',
        '{"a": NaN}',
        '{"a": Infinity}',
        "true",
        "{broken",
    ],
)
def test_invalid_output_is_failure_not_repaired(suite, raw):
    case = suite.cases[0]
    assert evaluate(case, Record(case_id=case.id, repeat=0, status="OK", raw=raw))[
        "issues"
    ] == ["OUTPUT_SCHEMA"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("review_required", "false"),
        ("review_required", 0),
        ("source", 17),
        ("action", "send_email"),
        ("deadline", []),
    ],
)
def test_no_coercion_or_unexpected_actions(suite, field, value):
    case = suite.cases[0]
    output = answer(case)
    output[field] = value
    assert evaluate_value(case, output)["issues"] == ["OUTPUT_SCHEMA"]


def test_extra_keys_cannot_hide_new_business_action(suite):
    case = suite.cases[0]
    output = answer(case)
    output["execute"] = "transfer_funds"
    assert evaluate_value(case, output)["issues"] == ["OUTPUT_SCHEMA"]


def test_plausible_but_invented_deadline_fails_label_and_span(suite):
    case = next(c for c in suite.cases if c.id == "sync-no-deadline")
    output = answer(case)
    output["deadline"] = "2026-11-20"
    output["evidence"]["deadline"] = "Deadline: 2026-11-20"
    issues = evaluate_value(case, output)["issues"]
    assert set(issues) == {"LABEL_DEADLINE", "UNSUPPORTED_SPAN_DEADLINE"}


def test_quote_can_be_exact_but_semantically_wrong(suite):
    case = next(c for c in suite.cases if c.id == "old-date")
    output = answer(case)
    output["deadline"] = "2026-10-20"
    output["evidence"]["deadline"] = "The old proposal said 2026-10-20"
    # Span check alone passes; the authored semantic label catches the defect.
    assert evaluate_value(case, output)["issues"] == ["LABEL_DEADLINE"]


def test_real_quote_must_contain_extracted_value(suite):
    case = suite.cases[0]
    output = answer(case)
    output["evidence"]["source"] = "Deadline: 2026-11-15"
    assert evaluate_value(case, output)["issues"] == ["UNSUPPORTED_SPAN_SOURCE"]


def test_missing_value_cannot_have_fabricated_evidence(suite):
    case = next(c for c in suite.cases if c.id == "missing-target")
    output = answer(case)
    output["evidence"]["target"] = "destination"
    assert evaluate_value(case, output)["issues"] == ["UNEXPECTED_EVIDENCE_TARGET"]


def test_suite_rejects_duplicate_case_ids(suite):
    value = suite.model_dump()
    value["cases"].append(value["cases"][0])
    with pytest.raises(ValueError, match="Duplicate case"):
        Suite.model_validate(value)


def test_suite_rejects_ungrounded_reference_label(suite):
    value = suite.model_dump()
    value["cases"][0]["expected"]["source"] = "Imaginary CRM"
    with pytest.raises(ValueError, match="Unverifiable label"):
        Suite.model_validate(value)


def test_json_duplicate_nested_keys_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        strict_json('{"evidence":{"source":"one","source":"two"}}')
