from fastapi.testclient import TestClient

from gateway.app.main import app

client = TestClient(app)


def test_generates_request_id_when_header_is_missing() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"].startswith("req_")


def test_propagates_valid_request_id_header() -> None:
    response = client.get("/health", headers={"X-Request-ID": "client-request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "client-request-123"


def test_replaces_invalid_request_id_header() -> None:
    response = client.get("/health", headers={"X-Request-ID": "bad value"})

    assert response.status_code == 200
    assert response.headers["x-request-id"].startswith("req_")


def test_backend_error_response_includes_request_id(
    monkeypatch,
) -> None:
    import httpx

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
        headers={
            "Authorization": "Bearer dev-key",
            "X-Request-ID": "client-timeout-123",
        },
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 504
    assert response.headers["x-request-id"] == "client-timeout-123"
    assert response.json()["request_id"] == "client-timeout-123"
