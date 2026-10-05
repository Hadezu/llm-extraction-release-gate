"""Bounded, single-attempt llama.cpp chat requests, restricted to loopback."""

import time
from urllib.parse import urlsplit

import httpx

from .contracts import Case, Record, Settings, strict_json

MAX_RESPONSE_BYTES = 131072


def validate_endpoint(endpoint: str) -> str:
    value = urlsplit(endpoint)
    if (
        value.scheme != "http"
        or value.hostname not in {"127.0.0.1", "::1"}
        or value.username
        or value.password
        or value.query
        or value.fragment
        or value.path != "/v1/chat/completions"
    ):
        raise ValueError(
            "Use a literal loopback HTTP /v1/chat/completions endpoint; no credentials or redirects"
        )
    _ = value.port  # Also rejects malformed ports.
    return endpoint


class LocalProvider:
    def __init__(self, endpoint: str, settings: Settings):
        self.endpoint = validate_endpoint(endpoint)
        self.settings = settings
        self.client = httpx.Client(
            timeout=settings.timeout_seconds, trust_env=False, follow_redirects=False
        )

    def close(self):
        self.client.close()

    def call(self, case: Case, repeat: int, prompt: str) -> Record:
        start = time.monotonic()
        common = {"case_id": case.id, "repeat": repeat}

        def result(status, **kwargs):
            return Record(
                **common,
                status=status,
                latency_ms=round((time.monotonic() - start) * 1000, 3),
                **kwargs,
            )

        body = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": case.input},
            ],
            "temperature": self.settings.temperature,
            "seed": self.settings.seed + repeat,
            "max_tokens": self.settings.max_tokens,
            "stream": False,
            "cache_prompt": False,
        }
        raw = None
        try:
            with self.client.stream("POST", self.endpoint, json=body) as response:
                status = response.status_code
                if status != 200:
                    return result("HTTP_ERROR", http_status=status)
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > MAX_RESPONSE_BYTES:
                        return result("OVERSIZED_RESPONSE", http_status=status)
                raw = chunks.decode("utf-8")
            parsed = strict_json(raw)
            if (
                not isinstance(parsed, dict)
                or not isinstance(parsed.get("choices"), list)
                or len(parsed["choices"]) != 1
            ):
                raise ValueError("Expected exactly one completion")
            if parsed.get("model") != self.settings.model:
                raise ValueError(
                    "Response model does not match the requested local alias"
                )
            choice = parsed["choices"][0]
            finish = choice["finish_reason"]
            message = choice["message"]
            content = message.get("content")
            if message.get("refusal") or finish == "content_filter":
                return result("REFUSAL", raw=raw, http_status=200)
            if not isinstance(content, str) or not isinstance(finish, str):
                raise ValueError("Invalid completion envelope")
            usage = parsed.get("usage") or {}
            # Preserve provider's exact output separately from the parsed extraction.
            return result(
                "OK" if finish == "stop" else "TRUNCATED",
                raw=raw,
                http_status=200,
                response_model=parsed.get("model"),
                finish_reason=finish,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            )
        except httpx.TimeoutException:
            return result("TIMEOUT")
        except httpx.TransportError:
            return result("TRANSPORT_ERROR")
        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            RecursionError,
        ):
            return result("MALFORMED_RESPONSE", raw=raw)


def output_record(record: Record, kind: str) -> Record:
    """Unwrap once, only for real HTTP captures. Never silently repair model text."""
    if record.status == "OK" and kind == "LIVE_LOCAL_MODEL":
        try:
            raw = strict_json(record.raw or "")["choices"][0]["message"]["content"]
            if not isinstance(raw, str):
                raise ValueError("Non-string model output")
            return record.model_copy(update={"raw": raw})
        except (ValueError, KeyError, IndexError, TypeError, RecursionError):
            return record.model_copy(update={"status": "MALFORMED_RESPONSE"})
    return record
