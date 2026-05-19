import pytest
from fastapi.testclient import TestClient

from gateway.app.main import app
from gateway.app.observability.metrics import count_completed_sse_content_chunks
from gateway.app.proxy.backend_client import BackendClient

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


class FakeMetricsBackendStream:
    async def aiter_text(self):
        yield 'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        yield 'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        yield 'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
        yield "data: [DONE]\n\n"


def test_metrics_endpoint_exposes_prometheus_format() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "gateway_http_requests_total" in response.text
    assert "gateway_http_errors_total" in response.text
    assert "gateway_http_rejections_total" in response.text
    assert "gateway_http_request_duration_seconds" in response.text


def test_metrics_count_successful_requests() -> None:
    health_response = client.get("/health")
    metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert (
        'gateway_http_requests_total{method="GET",path="/health",status_code="200"}'
        in metrics_response.text
    )
    assert "gateway_http_request_duration_seconds_bucket" in metrics_response.text
    assert 'method="GET",path="/health"' in metrics_response.text


def test_metrics_count_error_responses() -> None:
    error_response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )
    metrics_response = client.get("/metrics")

    assert error_response.status_code == 401
    assert error_response.headers["x-gateway-error-code"] == "invalid_api_key"
    assert (
        'gateway_http_errors_total{method="POST",path="/v1/chat/completions",status_code="401"}'
        in metrics_response.text
    )
    assert (
        'gateway_http_rejections_total{method="POST",path="/v1/chat/completions",'
        'reason="invalid_api_key",status_code="401"}' in metrics_response.text
    )


def test_count_completed_sse_content_chunks_ignores_role_and_done_events() -> None:
    buffer = (
        'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    remaining, count = count_completed_sse_content_chunks(buffer)

    assert remaining == ""
    assert count == 1


def test_metrics_count_streaming_ttft_duration_and_output_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_open_chat_completion_stream(
        self: BackendClient,
        request,
    ) -> FakeMetricsBackendStream:
        assert request.stream is True
        return FakeMetricsBackendStream()

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

    metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert "hello" in body
    assert "gateway_stream_ttft_seconds_bucket" in metrics_response.text
    assert "gateway_stream_duration_seconds_bucket" in metrics_response.text
    assert "gateway_stream_output_chunks_total" in metrics_response.text
    assert 'model="mock"' in metrics_response.text
    assert 'backend_model="mock"' in metrics_response.text
