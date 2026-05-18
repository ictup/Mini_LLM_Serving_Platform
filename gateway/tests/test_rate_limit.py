import pytest
from fastapi.testclient import TestClient

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.rate_limit import RATE_LIMIT_KEY_PREFIX, RateLimiter
from gateway.app.main import app
from gateway.app.proxy.backend_client import BackendClient

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, name: str) -> int:
        self.counts[name] = self.counts.get(name, 0) + 1
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


def enable_rate_limit(monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis, rpm: int) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        rate_limit_enabled=True,
        rate_limit_rpm=rpm,
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
    assert len(fake_redis.counts) == 1
    redis_key = next(iter(fake_redis.counts))
    assert redis_key.startswith(f"{RATE_LIMIT_KEY_PREFIX}:")
    assert "dev-key" not in redis_key


def teardown_function() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
