from pathlib import Path

from .contracts import Record, Settings, Suite
from .provider import LocalProvider
from .storage import RunWriter


def run_local(
    path: Path, suite: Suite, prompt: str, settings: Settings, endpoint: str, label: str
):
    provider = LocalProvider(endpoint, settings)
    try:
        writer = RunWriter(path, suite, prompt, settings, "LIVE_LOCAL_MODEL", label)
        calls = 0
        # Same ordering and seeds across variants; no retry that could hide a failure.
        for case in suite.cases:
            for repeat in range(settings.repeats):
                if calls >= settings.max_calls:
                    record = Record(
                        case_id=case.id, repeat=repeat, status="BUDGET_SKIPPED"
                    )
                else:
                    calls += 1
                    record = provider.call(case, repeat, prompt)
                writer.add(record)
        writer.finish()
    finally:
        provider.close()
