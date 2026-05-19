import httpx
import pytest
from fastapi.testclient import TestClient

from gateway.app.core.config import Settings, get_settings
from gateway.app.main import app
from gateway.app.proxy.backend_client import BackendClient, BackendClientError
from gateway.app.proxy.model_aliases import resolve_model_route

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


class FakeBackendStream:
    async def aiter_text(self):
        yield 'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        yield "data: [DONE]\n\n"


class FakeAliasedBackendStream:
    async def aiter_text(self):
        yield (
            'data: {"id":"chunk-1","object":"chat.completion.chunk",'
            '"created":1,"model":"backend-model","choices":[]}\n\n'
        )
        yield "data: [DONE]\n\n"


def test_gateway_proxies_non_streaming_chat_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        *,
        json: dict,
    ) -> httpx.Response:
        assert str(self.base_url) == "http://localhost:9000/v1/"
        assert url == "/chat/completions"
        assert json["stream"] is False
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-mock-test",
                "object": "chat.completion",
                "created": 1,
                "model": json["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "proxied"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

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
    assert response.json()["choices"][0]["message"]["content"] == "proxied"


def test_gateway_maps_model_alias_for_non_streaming_chat_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        model_aliases_json='{"friendly":"backend-model"}'
    )

    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        *,
        json: dict,
    ) -> httpx.Response:
        assert json["model"] == "backend-model"
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-alias-test",
                "object": "chat.completion",
                "created": 1,
                "model": json["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "aliased"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "friendly",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "friendly"


def test_gateway_routes_non_streaming_chat_completion_with_model_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        model_routes_json='{"friendly":{"targets":[{"model":"backend-model","weight":1}]}}'
    )

    async def fake_create_chat_completion(
        self: BackendClient,
        request,
    ) -> dict:
        assert request.model == "backend-model"
        return {
            "id": "chatcmpl-route-test",
            "object": "chat.completion",
            "created": 1,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "routed"},
                    "finish_reason": "stop",
                }
            ],
        }

    monkeypatch.setattr(BackendClient, "create_chat_completion", fake_create_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "friendly",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "friendly"


def test_gateway_falls_back_to_next_route_target_on_backend_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        model_routes_json=(
            '{"friendly":{"targets":['
            '{"model":"bad-backend","weight":1},'
            '{"model":"good-backend","weight":1}'
            "]}}"
        )
    )
    routing_key = next(
        f"fallback-key-{index}"
        for index in range(100)
        if (
            resolve_model_route(
                "friendly",
                settings,
                routing_key=f"fallback-key-{index}",
            ).backend_model
            == "bad-backend"
        )
    )
    app.dependency_overrides[get_settings] = lambda: settings
    calls: list[str] = []

    async def fake_create_chat_completion(
        self: BackendClient,
        request,
    ) -> dict:
        calls.append(request.model)
        if request.model == "bad-backend":
            raise BackendClientError(
                status_code=404,
                message="model backend rejected the request",
                error_type="backend_error",
                code="backend_rejected_request",
            )
        return {
            "id": "chatcmpl-fallback-test",
            "object": "chat.completion",
            "created": 1,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "fallback"},
                    "finish_reason": "stop",
                }
            ],
        }

    monkeypatch.setattr(BackendClient, "create_chat_completion", fake_create_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": routing_key},
        json={
            "model": "friendly",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    assert calls == ["bad-backend", "good-backend"]
    assert response.json()["model"] == "friendly"


def test_gateway_sends_vllm_api_key_to_vllm_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        backend_type="vllm",
        vllm_api_key="local-vllm-key",
        model_aliases_json='{"qwen-small":"Qwen/Qwen2.5-1.5B-Instruct"}',
    )

    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        *,
        json: dict,
    ) -> httpx.Response:
        assert str(self.base_url) == "http://localhost:8000/v1/"
        assert self.headers["authorization"] == "Bearer local-vllm-key"
        assert json["model"] == "Qwen/Qwen2.5-1.5B-Instruct"
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-vllm-test",
                "object": "chat.completion",
                "created": 1,
                "model": json["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "vllm"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "qwen-small",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "qwen-small"


def test_gateway_proxies_streaming_chat_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_open_chat_completion_stream(
        self: BackendClient,
        request,
    ) -> FakeBackendStream:
        assert request.stream is True
        return FakeBackendStream()

    monkeypatch.setattr(
        BackendClient,
        "open_chat_completion_stream",
        fake_open_chat_completion_stream,
    )

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"choices":[{"delta":{"content":"hello"}}]}' in body
    assert "data: [DONE]" in body


def test_gateway_maps_model_alias_for_streaming_chat_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        model_aliases_json='{"friendly":"backend-model"}'
    )

    async def fake_open_chat_completion_stream(
        self: BackendClient,
        request,
    ) -> FakeAliasedBackendStream:
        assert request.model == "backend-model"
        return FakeAliasedBackendStream()

    monkeypatch.setattr(
        BackendClient,
        "open_chat_completion_stream",
        fake_open_chat_completion_stream,
    )

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "friendly",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert '"model":"friendly"' in body
    assert "backend-model" not in body


def test_gateway_rejects_unknown_model_alias() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={**AUTH_HEADERS, "X-Request-ID": "unknown-model-123"},
        json={
            "model": "unknown-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 400
    assert response.headers["x-request-id"] == "unknown-model-123"
    assert response.json() == {
        "error": {
            "message": "model not found: unknown-model",
            "type": "invalid_request_error",
            "code": "model_not_found",
            "param": None,
        },
        "request_id": "unknown-model-123",
    }


def test_gateway_maps_backend_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        *,
        json: dict,
    ) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "backend_timeout"


def test_gateway_maps_streaming_backend_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_open_chat_completion_stream(
        self: BackendClient,
        request,
    ) -> FakeBackendStream:
        raise BackendClientError(
            status_code=504,
            message="model backend timed out",
            error_type="timeout_error",
            code="backend_timeout",
        )

    monkeypatch.setattr(
        BackendClient,
        "open_chat_completion_stream",
        fake_open_chat_completion_stream,
    )

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH_HEADERS,
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "backend_timeout"


def teardown_function() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
