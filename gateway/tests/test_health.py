import pytest
from fastapi.testclient import TestClient

from gateway.app.main import app
from gateway.app.proxy.backend_client import BackendClient, BackendClientError

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_backend_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_list_models(self: BackendClient) -> dict:
        return {"data": [{"id": "mock"}]}

    monkeypatch.setattr(BackendClient, "list_models", fake_list_models)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "backend": "ok",
        "backend_type": "mock",
        "models": "1",
    }


def test_ready_returns_503_when_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_list_models(self: BackendClient) -> dict:
        raise BackendClientError(
            status_code=502,
            message="model backend unavailable",
            error_type="backend_error",
            code="backend_unavailable",
        )

    monkeypatch.setattr(BackendClient, "list_models", fake_list_models)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "backend": "backend_unavailable",
        "backend_type": "mock",
        "models": "unavailable",
    }


def test_ready_returns_503_when_backend_has_no_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_list_models(self: BackendClient) -> dict:
        return {"data": []}

    monkeypatch.setattr(BackendClient, "list_models", fake_list_models)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "backend": "ok",
        "backend_type": "mock",
        "models": "empty",
    }
