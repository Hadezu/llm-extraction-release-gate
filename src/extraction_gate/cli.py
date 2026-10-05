import argparse
import sys
from pathlib import Path

from .compare import Policy, compare
from .contracts import Settings, Suite
from .report import write_report
from .runner import run_local
from .storage import read_json


def main():
    parser = argparse.ArgumentParser(
        description="Structured extraction checks with explicit evidence and release gates"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-local")
    run.add_argument("--suite", type=Path, required=True)
    run.add_argument("--prompt", type=Path, required=True)
    run.add_argument("--settings", type=Path, required=True)
    run.add_argument("--endpoint", default="http://127.0.0.1:8190/v1/chat/completions")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--label", required=True)
    diff = sub.add_parser("compare")
    diff.add_argument("baseline", type=Path)
    diff.add_argument("candidate", type=Path)
    diff.add_argument("--policy", type=Path)
    diff.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run-local":
            suite = Suite.model_validate(read_json(args.suite))
            settings = Settings.model_validate(read_json(args.settings))
            run_local(
                args.out,
                suite,
                args.prompt.read_text(encoding="utf-8"),
                settings,
                args.endpoint,
                args.label,
            )
            print(
                "Run recorded. Sealing evidence is not a quality PASS; run compare next."
            )
            return 0
        policy = (
            Policy.model_validate(read_json(args.policy)) if args.policy else Policy()
        )
        result = compare(args.baseline, args.candidate, policy)
        write_report(args.out, result)
        print(
            f"{result['verdict']}: {result['candidate_pass']}/{result['total']} candidate checks; {result['regressions']} case regressions"
        )
        return 1 if result["verdict"] == "BLOCK" else 0
    except (ValueError, OSError, RecursionError) as exc:
        # No traceback / provider request body accidentally printed in ordinary usage.
        print(
            f"EVIDENCE_ERROR: {type(exc).__name__}. No release verdict produced; inspect input/run files.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
