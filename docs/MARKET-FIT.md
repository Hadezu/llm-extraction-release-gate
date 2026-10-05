# Buyer requirements → existing service → missing proof

Research checked 5–6 October 2026. Sources are requirement samples, not a market ranking, promises that an opportunity remains open, or qualified email leads. No buyer was contacted and no application was submitted.

## Primary buyer evidence

1. [Applied ML Research Engineer — LLM Post-Training and Evaluation](https://www.upwork.com/freelance-jobs/apply/Applied-Research-Engineer-LLM-Post-Training-and-Evaluation_~022099698752005322108/). Buyer asks for comparable versioned evaluations, failure analysis by slice, honest negative results and evaluation before shipping model-output changes. The role also has an explicit end-to-end LoRA fine-tuning requirement. This project addresses the evaluation portion; it **does not satisfy the fine-tuning gate or establish eligibility for the whole role**.
2. [AI/ML Evaluation Specialist — LLM, Agent, Coding & Multimodal Evals](https://www.upwork.com/freelance-jobs/apply/Evaluation-Specialist-LLM-Agent-Coding-Multimodal-Evals_~022104599313408340858/). Buyer requests test/reference cases, failure analysis, reproducible checks and portfolio/GitHub examples, including a subtle failure that looked initially plausible. This case supplies a narrow structured-output example. It does not prove multimodal, computer-vision or broad ML expertise.
3. [AI Evaluation Engineer (Healthcare)](https://www.upwork.com/freelance-jobs/apply/Evaluation-Engineer-Healthcare-Build-Dynamic-Eval-Infrastructure-for-LLM-Systems_~022100294678518346634/). Buyer wants regression infrastructure but explicitly requires healthcare and production LLM evaluation experience. **HARD_EXPERIENCE_GATE** for those requirements; this synthetic general-business case cannot compensate for them.

These are buyer-authored listings, not freelancer service advertisements. Relative posting ages were not converted into exact dates. Marketplace sources were used to study technical requirements; acquisition remains email-first where a legitimate current paid route exists.

## Current site inspected

- [Homepage](https://work.matiushkin.com/en): custom business software, written requests, bounded tasks, AI-assisted implementation with tests/handover.
- [AI Lab](https://work.matiushkin.com/en/proof/ai-automation) / [PL](https://work.matiushkin.com/proof/ai-automation): actual Workers AI model, lexical retrieval, structured extraction and controlled evaluation on synthetic presets. Live GET returned HTTP 200; no production inference, form submission or site mutation performed for this task.
- Sitemap returned 48 URLs. This project does not add a production route or change the site's service list.

## Existing GitHub proof checked before selecting

| Repository | Existing competence | Why this case differs |
| --- | --- | --- |
| work-portfolio | React/TypeScript, interactive demonstrations, AI workflow | Adds durable paired release evaluation outside the portfolio demo |
| atomic-crm-import-review | Focused change to an existing CRM UI | No new CRM/import UI here |
| resilience4j-retry-review | Java maintenance and regression reproduction | Evaluates nondeterministic external model responses, not Java retry behavior |
| fastapi-webhook-reliability | PostgreSQL inbox/outbox and recovery | No webhook duplicate-delivery problem recreated |
| reconciliation-evidence-workbench | CSV/XLSX comparison and provenance | Comparing extracted AI requirements, not financial records |
| operations-approval-desk | Permissions, versions, concurrent human decisions | No new human approval workflow; CI policy checks only |

Public repository names/descriptions were read directly from GitHub. The two old private projects were preserved and not published or used as client-history evidence.

## Commercial proof map

| Item | Bounded answer |
| --- | --- |
| Buyer | Product team or agency with an existing LLM request-extraction feature |
| Problem | Prompt/model changes can silently alter extracted names, directions, missing values or deadlines |
| Existing service | AI workflow validation/evaluation, linked to the AI Lab |
| Missing evidence | Repeatable version comparison with retained outputs, critical-case veto and fail-closed evidence handling |
| First paid slice | One extraction contract + agreed sanitized labels + provider adapter + CI decision + failure report |
| Safe claim | I built and ran a structured-output evaluation tool that keeps raw responses and blocks changes failing agreed checks |
| Compensable gap | Missing example of implementing an evaluation harness, where buyer accepts project proof |
| Uncompensated gate | Mandatory production years, paid client references, healthcare experience, LoRA/RL training or certification |
| Query families | `LLM evaluation contractor`, `structured extraction regression testing`, `prompt evaluation project`, `AI output QA contract`, `LLM release evaluation freelance`, `AI agency external evaluation engineer` |

Query text is not demand evidence. Re-read a current first-party brief, requirements and published email route before outreach. Use the smallest matching proof; do not attach this repository to unrelated frontend or migration applications.
