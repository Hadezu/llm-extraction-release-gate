import json
import subprocess
import sys


def test_cli_block_is_exit_one_with_report(make_run, tmp_path):
    def corrupt(record, case):
        if case.id == "missing-target":
            value = json.loads(record.raw)
            value["target"] = "invented"
            return record.model_copy(update={"raw": json.dumps(value)})
        return record

    b, c = make_run("b"), make_run("c", corrupt)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "extraction_gate.cli",
            "compare",
            str(b),
            str(c),
            "--out",
            str(tmp_path / "report"),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1
    assert "BLOCK" in result.stdout
    assert (
        json.loads((tmp_path / "report/comparison.json").read_text())["verdict"]
        == "BLOCK"
    )


def test_cli_incomplete_evidence_is_exit_two_without_success_report(make_run, tmp_path):
    b, c = make_run("b"), make_run("c", finish=False)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "extraction_gate.cli",
            "compare",
            str(b),
            str(c),
            "--out",
            str(tmp_path / "report"),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert "EVIDENCE_ERROR" in result.stderr
    assert not (tmp_path / "report").exists()


def test_cli_pass_is_exit_zero(make_run, tmp_path):
    b, c = make_run("b"), make_run("c")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "extraction_gate.cli",
            "compare",
            str(b),
            str(c),
            "--out",
            str(tmp_path / "report"),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("PASS")
