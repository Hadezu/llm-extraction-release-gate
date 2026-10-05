import concurrent.futures
import json
import os
import subprocess
import sys
import threading

import pytest

from extraction_gate.contracts import Record, Settings, digest
from extraction_gate.storage import RunWriter, atomic_json, read_run


def test_modified_record_detected(make_run):
    path = make_run("run")
    (path / "daily-sync--0.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        read_run(path)


def test_maximum_length_case_id_roundtrips_with_repeat_suffix(make_run, suite):
    changed = suite.model_copy(deep=True)
    changed.cases[0].id = "a" * 80
    path = make_run("long-id", selected_suite=changed)
    manifest, records = read_run(path)
    assert manifest.complete
    assert "a" * 80 + "--1" in records


def test_missing_record_detected(make_run):
    path = make_run("run")
    (path / "daily-sync--0.json").unlink()
    with pytest.raises(ValueError, match="Unexpected evidence"):
        read_run(path)


def test_unsealed_is_never_accepted(make_run):
    path = make_run("run", finish=False)
    with pytest.raises(ValueError, match="interrupted"):
        read_run(path)


def test_mismatched_identity_detected_even_with_updated_hash(make_run):
    path = make_run("run")
    key = "daily-sync--0"
    value = json.loads((path / (key + ".json")).read_text(encoding="utf-8"))
    value["case_id"] = "other"
    atomic_json(path / (key + ".json"), value)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][key] = digest(value)
    atomic_json(path / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Mismatched case"):
        read_run(path)


@pytest.mark.parametrize("field", ["suite_sha256", "prompt_sha256"])
def test_changed_manifest_hash_rejected(make_run, field):
    path = make_run("run")
    value = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    value[field] = "0" * 64
    atomic_json(path / "manifest.json", value)
    with pytest.raises(ValueError, match="Manifest content"):
        read_run(path)


def test_extra_record_blocks_instead_of_silently_ignored(make_run):
    path = make_run("run")
    (path / "extra.json").write_text("{}")
    with pytest.raises(ValueError, match="Unexpected evidence"):
        read_run(path)


def test_failed_atomic_write_preserves_old_file(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    atomic_json(path, {"old": True})

    def fail(*_):
        raise PermissionError("simulated persistent write denial")

    monkeypatch.setattr(os, "replace", fail)
    monkeypatch.setattr("extraction_gate.storage.time.sleep", lambda _: None)
    with pytest.raises(PermissionError):
        atomic_json(path, {"new": True})
    assert json.loads(path.read_text()) == {"old": True}
    assert list(tmp_path.iterdir()) == [path]


def test_transient_windows_sharing_failure_retries_without_deletion(
    tmp_path, monkeypatch
):
    original = os.replace
    calls = []

    def transient(a, b):
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError("sharing")
        original(a, b)

    monkeypatch.setattr(os, "replace", transient)
    monkeypatch.setattr("extraction_gate.storage.time.sleep", lambda _: None)
    atomic_json(tmp_path / "state.json", {"ok": True})
    assert len(calls) == 2


def test_concurrent_run_creation_has_one_owner(tmp_path, suite):
    barrier = threading.Barrier(2)
    settings = Settings(model="test", model_revision="test", runtime="test")

    def create():
        barrier.wait(timeout=5)
        try:
            RunWriter(
                tmp_path / "exclusive",
                suite,
                "prompt",
                settings,
                "CONTROL_FIXTURE",
                "test",
            )
            return "created"
        except FileExistsError:
            return "exists"

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sorted(results) == ["created", "exists"]


def test_duplicate_record_and_early_seal_rejected(tmp_path, suite):
    writer = RunWriter(
        tmp_path / "run",
        suite,
        "prompt",
        Settings(model="test", model_revision="test", runtime="test"),
        "CONTROL_FIXTURE",
        "test",
    )
    record = Record(case_id="daily-sync", repeat=0, status="TIMEOUT")
    writer.add(record)
    with pytest.raises(ValueError, match="Duplicate record"):
        writer.add(record)
    with pytest.raises(ValueError, match="Incomplete run"):
        writer.finish()


def test_actual_process_death_leaves_inspectable_incomplete_run(tmp_path, suite):
    suite_file = tmp_path / "suite.json"
    atomic_json(suite_file, suite)
    code = """
import os,sys
from pathlib import Path
from extraction_gate.contracts import Suite, Settings, Record
from extraction_gate.storage import RunWriter, read_json
suite=Suite.model_validate(read_json(Path(sys.argv[1])))
writer=RunWriter(Path(sys.argv[2]), suite, "prompt", Settings(model="test",model_revision="test",runtime="test"), "CONTROL_FIXTURE", "crash")
writer.add(Record(case_id="daily-sync",repeat=0,status="TIMEOUT"))
os._exit(71)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(suite_file), str(tmp_path / "crashed")],
        timeout=20,
    )
    assert result.returncode == 71
    assert (tmp_path / "crashed/daily-sync--0.json").exists()
    with pytest.raises(ValueError, match="interrupted"):
        read_run(tmp_path / "crashed")
