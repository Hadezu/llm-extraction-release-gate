"""Create a small offline review bundle from verified captures and controls."""

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from control_demo import build

from extraction_gate.compare import compare
from extraction_gate.report import write_report
from extraction_gate.storage import read_json

ROOT = Path(__file__).resolve().parents[1]
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
published = ROOT / "evidence/local-qwen"
result = compare(published / "baseline", published / "candidate")
assert result == read_json(published / "comparison.json")
with tempfile.TemporaryDirectory(prefix="package-", dir=dist) as temp:
    temp = Path(temp)
    build(temp / "control")
    write_report(temp / "real-report", result)
    with zipfile.ZipFile(
        dist / "evaluation-evidence.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr(
            "README.txt",
            "Open real-model/index.html for actual local Qwen results (BLOCK).\nOpen controlled-regression/index.html to see authored failure fixtures, NOT model results.\nOpen corrected-control/index.html for the passing control.\nRaw model captures are in captures/. No client data or deployment.\nSource: https://github.com/Hadezu/llm-extraction-release-gate\n",
        )
        for source, destination in [
            (temp / "real-report", "real-model"),
            (temp / "control/blocked-report", "controlled-regression"),
            (temp / "control/fixed-report", "corrected-control"),
            (published / "baseline", "captures/baseline"),
            (published / "candidate", "captures/candidate"),
        ]:
            for path in sorted(source.glob("*")):
                if path.is_file() and path.suffix in {".json", ".html"}:
                    archive.write(path, destination + "/" + path.name)
shutil.copyfile(
    ROOT / "docs/images/evaluation-demo.webm", dist / "evaluation-demo.webm"
)
assets = sorted(
    path
    for path in dist.iterdir()
    if path.is_file()
    and (path.suffix in {".whl", ".zip", ".webm"} or path.name.endswith(".tar.gz"))
)
lines = [
    hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name for path in assets
]
(dist / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(
    json.dumps(
        {"assets": [path.name for path in assets], "raw_capture_replay": "VERIFIED"}
    )
)
