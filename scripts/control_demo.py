"""Deliberate controls to test the gate, NOT manufactured model results."""

import argparse
import json
from pathlib import Path

from extraction_gate.compare import compare
from extraction_gate.contracts import Record, Settings, Suite
from extraction_gate.report import write_report
from extraction_gate.storage import RunWriter, read_json

ROOT = Path(__file__).resolve().parents[1]


def correct(case):
    value = case.expected.model_dump()
    value["evidence"] = {
        key: getattr(case.expected, key) for key in ("source", "target", "deadline")
    }
    return value


def build(path: Path):
    suite = Suite.model_validate(read_json(ROOT / "data/suite.json"))
    settings = Settings(
        model="hand-authored-controls",
        model_revision="control-v1",
        runtime="No inference; authored validation fixtures",
    )
    for variant in ("baseline", "candidate", "fixed"):
        writer = RunWriter(
            path / variant,
            suite,
            "CONTROL FIXTURE: " + variant,
            settings,
            "CONTROL_FIXTURE",
            variant,
        )
        for case in suite.cases:
            for repeat in range(settings.repeats):
                value = correct(case)
                # Baseline misses three noncritical cases: 26/32 checks.
                if variant == "baseline" and case.id in {
                    "daily-sync",
                    "one-time-import",
                    "reporting-request",
                }:
                    value["action"] = "unknown"
                # Candidate improves aggregate to 30/32, but invents a deadline.
                if variant == "candidate" and case.id == "sync-no-deadline":
                    value["deadline"] = "2026-11-20"
                    value["evidence"]["deadline"] = "Deadline: 2026-11-20"
                writer.add(
                    Record(
                        case_id=case.id,
                        repeat=repeat,
                        status="OK",
                        raw=json.dumps(value, ensure_ascii=False),
                    )
                )
        writer.finish()
    blocked = compare(path / "baseline", path / "candidate")
    fixed = compare(path / "baseline", path / "fixed")
    assert (
        blocked["verdict"] == "BLOCK"
        and blocked["candidate_pass"] > blocked["baseline_pass"]
    )
    assert "CRITICAL_CASE_FAILURE" in blocked["reasons"]
    assert fixed["verdict"] == "PASS"
    write_report(path / "blocked-report", blocked)
    write_report(path / "fixed-report", fixed)
    print(
        "CONTROL DEMO: 26/32 -> 30/32 is BLOCK; 32/32 is PASS. These are authored controls, not model results."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("runs/control"))
    build(parser.parse_args().out)
