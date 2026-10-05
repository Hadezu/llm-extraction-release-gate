# Reproduce real local inference

No paid API or account is used. Downloading the optional model consumes approximately 491 MB of disk/network. The replay path in README needs no model download.

## Pinned components

| Component | Version / verification |
| --- | --- |
| llama.cpp | [b11430](https://github.com/ggml-org/llama.cpp/releases/tag/b11430), MIT |
| Windows CPU archive | `llama-b11430-bin-win-cpu-x64.zip`, SHA-256 `b608455b0109793f774537d63d15d4cf2098ddbc5b200ebc9a648e1d85369666` |
| Ubuntu CPU archive | `llama-b11430-bin-ubuntu-x64.tar.gz`, provider-published SHA-256 `1b898a3b23df35cc6c3e93c3adba5c63ec31d48bee8e5f30639e9372836ec2f2` |
| Qwen | [Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF), Apache-2.0 |
| Model revision | `9217f5db79a29953eb74d5343926648285ec7e67` |
| Model file | `qwen2.5-0.5b-instruct-q4_k_m.gguf`, 491400032 bytes |
| Model SHA-256 | `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` |

The Windows archive and model were downloaded and hashed locally; Linux archive metadata was read from the official GitHub release. **Fresh inference was verified on Windows CPU, not Linux.** Neither binaries nor model weights are redistributed in this repository.

## Windows PowerShell, from the repository directory

```powershell
New-Item -ItemType Directory -Path local-runtime
Invoke-WebRequest 'https://github.com/ggml-org/llama.cpp/releases/download/b11430/llama-b11430-bin-win-cpu-x64.zip' -OutFile 'local-runtime/llama.zip'
Invoke-WebRequest 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf' -OutFile 'local-runtime/qwen.gguf'
Get-FileHash 'local-runtime/llama.zip' -Algorithm SHA256
Get-FileHash 'local-runtime/qwen.gguf' -Algorithm SHA256
```

Compare both hashes with the table before executing the binary. Extract and start:

```powershell
Expand-Archive -LiteralPath 'local-runtime/llama.zip' -DestinationPath 'local-runtime/llama'
& './local-runtime/llama/llama-server.exe' --model './local-runtime/qwen.gguf' --alias eval-qwen --host 127.0.0.1 --port 8190 --ctx-size 4096 --parallel 1 --threads 4 --n-gpu-layers 0
```

Keep that terminal open. In another terminal:

```sh
uv sync --locked
uv run extraction-gate run-local --suite data/suite.json --settings data/settings.json --prompt prompts/baseline.txt --label baseline-v1 --out runs/new-baseline
uv run extraction-gate run-local --suite data/suite.json --settings data/settings.json --prompt prompts/candidate.txt --label candidate-v1 --out runs/new-candidate
uv run extraction-gate compare runs/new-baseline runs/new-candidate --policy data/policy.json --out runs/new-comparison
```

The observed result is BLOCK (exit 1), which is expected for these prompts/model. Do not ignore a nonzero exit when integrating with a real release. Each output directory must be new; never relabel/rewrite an old run to make it appear current. Stop the server with Ctrl+C afterwards. It binds to loopback and has no business-system tools; do not expose it publicly.

## Different runtime or model

Use a new settings file recording the actual model hash and runtime, with a matching local server alias. The adapter expects a single llama.cpp-style chat response with a matching model alias. Keep case set and inference settings equal for a paired comparison. Both prompt and model may change, but the comparison does not establish which caused any score change. Do not reuse the published runtime description after changing hardware/backend settings.

A request timeout is an inactivity timeout, not an absolute batch deadline. `max_calls` counts attempts; `max_tokens` limits requested generation per call. No retries occur. Cancellation/process death leaves an incomplete directory that the gate refuses. Review before scheduling a distinctly named new run; partial evidence is not silently resumed.

Even with fixed seeds, greedy sampling and prompt caching disabled, exact model outputs can vary across runtimes and hardware. The checked-in raw captures provide reproducible **evaluation**, not a promise of bit-identical new inference.
