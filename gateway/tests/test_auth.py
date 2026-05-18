from fastapi.testclient import TestClient

from gateway.app.main import app

client = TestClient(app)


def test_health_does_not_require_api_key() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"].startswith("req_")


def test_chat_requires_authorization_header() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    body = response.json()
    assert body == {
        "error": {
            "message": "invalid api key",
            "type": "authentication_error",
            "code": "invalid_api_key",
            "param": None,
        },
        "request_id": response.headers["x-request-id"],
    }


def test_chat_rejects_invalid_api_key() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer wrong-key"},
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_chat_rejects_malformed_authorization_header() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "dev-key"},
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"
    assert response.json()["request_id"] == response.headers["x-request-id"]
