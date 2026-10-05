import json
from pathlib import Path

import pytest

from extraction_gate.contracts import Record, Settings, Suite
from extraction_gate.storage import RunWriter, read_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def suite():
    return Suite.model_validate(read_json(ROOT / "data/suite.json"))


def answer(case):
    value = case.expected.model_dump()
    value["evidence"] = {
        key: getattr(case.expected, key) for key in ("source", "target", "deadline")
    }
    return value


@pytest.fixture
def make_run(tmp_path, suite):
    def make(
        name,
        mutate=None,
        selected_suite=None,
        settings=None,
        kind="CONTROL_FIXTURE",
        finish=True,
    ):
        selected_suite = selected_suite or suite
        settings = settings or Settings(
            model="control", model_revision="authored-v1", runtime="test-control"
        )
        writer = RunWriter(tmp_path / name, selected_suite, name, settings, kind, name)
        for case in selected_suite.cases:
            for repeat in range(settings.repeats):
                record = Record(
                    case_id=case.id,
                    repeat=repeat,
                    status="OK",
                    raw=json.dumps(answer(case)),
                )
                if mutate:
                    record = mutate(record, case)
                writer.add(record)
        if finish:
            writer.finish()
        return tmp_path / name

    return make
