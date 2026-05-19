import pytest
from fastapi.testclient import TestClient

from gateway.app.api import routes_chat
from gateway.app.main import app
from gateway.app.proxy.backend_client import BackendClient

client = TestClient(app)


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def info(self, event: str, **kwargs) -> None:
        self.events.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs) -> None:
        self.events.append(("warning", event, kwargs))


def test_chat_logging_records_metadata_without_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_logger = FakeLogger()

    async def fake_create_chat_completion(
        self: BackendClient,
        request,
    ) -> dict:
        return {
            "id": "chatcmpl-log-test",
            "object": "chat.completion",
            "created": 1,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "logged safely"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(routes_chat, "logger", fake_logger)
    monkeypatch.setattr(BackendClient, "create_chat_completion", fake_create_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers={
            "Authorization": "Bearer dev-key",
            "X-Request-ID": "log-req-123",
        },
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": "SECRET_PROMPT_DO_NOT_LOG"}],
            "stream": False,
        },
    )

    assert response.status_code == 200

    log_event = next(
        event for level, event, _kwargs in fake_logger.events if event == "chat_completion_request"
    )
    log_kwargs = next(
        kwargs for _level, event, kwargs in fake_logger.events if event == "chat_completion_request"
    )

    assert log_event == "chat_completion_request"
    assert log_kwargs == {
        "request_id": "log-req-123",
        "model": "mock",
        "backend_model": "mock",
        "stream": False,
        "backend_type": "mock",
        "route_strategy": "alias",
        "route_attempt": 1,
    }
    assert "SECRET_PROMPT_DO_NOT_LOG" not in str(fake_logger.events)
