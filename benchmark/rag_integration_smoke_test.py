import argparse
import os

from openai import OpenAI

DEFAULT_CONTEXTS = [
    "The Mini LLM Serving Platform exposes an OpenAI-compatible Gateway.",
    "The Gateway can route requests to a mock backend locally or vLLM when GPU is available.",
    "Clients can switch backends by changing the base URL, API key, and model alias.",
]

RAG_SYSTEM_PROMPT = (
    "You are a RAG assistant. Answer the user question using only the provided context. "
    "If the context is insufficient, say that the context does not contain enough information."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test a RAG-style OpenAI-compatible call through the Gateway."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1"),
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY", "dev-key"),
        help="Bearer API key accepted by the gateway.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "mock"),
        help="Client-facing model alias to send to the gateway.",
    )
    parser.add_argument(
        "--question",
        default="How can a RAG app use this serving platform?",
        help="Question to answer using the provided context.",
    )
    parser.add_argument(
        "--context",
        action="append",
        dest="contexts",
        help="Retrieved context passage. Can be passed multiple times.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Completion temperature.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Maximum completion tokens.",
    )
    parser.add_argument(
        "--skip-streaming",
        action="store_true",
        help="Accepted for compatibility with local_e2e.py; this script is non-streaming.",
    )
    return parser.parse_args()


def select_contexts(contexts: list[str] | None) -> list[str]:
    selected = [context.strip() for context in contexts or [] if context.strip()]
    return selected or DEFAULT_CONTEXTS


def build_rag_messages(question: str, contexts: list[str]) -> list[dict[str, str]]:
    context_block = "\n".join(
        f"[{index}] {context.strip()}" for index, context in enumerate(contexts, start=1)
    )
    user_prompt = f"Context:\n{context_block}\n\nQuestion: {question.strip()}\n\nAnswer:"
    return [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def create_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def run_rag_completion(
    client: OpenAI,
    model: str,
    question: str,
    contexts: list[str],
    temperature: float,
    max_tokens: int,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=build_rag_messages(question, contexts),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
    )
    return response.choices[0].message.content or ""


def main() -> None:
    args = parse_args()
    contexts = select_contexts(args.contexts)
    client = create_client(base_url=args.base_url, api_key=args.api_key)
    answer = run_rag_completion(
        client=client,
        model=args.model,
        question=args.question,
        contexts=contexts,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    if not answer:
        raise RuntimeError("RAG smoke response was empty")
    print(f"rag_answer: {answer}")


if __name__ == "__main__":
    main()
