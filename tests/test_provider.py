"""Real loopback HTTP faults. Server is a declared test double, never AI evidence."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from extraction_gate.contracts import Settings
from extraction_gate.provider import LocalProvider, output_record, validate_endpoint
from extraction_gate.runner import run_local
from extraction_gate.storage import read_run


@pytest.fixture
def server():
    state = {"requests": [], "mode": "ok"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append(body)
            mode = state["mode"]
            if mode == "timeout":
                time.sleep(0.15)
            status = int(mode) if mode in {"401", "429", "503", "307"} else 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if status == 307:
                self.send_header("Location", "http://127.0.0.1:1/v1/chat/completions")
            self.end_headers()
            output = {
                "model": "test-local",
                "choices": [
                    {
                        "message": {"content": '{"literal":"unchanged"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 40, "completion_tokens": 8},
            }
            if mode == "truncated":
                output["choices"][0]["finish_reason"] = "length"
            if mode == "refusal":
                output["choices"][0]["message"]["refusal"] = "refused"
            if mode == "model-mismatch":
                output["model"] = "different-model"
            if mode == "wrong-content":
                output["choices"][0]["message"]["content"] = ["wrong"]
            if mode == "bad-usage":
                output["usage"]["completion_tokens"] = -1
            if mode == "bad-message":
                output["choices"][0]["message"] = None
            if mode == "multiple":
                output["choices"].append(output["choices"][0])
            data = json.dumps(output).encode()
            if mode == "malformed":
                data = b"{broken"
            if mode == "oversized":
                data = b"x" * 140000
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}/v1/chat/completions", state
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=3)


def settings(**kwargs):
    return Settings(
        model="test-local",
        model_revision="test-double",
        runtime="HTTP-test-double",
        **kwargs,
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.example.com/v1/chat/completions",
        "http://localhost:8000/v1/chat/completions",
        "http://127.0.0.1:1/other",
        "http://user:secret@127.0.0.1/v1/chat/completions",
        "http://127.0.0.1/v1/chat/completions?key=secret",
        "http://127.0.0.1/v1/chat/completions#frag",
        "http://127.0.0.1:bad/v1/chat/completions",
    ],
)
def test_remote_ambiguous_or_credentialed_routes_rejected(endpoint):
    with pytest.raises(ValueError):
        validate_endpoint(endpoint)


def test_actual_request_does_not_leak_labels_or_case_metadata(server, suite):
    url, state = server
    provider = LocalProvider(url, settings())
    try:
        record = provider.call(suite.cases[0], 1, "real prompt")
    finally:
        provider.close()
    assert record.status == "OK"
    assert record.output_tokens == 8
    assert output_record(record, "LIVE_LOCAL_MODEL").raw == '{"literal":"unchanged"}'
    body = state["requests"][0]
    assert body["messages"] == [
        {"role": "system", "content": "real prompt"},
        {"role": "user", "content": suite.cases[0].input},
    ]
    assert body["seed"] == 43
    assert body["cache_prompt"] is False
    assert "expected" not in body and "critical" not in body


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("401", "HTTP_ERROR"),
        ("429", "HTTP_ERROR"),
        ("503", "HTTP_ERROR"),
        ("307", "HTTP_ERROR"),
        ("timeout", "TIMEOUT"),
        ("malformed", "MALFORMED_RESPONSE"),
        ("oversized", "OVERSIZED_RESPONSE"),
        ("truncated", "TRUNCATED"),
        ("refusal", "REFUSAL"),
        ("model-mismatch", "MALFORMED_RESPONSE"),
        ("wrong-content", "MALFORMED_RESPONSE"),
        ("bad-usage", "MALFORMED_RESPONSE"),
        ("bad-message", "MALFORMED_RESPONSE"),
        ("multiple", "MALFORMED_RESPONSE"),
    ],
)
def test_actual_http_faults_not_retried(server, suite, mode, expected):
    url, state = server
    state["mode"] = mode
    provider = LocalProvider(
        url, settings(timeout_seconds=0.03 if mode == "timeout" else 2.0)
    )
    try:
        record = provider.call(suite.cases[0], 0, "prompt")
    finally:
        provider.close()
    assert record.status == expected
    assert len(state["requests"]) == 1
    if mode == "malformed":
        assert record.raw == "{broken"


def test_runner_call_budget_preserves_every_unexecuted_case(server, suite, tmp_path):
    url, state = server
    run_local(
        tmp_path / "run",
        suite,
        "prompt",
        settings(max_calls=1, repeats=1),
        url,
        "limited",
    )
    manifest, records = read_run(tmp_path / "run")
    assert manifest.complete
    assert len(records) == 16
    assert len(state["requests"]) == 1
    assert sum(r.status == "BUDGET_SKIPPED" for r in records.values()) == 15


def test_connection_failure_is_explicit_without_traceback(suite):
    # Bind and close an ephemeral port; no listener remains on it.
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    provider = LocalProvider(
        f"http://127.0.0.1:{port}/v1/chat/completions", settings(timeout_seconds=0.05)
    )
    try:
        assert provider.call(suite.cases[0], 0, "prompt").status in {
            "TRANSPORT_ERROR",
            "TIMEOUT",
        }
    finally:
        provider.close()
