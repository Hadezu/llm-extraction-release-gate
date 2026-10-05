# Verification record

Checked 6 October 2026, Europe/Warsaw. Local environment: Windows x64, Python 3.14.4, uv 0.12.23; locked dependencies in uv.lock.

## Actual local evidence

- **85 tests passed** (17.44 s): strict schema/labels, quoted-but-wrong dates, higher-score critical regression, unchanged poor baseline, mixed repeats, settings/suite incompatibility, changed hashes/identities, maximum-length case IDs, interrupted evidence, actual separate-process exit, concurrent run ownership, atomic-write failures and CLI exit semantics.
- Real loopback HTTP test server: 401/429/503, redirect rejection, timeout, malformed JSON/envelope/usage, oversized body, truncation/refusal/model mismatch and call-budget exhaustion. This server is explicitly a test double, not AI inference.
- **64 actual Qwen calls**: 16 inputs × 2 repeats × 2 prompts. Baseline 0/32, candidate 6/32, no pass-count regressions, 10 failing critical cases. **BLOCK** due to absolute floor and critical failures. All response envelopes and comparison are in evidence/local-qwen.
- Recomputing the comparison from the published capture files produced the same full result; no new inference was claimed for replay.
- Chromium: control aggregate improvement still blocked; details expose the invented deadline; corrected control passes; downloaded JSON matches. Real model report, provenance and 390px layout inspected; no JS errors or external requests. Screenshots were visually reviewed. Video records the real report interactions, not a rendered storyboard.
- Ruff lint/format passed; source archive and wheel built. A wheel installed in a separate environment and invoked outside the source directory reproduced BLOCK and generated its HTML report successfully.
- The offline release ZIP passed integrity checks and contains all 64 raw model responses plus two manifests. Its suite and comparison match the checked-in source. Video SHA-256: `f75cbc80099893e524f786de0a1df1f41d409da37e58feffc5a89729d56decd6`.

Initial local pytest attempts encountered an inaccessible shared system temporary directory, then a missing custom parent directory; no test assertions ran for those fixtures. The final run used a new test-results temporary directory. A test helper initially read UTF-8 metadata using Windows' default encoding; this was corrected explicitly, then the complete suite passed. A transient Windows file-sharing denial during early control generation led to a bounded atomic-rename retry with tests for transient and persistent failure. No permissions were weakened.

## Hosted CI readback

Implementation commit: `ff2672a14aba7e464c39301ef9e703d1a0553259`.

[GitHub Actions run 37381764743](https://github.com/Hadezu/llm-extraction-release-gate/actions/runs/37381764743) completed **SUCCESS**. Both Linux/Python 3.12 and Windows/Python 3.14 jobs completed lint/format, the test suite, control generation, full capture replay, actual Chromium report/download/mobile checks, package build and installed-wheel CLI verification. Artifacts were uploaded by both jobs. Windows browser dependency installation took several minutes; it completed successfully.

This is hosted runtime evidence for the evaluation tool and report. It does **not** claim fresh model inference in GitHub Actions. The two real inference runs were local, and their model-quality verdict remains BLOCK. The final publication commit only updates documentation/media after this verified implementation commit.

## Reproduction commands

```sh
uv sync --locked
uv run pytest -q --junitxml=test-results/unit.xml
uv run ruff check .
uv run ruff format --check .
uv run python scripts/control_demo.py
uv run python scripts/replay_evidence.py
uv run playwright install chromium
uv run python scripts/browser_check.py
uv build
```

If Windows' shared pytest temp directory is inaccessible, create a private test-results directory and pass a **new** `--basetemp test-results/tmp-unique` path. Pytest may clear its selected base temp; never point it at useful data.

The workflow runs on Linux/Python 3.12 and Windows/Python 3.14, checks the built wheel outside the source directory and uploads evidence. It replays saved inference, not fresh remote model calls. A green workflow confirms the harness verification; the demonstrated AI candidate remains blocked.

## Limits of this verification

No production service or buyer data; no load test, pen test, formal security/compliance review, independent label adjudication or production SLA. CPU inference was performed locally on Windows only. No model fine-tuning or quality guarantee. Runtime/weight identity in manifests is an operator record, not cryptographic server attestation. Scores use 16 development cases; repeats do not create an independent 32-case benchmark.
