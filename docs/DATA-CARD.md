# Dataset and evaluation card

**business-request-v1** contains 16 authored synthetic requests: 15 English, one Polish. Fictional system names and dates were chosen for an integration/internal-tools workflow. No customer records, copied client prompts or personal data.

| Slice | Cases | Purpose |
| --- | ---: | --- |
| complete | 3 | Basic sync/migration/report classification and extraction |
| missing | 3 | Null handling and clarification requirements |
| dates | 3 | Relative, withdrawn and replacement dates |
| direction | 2 | Reversed direction and similar system names |
| ambiguity | 2 | Unselected alternatives and absent task |
| injection | 2 | Embedded instruction text and a quoted pseudo-system message |
| language | 1 | Polish one-time migration request |

`critical=true` marks data-integrity cases where the example release policy tolerates no failing outputs. This is an explicit authored choice, not a risk certification. Changes to text, labels, rationales or criticality change the suite hash and invalidate direct comparison with an older suite.

Labels were authored before the first local inference, with rationale in each case. Candidate wording was revised after inspecting the baseline's schema-echo failure. All cases are **development diagnostics**, not a blind holdout; no generalization or test-set independence claim is made. The prompt's example uses different system names/date from the dataset, but the overall contract was designed with the same task in mind.

The initial contract intentionally does not require a deadline before extraction succeeds. It requires review for unknown action or missing source, plus missing target for integration/migration. Reporting has no required target. `review_required` is a field being tested, **not** an authorization to execute business work.

Exact field agreement is suitable here because expected system names, date/null and direction are fixed. It is not an appropriate quality metric for free-form summaries. Source-span presence is checked separately; correct spans alone do not prove semantic support. Example: an old, withdrawn date appears verbatim but is the wrong current deadline.

Two runs per prompt/case were made at temperature zero with different seeds. Observed pass/fail results were identical within each pair. Counts of 32 are repeated outputs on **16 unique inputs**, not 32 independent examples. Rates and latency totals are descriptive; no statistical significance, confidence interval, speed comparison or cost-saving claim.

The controlled demo emits intentionally hand-authored outputs and is marked CONTROL_FIXTURE in every manifest/report. Those outputs test failure detection, not model accuracy. The real experiment uses LIVE_LOCAL_MODEL and stores HTTP response envelopes unmodified. The tool refuses to compare evidence kinds.

To use with a buyer, agree a representative sanitized corpus, separate development/holdout sets where appropriate, independently review labels and discuss the cost of each error. This repository supplies the mechanism and an example contract, not those buyer-specific judgments.
