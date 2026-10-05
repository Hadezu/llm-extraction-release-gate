# A higher score is not a release decision

A team extracts structured work requests with an LLM. A prompt edit may fix common requests while introducing a fabricated deadline or a wrong source/target direction. Manually trying a few examples gives the team no repeatable acceptance record.

This case adds a small evaluation boundary around that workflow. The system under test receives only the request and prompt. Separately authored expectations define the checks. Each attempted inference is stored before continuing, and a comparison checks both absolute quality and individual changes.

## What I implemented

Ivan Matiushkin with Codex implemented the Python package, labelled synthetic corpus, prompt variants, HTTP adapter, durable run files, deterministic evaluator, comparison rules, HTML report, fault tests, browser walkthrough and CI. llama.cpp and Qwen provide real inference and retain their own authorship/licenses. This is original evaluation code, not a fork of those projects.

The portfolio already had a real-model AI workflow demo. This project adds **persistent, version-to-version evaluation and release blocking**, not another approval screen or a second webhook system.

## Real experiment: reject an insufficient improvement

On 6 October 2026 in Warsaw (5 October UTC), Qwen2.5-0.5B-Instruct Q4_K_M ran on local CPU through llama.cpp b11430. There were 64 requests: 16 cases × 2 repeats × 2 prompts. No schema grammar constrained generation. Raw response envelopes, token counts, timings, prompt text and model revision are in [`evidence/local-qwen`](evidence/local-qwen).

The baseline prompt included a compact pseudo-schema. This small model frequently echoed the pseudo-schema instead of filling it, resulting in **0/32 passing outputs**. The candidate used a valid JSON example and more explicit instructions; **6/32** outputs passed all checks. It still copied example dates, misread superseded requirements and failed unknown-value handling. Ten critical cases had failures. Both repeats happened to give the same pass/fail outcomes.

The gate returned **BLOCK**. There were no per-case regressions relative to the very weak baseline; it was blocked by the absolute floor and critical-case rule. This distinction matters: not every BLOCK is a regression.

This experiment does not isolate the impact of any one prompt sentence: multiple prompt changes were made together. Inputs were authored for development and inspected during implementation, not kept as a blind holdout. It establishes actual capture and failure diagnosis for this configuration, not general model quality.

## Controlled experiment: catch the hidden regression

To test a different property, the repository includes explicitly authored control outputs. The baseline fails three noncritical cases; a candidate fixes those but invents a deadline on one critical case. Aggregate performance increases **26/32 → 30/32**, crossing the 90% floor, but the gate blocks it. A corrected control passes **32/32**.

These controls verify the gate's behavior. They are never mixed with or reported as real model responses. The comparison refuses cross-kind input.

## Engineering choices

Strict Pydantic contracts and deterministic labels are appropriate for this bounded structured task. A model judge would add cost and uncertain scoring without helping determine whether an exact source name/date was returned. Files are enough for a single-owner local batch; a database or agent framework would add operations without improving this acceptance boundary. llama.cpp provides an existing open-source system over a real HTTP interface, with no paid service dependency.

See [architecture and limitations](docs/ARCHITECTURE.md) for what the file protocol and gate do not guarantee.

## What a buyer could ask me to deliver

Add this style of regression check to one existing request-extraction feature: agree representative sanitized cases, define acceptance rules, integrate with the actual provider and CI, and hand over the failures and reproduction commands. Provider credentials, representative data and production thresholds belong to the buyer's project, not this demonstration.
