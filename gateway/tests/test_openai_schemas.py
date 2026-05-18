import pytest
from pydantic import ValidationError

from gateway.app.schemas.openai import ChatCompletionRequest


def test_chat_completion_request_accepts_minimal_openai_shape() -> None:
    request = ChatCompletionRequest.model_validate(
        {
            "model": "mock",
            "messages": [{"role": "user", "content": "hello"}],
        }
    )

    assert request.model == "mock"
    assert request.messages[0].role == "user"
    assert request.stream is False


def test_chat_completion_request_requires_messages() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate({"model": "mock", "messages": []})
