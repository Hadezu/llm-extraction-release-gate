"""Exclusive run directories, atomic snapshots and fail-closed evidence readback."""

import hashlib
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .contracts import Manifest, Record, Settings, Suite, canonical, digest, strict_json


def now():
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, value):
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        # Windows indexers/antivirus can hold the previous file briefly. Retry
        # only sharing/permission failures; never weaken ACLs or delete target.
        for attempt in range(6):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        temp.unlink(missing_ok=True)


class RunWriter:
    def __init__(
        self,
        path: Path,
        suite: Suite,
        prompt: str,
        settings: Settings,
        kind: str,
        label: str,
    ):
        self.manifest = Manifest(
            kind=kind,
            label=label,
            started_at=now(),
            suite=suite,
            suite_sha256=digest(suite),
            prompt=prompt,
            prompt_sha256=digest(prompt),
            settings=settings,
        )
        path.mkdir(parents=True, exist_ok=False)
        self.path = path
        atomic_json(path / "manifest.json", self.manifest)

    def add(self, record: Record):
        key = f"{record.case_id}--{record.repeat}"
        if key in self.manifest.files:
            raise ValueError("Duplicate record")
        atomic_json(self.path / (key + ".json"), record)
        self.manifest.files[key] = digest(record)
        atomic_json(self.path / "manifest.json", self.manifest)

    def finish(self):
        expected = {
            f"{case.id}--{i}"
            for case in self.manifest.suite.cases
            for i in range(self.manifest.settings.repeats)
        }
        if set(self.manifest.files) != expected:
            raise ValueError("Incomplete run cannot be sealed")
        self.manifest.complete = True
        self.manifest.finished_at = now()
        atomic_json(self.path / "manifest.json", self.manifest)


def read_json(path: Path, limit: int = 4_000_000):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Evidence file exceeds limit")
    return strict_json(raw.decode("utf-8"))


def read_run(path: Path):
    if (path / "manifest.json").is_symlink():
        raise ValueError("Evidence symlinks are not accepted")
    manifest = Manifest.model_validate(read_json(path / "manifest.json"))
    if not manifest.complete or not manifest.finished_at:
        raise ValueError(
            "Run interrupted or not sealed; never automatically resume unknown inference"
        )
    if (
        digest(manifest.suite) != manifest.suite_sha256
        or digest(manifest.prompt) != manifest.prompt_sha256
    ):
        raise ValueError("Manifest content hash mismatch")
    expected = {
        f"{case.id}--{i}"
        for case in manifest.suite.cases
        for i in range(manifest.settings.repeats)
    }
    if set(manifest.files) != expected:
        raise ValueError("Missing or unexpected planned record")
    if {p.name for p in path.iterdir()} != {"manifest.json"} | {
        key + ".json" for key in expected
    }:
        raise ValueError("Unexpected evidence files; possible interrupted write")
    records = {}
    for key, expected_hash in manifest.files.items():
        record_path = path / (key + ".json")
        if record_path.is_symlink():
            raise ValueError("Evidence symlinks are not accepted")
        with record_path.open("rb") as stream:
            raw = stream.read(800_001)
        if len(raw) > 800_000 or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError("Record content hash mismatch")
        record = Record.model_validate(strict_json(raw.decode("utf-8")))
        if f"{record.case_id}--{record.repeat}" != key:
            raise ValueError("Mismatched case identity")
        records[key] = record
    return manifest, records
