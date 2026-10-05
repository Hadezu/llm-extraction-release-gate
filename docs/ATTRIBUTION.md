# Attribution and dependency boundaries

Original evaluation application, dataset, prompts, tests, report design and documentation: **Ivan Matiushkin with Codex**, MIT (repository LICENSE). Codex assisted implementation, debugging, tests and documentation. Published claims are tied to recorded checks; AI assistance is not a substitute for checking the result.

This repository uses an existing open-source **inference system**, llama.cpp, rather than wrapping another CRM or creating a new model. It does not copy or modify llama.cpp/Qwen source or claim their authorship. Their binaries/weights are downloaded separately and are not included in source/release archives.

| Component | Upstream / license | Role |
| --- | --- | --- |
| llama.cpp | [ggml-org](https://github.com/ggml-org/llama.cpp), MIT | Actual local HTTP inference runtime, pinned b11430 |
| Qwen2.5-0.5B-Instruct-GGUF | [Qwen team](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF), Apache-2.0 | Real open-weight test model; model card and original license remain authoritative |
| Pydantic | [pydantic/pydantic](https://github.com/pydantic/pydantic), MIT | Strict data validation |
| HTTPX | [encode/httpx](https://github.com/encode/httpx), BSD-3-Clause | Bounded local HTTP requests |
| Jinja | [pallets/jinja](https://github.com/pallets/jinja), BSD-3-Clause | Autoescaped static reports |
| pytest | [pytest-dev/pytest](https://github.com/pytest-dev/pytest), MIT | Unit/integration/failure tests |
| Playwright | [microsoft/playwright-python](https://github.com/microsoft/playwright-python), Apache-2.0 | Real browser verification and recording |
| uv / Ruff | [Astral](https://github.com/astral-sh), MIT/Apache-2.0 | Dependency locking, packaging and linting |

Transitive dependencies retain their own licenses; exact versions are in uv.lock. Installing dependencies does not relicense them under this project's MIT license. No upstream endorsement, sponsorship or client relationship is implied.
