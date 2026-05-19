from benchmark.rag_integration_smoke_test import (
    DEFAULT_CONTEXTS,
    RAG_SYSTEM_PROMPT,
    build_rag_messages,
    select_contexts,
)


def test_select_contexts_uses_defaults_when_no_context_is_supplied() -> None:
    assert select_contexts(None) == DEFAULT_CONTEXTS
    assert select_contexts(["", "   "]) == DEFAULT_CONTEXTS


def test_select_contexts_strips_custom_contexts() -> None:
    assert select_contexts([" first passage ", "second passage"]) == [
        "first passage",
        "second passage",
    ]


def test_build_rag_messages_numbers_contexts_and_includes_question() -> None:
    messages = build_rag_messages(
        question="What does the Gateway do?",
        contexts=["Gateway exposes an OpenAI-compatible API.", "vLLM runs the model."],
    )

    assert messages[0] == {"role": "system", "content": RAG_SYSTEM_PROMPT}
    assert messages[1]["role"] == "user"
    assert "[1] Gateway exposes an OpenAI-compatible API." in messages[1]["content"]
    assert "[2] vLLM runs the model." in messages[1]["content"]
    assert "Question: What does the Gateway do?" in messages[1]["content"]
