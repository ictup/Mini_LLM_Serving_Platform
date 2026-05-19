import pytest

from gateway.app.core.token_accounting import (
    ModelAwareTokenCounter,
    candidate_models,
    estimate_chat_token_cost,
    estimate_qwen2_text_tokens,
    load_tokenizer_paths,
    load_tokenizer_profiles,
)
from gateway.app.schemas.openai import ChatCompletionRequest, Message


def test_qwen2_profile_counts_cjk_characters_as_tokens() -> None:
    assert estimate_qwen2_text_tokens("你好世界") == 4


def test_model_aware_chat_cost_uses_backend_model_profile() -> None:
    request = ChatCompletionRequest(
        model="qwen-small",
        messages=[Message(role="user", content="hello world")],
        max_tokens=1,
    )

    token_cost = estimate_chat_token_cost(
        request,
        default_completion_tokens=256,
        tokenizer_profiles_json='{"Qwen/Qwen2.5-0.5B-Instruct":"qwen2"}',
        backend_model="Qwen/Qwen2.5-0.5B-Instruct",
    )

    assert token_cost == 11


def test_model_aware_counter_falls_back_from_missing_tokenizer_file_to_profile() -> None:
    tokenizer_paths = load_tokenizer_paths('{"qwen-small":"missing.json"}')
    counter = ModelAwareTokenCounter(
        profiles={"qwen-small": "qwen2"},
        tokenizer_paths=tokenizer_paths,
    )

    assert counter.count_text("hello world", client_model="qwen-small", backend_model=None) == 4


def test_candidate_models_prefers_client_alias_then_backend_model() -> None:
    assert candidate_models(client_model="qwen-small", backend_model="Qwen/model") == (
        "qwen-small",
        "Qwen/model",
    )


def test_tokenizer_profile_config_requires_json_object() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        load_tokenizer_profiles("[]")
