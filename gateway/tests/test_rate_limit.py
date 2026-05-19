import pytest
from fastapi.testclient import TestClient

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.rate_limit import (
    RATE_LIMIT_RPM_KEY_PREFIX,
    RATE_LIMIT_TPM_KEY_PREFIX,
    RateLimiter,
    estimate_chat_token_cost,
    estimate_text_tokens,
)
from gateway.app.main import app
from gateway.app.proxy.backend_client import BackendClient
from gateway.app.schemas.openai import ChatCompletionRequest, Message

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, name: str) -> int:
        self.counts[name] = self.counts.get(name, 0) + 1
        return self.counts[name]

    async def incrby(self, name: str, amount: int) -> int:
        self.counts[name] = self.counts.get(name, 0) + amount
        return self.counts[name]

    async def expire(self, name: str, time: int) -> None:
        self.expirations[name] = time


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture(autouse=True)
def override_backend(monkeypatch: pytest.MonkeyPatch):
    async def fake_create_chat_completion(
        self: BackendClient,
        request,
    ) -> dict:
        return {
            "id": "chatcmpl-rate-limit-test",
            "object": "chat.completion",
            "created": 1,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "allowed"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(BackendClient, "create_chat_completion", fake_create_chat_completion)


def enable_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
    rpm: int,
    tpm: int = 1_000,
    default_completion_tokens: int = 1,
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        rate_limit_enabled=True,
        rate_limit_rpm=rpm,
        rate_limit_tpm=tpm,
        rate_limit_default_completion_tokens=default_completion_tokens,
    )

    def fake_create_rate_limiter(settings: Settings) -> RateLimiter:
        return RateLimiter(redis_client=fake_redis)

    monkeypatch.setattr(
        "gateway.app.core.rate_limit.create_rate_limiter",
        fake_create_rate_limiter,
    )


def test_rate_limit_allows_requests_under_limit(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> None:
    enable_rate_limit(monkeypatch, fake_redis, rpm=2)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "allowed"


def test_rate_limit_blocks_requests_over_limit(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> None:
    enable_rate_limit(monkeypatch, fake_redis, rpm=1)

    first = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )
    second = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "rate-limit-req-123"},
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello again"}],
            "stream": False,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["x-request-id"] == "rate-limit-req-123"
    assert second.json() == {
        "error": {
            "message": "rate limit exceeded",
            "type": "rate_limit_error",
            "code": "rate_limit_exceeded",
            "param": None,
        },
        "request_id": "rate-limit-req-123",
    }


def test_rate_limit_redis_key_hashes_api_key(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> None:
    enable_rate_limit(monkeypatch, fake_redis, rpm=2)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    redis_keys = list(fake_redis.counts)
    assert any(redis_key.startswith(f"{RATE_LIMIT_RPM_KEY_PREFIX}:") for redis_key in redis_keys)
    assert any(redis_key.startswith(f"{RATE_LIMIT_TPM_KEY_PREFIX}:") for redis_key in redis_keys)
    assert all("dev-key" not in redis_key for redis_key in redis_keys)


def test_estimate_text_tokens_uses_word_or_character_estimate() -> None:
    assert estimate_text_tokens("") == 0
    assert estimate_text_tokens("hello world") == 3
    assert estimate_text_tokens("one two three four five") == 6


def test_estimate_chat_token_cost_includes_prompt_and_completion_budget() -> None:
    request = ChatCompletionRequest(
        model="mock",
        messages=[
            Message(role="system", content="Be concise."),
            Message(role="user", content="Explain the Gateway."),
        ],
        max_tokens=10,
    )

    assert estimate_chat_token_cost(request, default_completion_tokens=256) == 28


def test_estimate_chat_token_cost_uses_default_completion_budget_when_missing() -> None:
    request = ChatCompletionRequest(
        model="mock",
        messages=[Message(role="user", content="hello")],
    )

    assert estimate_chat_token_cost(request, default_completion_tokens=8) == 16


def test_token_rate_limit_blocks_requests_over_tpm(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> None:
    enable_rate_limit(monkeypatch, fake_redis, rpm=10, tpm=8, default_completion_tokens=1)

    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "token-limit-req-123"},
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "one two three four"}],
            "max_tokens": 1,
            "stream": False,
        },
    )

    assert response.status_code == 429
    assert response.headers["x-request-id"] == "token-limit-req-123"
    assert response.json() == {
        "error": {
            "message": "token rate limit exceeded",
            "type": "rate_limit_error",
            "code": "token_rate_limit_exceeded",
            "param": None,
        },
        "request_id": "token-limit-req-123",
    }


def test_token_rate_limit_accumulates_tokens_per_api_key(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> None:
    enable_rate_limit(monkeypatch, fake_redis, rpm=10, tpm=18, default_completion_tokens=1)

    payload = {
        "model": "mock",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 1,
        "stream": False,
    }

    first = client.post("/v1/chat/completions", headers=AUTH_HEADERS, json=payload)
    second = client.post("/v1/chat/completions", headers=AUTH_HEADERS, json=payload)
    third = client.post("/v1/chat/completions", headers=AUTH_HEADERS, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "token_rate_limit_exceeded"


def teardown_function() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
