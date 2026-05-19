import pytest
from fastapi.testclient import TestClient

import gateway.app.core.request_limits as request_limits
from gateway.app.core.config import Settings, get_settings
from gateway.app.main import app
from gateway.app.proxy.backend_client import BackendClient

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


@pytest.fixture(autouse=True)
def override_backend(monkeypatch: pytest.MonkeyPatch):
    async def fake_create_chat_completion(
        self: BackendClient,
        request,
    ) -> dict:
        return {
            "id": "chatcmpl-request-limit-test",
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


def test_request_body_size_limit_rejects_large_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        request_limits,
        "get_settings",
        lambda: Settings(max_request_body_bytes=80),
    )

    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "body-limit-req-123"},
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "x" * 200}],
            "stream": False,
        },
    )

    assert response.status_code == 413
    assert response.headers["x-request-id"] == "body-limit-req-123"
    assert response.json() == {
        "error": {
            "message": "request body too large",
            "type": "invalid_request_error",
            "code": "request_body_too_large",
            "param": None,
        },
        "request_id": "body-limit-req-123",
    }


def test_chat_request_limit_rejects_too_many_messages() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(max_chat_messages=1)

    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "message-count-limit-req-123"},
        json={
            "model": "mock",
            "messages": [
                {"role": "user", "content": "first"},
                {"role": "user", "content": "second"},
            ],
            "stream": False,
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "message": "too many chat messages",
            "type": "invalid_request_error",
            "code": "too_many_messages",
            "param": "messages",
        },
        "request_id": "message-count-limit-req-123",
    }


def test_chat_request_limit_rejects_oversized_single_message() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(max_chat_message_chars=5)

    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "message-char-limit-req-123"},
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "too long"}],
            "stream": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "chat_message_too_large"
    assert response.json()["error"]["param"] == "messages[0].content"
    assert response.json()["request_id"] == "message-char-limit-req-123"


def test_chat_request_limit_rejects_total_message_chars() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(max_chat_total_message_chars=8)

    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "total-char-limit-req-123"},
        json={
            "model": "mock",
            "messages": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
            ],
            "stream": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "chat_messages_too_large"
    assert response.json()["error"]["param"] == "messages"
    assert response.json()["request_id"] == "total-char-limit-req-123"


def test_chat_request_limit_allows_request_under_limits() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        max_chat_messages=2,
        max_chat_message_chars=16,
        max_chat_total_message_chars=32,
    )

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


def teardown_function() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
