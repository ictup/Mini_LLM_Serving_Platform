from fastapi.testclient import TestClient

from gateway.app.core.config import Settings, get_settings
from gateway.app.main import app

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


def test_models_requires_api_key() -> None:
    response = client.get("/v1/models")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_gateway_lists_default_model_aliases() -> None:
    response = client.get("/v1/models", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [{"id": "mock", "object": "model", "owned_by": "gateway"}],
    }


def test_gateway_lists_configured_model_aliases() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        model_aliases_json='{"friendly":"backend-model","mock":"mock"}'
    )

    response = client.get(
        "/v1/models",
        headers={**AUTH_HEADERS, "X-Request-ID": "models-aliases-123"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "models-aliases-123"
    assert response.json() == {
        "object": "list",
        "data": [
            {"id": "friendly", "object": "model", "owned_by": "gateway"},
            {"id": "mock", "object": "model", "owned_by": "gateway"},
        ],
    }


def teardown_function() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
