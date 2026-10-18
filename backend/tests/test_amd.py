import asyncio
import json
import logging
import time
import traceback

import httpx
import pytest
from pydantic import ValidationError

from app.config import AMDSettings
from app.inference.amd import AMDInference, configured_amd, retry_delay
from app.inference.contracts import CompletionRequest, InferenceError, Message

KEY = "synthetic-unit-test-token-never-real"
REQUEST = CompletionRequest(
    messages=(Message(role="user", content="Reply OK"),), max_tokens=8
)


def settings(**overrides):
    return AMDSettings(_env_file=None, AMD_API_KEY=KEY, AMD_MAX_RETRIES=1, **overrides)


def success(**overrides):
    return dict(
        model="self-dploy/DeepSeek-V4-Flash",
        choices=[
            {"message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}
        ],
        usage={
            "prompt_tokens": 9,
            "completion_tokens": 2,
            "total_tokens": 11,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
        **overrides,
    )


def execute(handler, config=None):
    adapter = AMDInference(config or settings(), transport=httpx.MockTransport(handler))
    return asyncio.run(adapter.complete(REQUEST))


def test_success_and_http_contract():
    def handler(request):
        assert (
            request.url == "https://developer.amd.com.cn/radeon/api/v1/chat/completions"
        )
        assert request.headers["Authorization"] == "Bearer " + KEY
        assert request.extensions["timeout"] == dict(
            connect=5, read=45, write=5, pool=5
        )
        assert json.loads(request.content) == {
            "model": "DeepSeek-V4-Flash",
            "messages": [{"role": "user", "content": "Reply OK"}],
            "max_tokens": 8,
            "stream": False,
        }
        return httpx.Response(200, json=success())

    result = execute(handler)
    assert result.text == "OK" and result.model == "self-dploy/DeepSeek-V4-Flash"
    assert result.requested_model == "DeepSeek-V4-Flash"
    assert result.usage.total_tokens == 11 and result.usage.reasoning_tokens == 0
    assert result.finish_reason == "stop" and result.attempts == 1
    assert result.latency_ms >= 0


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "authentication"),
        (403, "authentication"),
        (400, "http"),
        (404, "http"),
        (500, "http"),
        (503, "http"),
        (307, "http"),
    ],
)
def test_http_errors_do_not_retry_or_leak(status, code, caplog):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            json={"error": {"message": KEY}},
            headers={"Location": "https://evil.invalid/" + KEY},
        )

    with caplog.at_level(logging.DEBUG), pytest.raises(InferenceError) as caught:
        execute(handler)
    assert (
        len(calls) == 1 and caught.value.code == code and caught.value.status == status
    )
    assert KEY not in str(caught.value) + repr(caught.value) + caplog.text + "".join(
        traceback.format_exception(caught.value)
    )
    assert caught.value.__context__ is None


@pytest.mark.parametrize(
    "exception,code,retries",
    [
        (httpx.ReadTimeout, "timeout", 0),
        (httpx.WriteTimeout, "timeout", 0),
        (httpx.ReadError, "network", 0),
        (httpx.WriteError, "network", 0),
        (httpx.RemoteProtocolError, "network", 0),
        (httpx.ConnectTimeout, "timeout", 1),
        (httpx.PoolTimeout, "timeout", 1),
        (httpx.ConnectError, "network", 1),
    ],
)
def test_network_classification_and_retry_bounds(exception, code, retries, caplog):
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        raise exception(KEY, request=request)

    with pytest.raises(InferenceError) as caught:
        execute(handler)
    assert caught.value.code == code and caught.value.attempts == 1 + retries
    assert count == 1 + retries
    assert caught.value.__context__ is None
    assert KEY not in "".join(traceback.format_exception(caught.value)) + caplog.text


def test_rate_limit_then_success():
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return (
            httpx.Response(429, headers={"Retry-After": "0"})
            if count == 1
            else httpx.Response(200, json=success())
        )

    assert execute(handler).attempts == 2


def test_rate_limit_bound():
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(429, headers={"Retry-After": "0"}, text=KEY)

    with pytest.raises(InferenceError) as caught:
        execute(handler)
    assert count == 2 and caught.value.code == "rate_limit"


def test_large_retry_after_is_not_shortened():
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(429, headers={"Retry-After": "3600"})

    with pytest.raises(InferenceError) as caught:
        execute(handler)
    assert count == 1 and caught.value.code == "rate_limit"


def test_retry_after_dates_and_invalid_values():
    assert retry_delay("Thu, 01 Jan 2099 00:00:00 GMT", 1) > 100
    assert retry_delay("not-a-date", 1) == 0.25
    assert retry_delay("nan", 1) == float("inf")


def test_overall_deadline_and_no_replay():
    count = 0

    async def handler(request):
        nonlocal count
        count += 1
        await asyncio.sleep(2)
        return httpx.Response(200, json=success())

    start = time.perf_counter()
    with pytest.raises(InferenceError) as caught:
        execute(handler, settings(AMD_OVERALL_TIMEOUT=0.03))
    assert time.perf_counter() - start < 1 and count == 1
    assert caught.value.code == "timeout" and caught.value.__context__ is None


def test_cancellation_propagates():
    async def scenario():
        started = asyncio.Event()

        async def handler(request):
            started.set()
            await asyncio.sleep(5)

        adapter = AMDInference(settings(), transport=httpx.MockTransport(handler))
        task = asyncio.create_task(adapter.complete(REQUEST))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "body",
    [
        [],
        {},
        {"choices": []},
        {"error": {"message": KEY}},
        {"choices": [{"message": {"role": "assistant", "content": ""}}]},
        {"choices": [{"message": {"role": "assistant", "content": "   "}}]},
        {"choices": [{"message": {"role": "assistant", "content": None}}]},
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "partial"},
                    "finish_reason": "length",
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "unsafe"},
                    "finish_reason": "content_filter",
                }
            ]
        },
        {
            "choices": [
                {"message": {"role": "assistant", "content": "OK", "tool_calls": [{}]}}
            ]
        },
        {"choices": [{"message": {"role": "user", "content": "OK"}}]},
        {"choices": [{"message": {"role": "assistant", "content": KEY}}]},
    ],
)
def test_malformed_empty_or_model_failures(body):
    with pytest.raises(InferenceError) as caught:
        execute(lambda request: httpx.Response(200, json=body))
    assert (
        caught.value.code in ("invalid_response", "model")
        and caught.value.attempts == 1
    )
    assert KEY not in str(caught.value)


def test_non_json_is_sanitized():
    with pytest.raises(InferenceError) as caught:
        execute(lambda request: httpx.Response(200, text="<html>" + KEY + "</html>"))
    assert caught.value.code == "invalid_response"


@pytest.mark.parametrize(
    "usage",
    [False, [], {"total_tokens": -1}, {"total_tokens": "11"}, {"total_tokens": True}],
)
def test_invalid_usage_rejected(usage):
    body = success()
    body["usage"] = usage
    with pytest.raises(InferenceError):
        execute(lambda request: httpx.Response(200, json=body))


def test_optional_metadata_and_model_switch():
    body = success()
    del body["usage"]
    del body["model"]
    del body["choices"][0]["finish_reason"]

    def handler(request):
        assert json.loads(request.content)["model"] == "Gemma-4-31B-IT"
        return httpx.Response(200, json=body)

    result = execute(handler, settings(AMD_MODEL="Gemma-4-31B-IT"))
    assert result.model is None and result.usage.total_tokens is None
    assert result.finish_reason is None


def test_settings_protect_secret_and_use_explicit_aliases(tmp_path, monkeypatch):
    for name in ("AMD_API_KEY", "AMD_BASE_URL", "AMD_MODEL"):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / ".env"
    env.write_text(f"AMD_API_KEY={KEY}\nAMD_MODEL=Qwen3.8-27B\n")
    config = AMDSettings(_env_file=env)
    assert config.api_key.get_secret_value() == KEY and config.model == "Qwen3.8-27B"
    assert KEY not in repr(config) + str(config) + config.model_dump_json() + repr(
        config.model_dump()
    )
    monkeypatch.setenv("AMD_MODEL", "Gemma-4-31B-IT")
    assert AMDSettings(_env_file=env).model == "Gemma-4-31B-IT"


@pytest.mark.parametrize(
    "url",
    [
        "http://developer.amd.com.cn/radeon/api/v1",
        "https://evil.invalid",
        "https://developer.amd.com.cn/radeon/api/v1?key=" + KEY,
    ],
)
def test_unverified_endpoint_rejected(url):
    with pytest.raises(ValidationError) as caught:
        settings(AMD_BASE_URL=url)
    assert KEY not in str(caught.value)


def test_missing_key_never_sends(monkeypatch):
    monkeypatch.delenv("AMD_API_KEY", raising=False)

    def handler(request):
        pytest.fail("Must not send an unauthenticated request")

    with pytest.raises(InferenceError) as caught:
        execute(handler, AMDSettings(_env_file=None))
    assert caught.value.code == "configuration" and caught.value.attempts == 0


def test_factory_sanitizes_bad_configuration(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AMD_BASE_URL", "https://evil.invalid/" + KEY)
    with pytest.raises(InferenceError) as caught:
        configured_amd()
    assert caught.value.code == "configuration"
    assert caught.value.__context__ is None
    assert KEY not in "".join(traceback.format_exception(caught.value))


def test_escaped_credential_in_success_is_rejected():
    body = json.dumps(success()).replace(
        '"OK"', '"' + "".join("\\u%04x" % ord(c) for c in KEY) + '"'
    )
    with pytest.raises(InferenceError) as caught:
        execute(lambda request: httpx.Response(200, content=body.encode()))
    assert caught.value.code == "invalid_response"
    assert KEY not in str(caught.value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"AMD_CONNECT_TIMEOUT": 0},
        {"AMD_READ_TIMEOUT": -1},
        {"AMD_OVERALL_TIMEOUT": "nan"},
        {"AMD_MAX_RETRIES": 3},
    ],
)
def test_invalid_bounds(overrides):
    with pytest.raises(ValidationError):
        AMDSettings(_env_file=None, **overrides)


def test_only_scoped_inference_routes_added(tmp_path):
    from app.config import Settings
    from app.main import create_app

    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            database_path=str(tmp_path / "test.sqlite3"),
        )
    )
    paths = set(app.openapi()["paths"])
    assert paths == {
        "/api/v1/troubleshoot",
        "/api/v1/capture/structure",
        "/api/v1/ai/configuration",
        "/api/v1/capture/transcribe",
        "/api/v1/capture/voice/status",
        "/api/v1/health",
        "/api/v1/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/logout",
        "/api/v1/machines",
        "/api/v1/knowledge",
        "/api/v1/submissions",
        "/api/v1/submissions/{record_id}/revisions",
        "/api/v1/submissions/{record_id}/review",
        "/api/v1/submissions/{record_id}/history",
        "/api/v1/documents/{document_id}",
    }
