"""Async AMD transport. No agents, retrieval, public routes, or automatic fallbacks."""

import asyncio
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from pydantic import ValidationError

from app.config import AMDSettings
from app.inference.contracts import (
    CompletionRequest,
    CompletionResult,
    InferenceError,
    TokenUsage,
)


def retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            seconds = float(value)
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                seconds = (date - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                seconds = 0.25 * attempt
        if not math.isfinite(seconds):
            return math.inf
        return max(0, seconds)
    return 0.25 * attempt


class AMDInference:
    def __init__(
        self,
        settings: AMDSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._settings = settings
        self._transport = transport

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        start = time.perf_counter()
        attempts = 0
        settings = self._settings
        key = settings.api_key.get_secret_value().strip()
        if not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise InferenceError("configuration")
        # Bound all attempts, connection phases and retry sleeps with one deadline.
        error = None
        try:
            async with asyncio.timeout(settings.overall_timeout):
                async with httpx.AsyncClient(
                    transport=self._transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx.Timeout(
                        settings.read_timeout,
                        connect=settings.connect_timeout,
                        write=settings.connect_timeout,
                        pool=settings.connect_timeout,
                    ),
                ) as client:
                    for attempts in range(1, settings.max_retries + 2):
                        retry = False
                        delay = 0.25 * attempts
                        try:
                            response = await client.post(
                                settings.base_url + "/chat/completions",
                                headers={"Authorization": "Bearer " + key},
                                json={
                                    "model": settings.model,
                                    "messages": [
                                        m.model_dump() for m in request.messages
                                    ],
                                    "max_tokens": request.max_tokens,
                                    "stream": False,
                                    **(
                                        {
                                            "response_format": request.response_format.model_dump()
                                        }
                                        if request.response_format is not None
                                        else {}
                                    ),
                                },
                            )
                        except (httpx.ConnectTimeout, httpx.PoolTimeout):
                            error = InferenceError("timeout")
                            retry = True  # No completion bytes sent.
                        except httpx.ConnectError:
                            error = InferenceError("network")
                            retry = True  # Connection establishment failed.
                        except httpx.TimeoutException:
                            error = InferenceError(
                                "timeout"
                            )  # Read/write outcome is ambiguous.
                        except httpx.RequestError:
                            error = InferenceError(
                                "network"
                            )  # Never replay mid-flight failures.
                        else:
                            if response.status_code in (401, 403):
                                error = InferenceError(
                                    "authentication", status=response.status_code
                                )
                            elif response.status_code == 429:
                                error = InferenceError("rate_limit", status=429)
                                delay = retry_delay(
                                    response.headers.get("retry-after"), attempts
                                )
                                retry = True
                            elif not response.is_success:
                                # Even 5xx may follow completed inference. No automatic POST replay.
                                error = InferenceError(
                                    "http", status=response.status_code
                                )
                            else:
                                try:
                                    result = self._parse(response, key)
                                except InferenceError as exc:
                                    # Token counts can still be useful when a completion is
                                    # truncated or unusable. Never retain text/error payloads.
                                    exc.usage = self._failure_usage(response, key)
                                    raise
                                return CompletionResult(
                                    **result,
                                    provider="amd",
                                    requested_model=settings.model,
                                    latency_ms=(time.perf_counter() - start) * 1000,
                                    attempts=attempts,
                                )
                        remaining = settings.overall_timeout - (
                            time.perf_counter() - start
                        )
                        if (
                            not retry
                            or attempts > settings.max_retries
                            or delay >= remaining
                        ):
                            break
                        await asyncio.sleep(delay)
        except TimeoutError:
            error = InferenceError("timeout")
        except InferenceError as exc:
            error = exc
        # Raise outside transport exception handlers: no original exception chain/payload.
        assert error is not None
        error.attempts = attempts
        error.latency_ms = (time.perf_counter() - start) * 1000
        raise error from None

    @staticmethod
    def _failure_usage(response: httpx.Response, key: str) -> TokenUsage | None:
        try:
            data = response.json()
        except (ValueError, UnicodeError):
            return None
        if not isinstance(data, dict) or key in str(data):
            return None
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        counts = {name: usage.get(name) for name in TokenUsage.model_fields}
        details = usage.get("completion_tokens_details")
        if counts["reasoning_tokens"] is None and isinstance(details, dict):
            counts["reasoning_tokens"] = details.get("reasoning_tokens")
        if any(
            v is not None and (type(v) is not int or v < 0) for v in counts.values()
        ):
            return None
        return TokenUsage(**counts)

    @staticmethod
    def _parse(response: httpx.Response, key: str) -> dict:
        # A provider must not echo the credential into a successful response either.
        if key.encode() in response.content:
            raise InferenceError("invalid_response", status=response.status_code)
        try:
            data = response.json()
        except (ValueError, UnicodeError):
            data = None
        if not isinstance(data, dict):
            raise InferenceError("invalid_response", status=response.status_code)
        if "error" in data:
            raise InferenceError("model", status=response.status_code)
        choices = data.get("choices")
        if (
            not isinstance(choices, list)
            or len(choices) != 1
            or not isinstance(choices[0], dict)
        ):
            raise InferenceError("invalid_response", status=response.status_code)
        choice = choices[0]
        message = choice.get("message")
        finish = choice.get("finish_reason")
        if finish not in (None, "stop"):
            raise InferenceError("model", status=response.status_code)
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise InferenceError("invalid_response", status=response.status_code)
        text = message.get("content")
        if message.get("tool_calls") or message.get("refusal"):
            raise InferenceError("model", status=response.status_code)
        if not isinstance(text, str) or not text.strip():
            raise InferenceError("invalid_response", status=response.status_code)
        model = data.get("model")
        if model is not None and (not isinstance(model, str) or not model.strip()):
            raise InferenceError("invalid_response", status=response.status_code)
        if key in text or (isinstance(model, str) and key in model):
            raise InferenceError("invalid_response", status=response.status_code)
        usage = data.get("usage")
        if usage is None:
            usage = {}
        if not isinstance(usage, dict):
            raise InferenceError("invalid_response", status=response.status_code)
        counts = {k: usage.get(k) for k in TokenUsage.model_fields}
        details = usage.get("completion_tokens_details")
        if counts["reasoning_tokens"] is None and isinstance(details, dict):
            counts["reasoning_tokens"] = details.get("reasoning_tokens")
        if any(
            v is not None and (type(v) is not int or v < 0) for v in counts.values()
        ):
            raise InferenceError("invalid_response", status=response.status_code)
        return dict(
            text=text.strip(),
            model=model,
            finish_reason=finish,
            usage=TokenUsage(**counts),
        )


def configured_amd() -> AMDInference:
    """Lazy configuration keeps Stage 2 usable with no AMD credentials."""
    try:
        settings = AMDSettings()
    except ValidationError:
        settings = None
    if settings is None:
        raise InferenceError("configuration")
    return AMDInference(settings)
