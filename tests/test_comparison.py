import json

import pytest

from extraction_gate.compare import Policy, compare
from extraction_gate.contracts import Settings
from extraction_gate.report import write_report


def wrong(record, field="action", value="unknown"):
    data = json.loads(record.raw)
    data[field] = value
    return record.model_copy(update={"raw": json.dumps(data)})


def test_higher_aggregate_cannot_hide_critical_regression(make_run):
    baseline = make_run(
        "baseline",
        lambda r, c: (
            wrong(r)
            if c.id in {"daily-sync", "one-time-import", "reporting-request"}
            else r
        ),
    )
    candidate = make_run(
        "candidate",
        lambda r, c: (
            wrong(r, "deadline", "2026-11-20") if c.id == "sync-no-deadline" else r
        ),
    )
    result = compare(baseline, candidate)
    assert (result["baseline_pass"], result["candidate_pass"], result["total"]) == (
        26,
        30,
        32,
    )
    assert result["verdict"] == "BLOCK"
    assert result["reasons"] == ["CASE_REGRESSION", "CRITICAL_CASE_FAILURE"]


def test_both_bad_is_not_a_pass(make_run):
    b = make_run("b", lambda r, c: wrong(r))
    c = make_run("c", lambda r, c: wrong(r))
    result = compare(b, c)
    assert result["regressions"] == 0
    assert result["verdict"] == "BLOCK"
    assert "BELOW_ABSOLUTE_FLOOR" in result["reasons"]


def test_control_correction_passes(make_run):
    result = compare(make_run("b"), make_run("c"))
    assert result["verdict"] == "PASS"
    assert result["candidate_pass"] == 32


def test_mixed_repeat_is_visible_and_critical_veto(make_run):
    c = make_run(
        "c", lambda r, c: wrong(r) if c.id == "missing-target" and r.repeat == 1 else r
    )
    result = compare(make_run("b"), c)
    assert result["unstable_cases"] == 1
    assert result["critical_failures"] == 1


@pytest.mark.parametrize(
    "status",
    [
        "TIMEOUT",
        "HTTP_ERROR",
        "MALFORMED_RESPONSE",
        "TRANSPORT_ERROR",
        "OVERSIZED_RESPONSE",
        "BUDGET_SKIPPED",
    ],
)
def test_provider_fault_in_baseline_also_blocks(make_run, status):
    b = make_run(
        "b",
        lambda r, c: (
            r.model_copy(update={"status": status, "raw": None})
            if c.id == "daily-sync"
            else r
        ),
    )
    result = compare(b, make_run("c"))
    assert result["candidate_pass"] == 32
    assert result["verdict"] == "BLOCK"
    assert result["reasons"] == ["INCOMPLETE_PROVIDER_EVIDENCE"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("repeats", 1),
        ("temperature", 0.7),
        ("seed", 15),
        ("max_tokens", 128),
        ("max_calls", 32),
        ("timeout_seconds", 3.0),
    ],
)
def test_incomparable_conditions_refused(make_run, field, value):
    settings = Settings(
        model="control", model_revision="authored-v1", runtime="test-control"
    ).model_copy(update={field: value})
    with pytest.raises(ValueError, match="Incomparable inference"):
        compare(make_run("b"), make_run("c", settings=settings))


def test_model_changes_allowed_and_recorded(make_run):
    settings = Settings(
        model="new-model", model_revision="new-sha", runtime="new-runtime"
    )
    result = compare(make_run("b"), make_run("c", settings=settings))
    assert result["candidate"]["model_revision"] == "new-sha"


def test_suite_change_refused(make_run, suite):
    changed = suite.model_copy(deep=True)
    changed.cases[0].input += " Changed input."
    with pytest.raises(ValueError, match="Incomparable suite"):
        compare(make_run("b"), make_run("c", selected_suite=changed))


def test_cannot_mix_handwritten_and_live_evidence(make_run):
    with pytest.raises(ValueError, match="Never compare"):
        compare(make_run("b"), make_run("c", kind="LIVE_LOCAL_MODEL"))


def test_policy_fingerprint_changes_when_threshold_changes(make_run):
    b, c = make_run("b"), make_run("c")
    original = compare(b, c)
    changed = compare(b, c, Policy(min_candidate_rate=0.95))
    assert original["policy_sha256"] != changed["policy_sha256"]


@pytest.mark.parametrize(
    "policy", [Policy(min_candidate_rate=1.1), Policy(max_case_regressions=-1)]
)
def test_invalid_policy_rejected(make_run, policy):
    with pytest.raises(ValueError, match="Invalid release policy"):
        compare(make_run("b"), make_run("c"), policy)


def test_report_html_escapes_untrusted_input_and_model_output(make_run, tmp_path):
    result = compare(make_run("b"), make_run("c"))
    evil = '<img src=x onerror="alert(1)"></pre><script>alert(2)</script>'
    result["rows"][0]["input"] = evil
    result["rows"][0]["after"][0]["raw"] = evil
    write_report(tmp_path / "report", result)
    html = (tmp_path / "report/index.html").read_text(encoding="utf-8")
    assert evil not in html
    assert "&lt;script&gt;" in html
    assert "script-src 'none'" in html
    with pytest.raises(FileExistsError):
        write_report(tmp_path / "report", result)
