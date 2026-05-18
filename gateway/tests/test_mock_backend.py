from fastapi.testclient import TestClient

from serving.mock_backend.app import app

client = TestClient(app)


def test_mock_backend_lists_models() -> None:
    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [{"id": "mock", "object": "model", "owned_by": "mock-backend"}],
    }


def test_mock_backend_chat_completion_non_streaming() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "Explain KV cache briefly."}],
            "stream": False,
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"].startswith("chatcmpl-mock-")
    assert body["object"] == "chat.completion"
    assert body["model"] == "mock"
    assert body["choices"][0]["message"] == {
        "role": "assistant",
        "content": "Mock response to: Explain KV cache briefly.",
    }
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"]["total_tokens"] > 0


def test_mock_backend_chat_completion_streaming() -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: " in body
    assert '"object":"chat.completion.chunk"' in body
    assert '"content":"Mock"' in body
    assert '"content":" streaming"' in body
    assert '"content":" hello"' in body
    assert "data: [DONE]" in body
