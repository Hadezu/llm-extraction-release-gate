"""Recompute a published result from raw captures without claiming new inference."""

import argparse
from pathlib import Path

from extraction_gate.compare import compare
from extraction_gate.report import write_report
from extraction_gate.storage import read_json

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", type=Path, default=Path("evidence/local-qwen"))
parser.add_argument("--out", type=Path, default=Path("runs/live-report"))
args = parser.parse_args()
result = compare(args.evidence / "baseline", args.evidence / "candidate")
assert result == read_json(args.evidence / "comparison.json"), (
    "Published comparison does not match raw captures"
)
write_report(args.out, result)
print(
    f"CAPTURE REPLAY VERIFIED: {result['verdict']}; no new model inference performed."
)
