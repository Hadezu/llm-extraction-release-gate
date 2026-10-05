"""Paired comparisons, critical-case veto and explicit evidence comparability."""

from collections import Counter
from pathlib import Path

from .contracts import Strict, digest
from .evaluate import evaluate
from .provider import output_record
from .storage import read_run


class Policy(Strict):
    # Intentionally small, transparent policy. Changing it changes the policy hash.
    min_candidate_rate: float = 0.9
    max_case_regressions: int = 0
    critical_all_pass: bool = True

    def validate_bounds(self):
        if not 0 <= self.min_candidate_rate <= 1 or self.max_case_regressions < 0:
            raise ValueError("Invalid release policy")


def compare(baseline: Path, candidate: Path, policy: Policy | None = None) -> dict:
    policy = policy or Policy()
    policy.validate_bounds()
    bm, br = read_run(baseline)
    cm, cr = read_run(candidate)
    # Model / prompt are intended independent variables. All other evaluation
    # conditions must match. This is not an inference of causation.
    if bm.suite_sha256 != cm.suite_sha256 or bm.evaluator != cm.evaluator:
        raise ValueError("Incomparable suite or evaluator version")
    if bm.kind != cm.kind:
        raise ValueError("Never compare control fixtures with live model evidence")
    for field in (
        "temperature",
        "seed",
        "max_tokens",
        "repeats",
        "max_calls",
        "timeout_seconds",
    ):
        if getattr(bm.settings, field) != getattr(cm.settings, field):
            raise ValueError("Incomparable inference setting: " + field)
    rows = []
    infra = []
    slices = {}
    for case in cm.suite.cases:
        before, after = [], []
        for i in range(cm.settings.repeats):
            key = f"{case.id}--{i}"
            b = evaluate(case, output_record(br[key], bm.kind))
            c = evaluate(case, output_record(cr[key], cm.kind))
            before.append(
                {**b, "repeat": i, "raw": output_record(br[key], bm.kind).raw}
            )
            after.append({**c, "repeat": i, "raw": output_record(cr[key], cm.kind).raw})
            # Provider / transport failure cannot be hidden by a bad baseline.
            for variant, rec in (("baseline", br[key]), ("candidate", cr[key])):
                rec = output_record(rec, cm.kind)
                if rec.status in {
                    "TIMEOUT",
                    "HTTP_ERROR",
                    "TRANSPORT_ERROR",
                    "MALFORMED_RESPONSE",
                    "OVERSIZED_RESPONSE",
                    "BUDGET_SKIPPED",
                }:
                    infra.append(f"{variant}/{key}: {rec.status}")
        bp = sum(r["passed"] for r in before)
        cp = sum(r["passed"] for r in after)
        total = cm.settings.repeats
        regression = cp < bp
        critical_failure = case.critical and cp < total
        unstable = cp not in (0, total)
        outcome = (
            "REGRESSION" if regression else ("IMPROVED" if cp > bp else "UNCHANGED")
        )
        rows.append(
            {
                "id": case.id,
                "slice": case.slice,
                "critical": case.critical,
                "input": case.input,
                "expected": case.expected.model_dump(),
                "rationale": case.rationale,
                "baseline_pass": bp,
                "candidate_pass": cp,
                "total": total,
                "outcome": outcome,
                "critical_failure": critical_failure,
                "unstable": unstable,
                "before": before,
                "after": after,
            }
        )
        part = slices.setdefault(
            case.slice, {"baseline": 0, "candidate": 0, "total": 0}
        )
        part["baseline"] += bp
        part["candidate"] += cp
        part["total"] += total
    total = len(rows) * cm.settings.repeats
    bpass = sum(row["baseline_pass"] for row in rows)
    cpass = sum(row["candidate_pass"] for row in rows)
    regressions = sum(row["outcome"] == "REGRESSION" for row in rows)
    critical = sum(row["critical_failure"] for row in rows)
    reasons = []
    if infra:
        reasons.append("INCOMPLETE_PROVIDER_EVIDENCE")
    if cpass / total < policy.min_candidate_rate:
        reasons.append("BELOW_ABSOLUTE_FLOOR")
    if regressions > policy.max_case_regressions:
        reasons.append("CASE_REGRESSION")
    if critical and policy.critical_all_pass:
        reasons.append("CRITICAL_CASE_FAILURE")
    flags = Counter(
        issue for row in rows for rep in row["after"] for issue in rep["issues"]
    )

    def metadata(m, records):
        return {
            "label": m.label,
            "model": m.settings.model,
            "model_revision": m.settings.model_revision,
            "runtime": m.settings.runtime,
            "prompt_sha256": m.prompt_sha256,
            "started_at": m.started_at,
            "finished_at": m.finished_at,
            "observed_models": sorted(
                {r.response_model for r in records.values() if r.response_model}
            ),
            "total_latency_ms": round(sum(r.latency_ms for r in records.values()), 3),
            "reported_output_tokens": sum(
                r.output_tokens or 0 for r in records.values()
            ),
            "usage_available": sum(
                r.output_tokens is not None for r in records.values()
            ),
        }

    return {
        "format": "extraction-comparison-v1",
        "verdict": "BLOCK" if reasons else "PASS",
        "kind": cm.kind,
        "reasons": reasons,
        "infrastructure_findings": infra,
        "baseline": metadata(bm, br),
        "candidate": metadata(cm, cr),
        "suite_sha256": cm.suite_sha256,
        "policy": policy.model_dump(),
        "policy_sha256": digest(policy),
        "evaluator": cm.evaluator,
        "cases": len(rows),
        "repeats": cm.settings.repeats,
        "baseline_pass": bpass,
        "candidate_pass": cpass,
        "total": total,
        "regressions": regressions,
        "critical_failures": critical,
        "unstable_cases": sum(row["unstable"] for row in rows),
        "slices": slices,
        "findings": dict(flags),
        "rows": rows,
        "limits": "Synthetic diagnostic set, not a representative benchmark. Repeats are correlated; rates are descriptive, not statistical significance. Exact labels and source spans do not establish semantic truth or general prompt-injection resistance. A PASS is only this policy on this evidence, never production approval.",
    }
