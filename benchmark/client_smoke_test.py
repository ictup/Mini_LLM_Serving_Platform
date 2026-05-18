import argparse
import os

from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test the gateway with the OpenAI SDK.")
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
        help="Model name to send to the gateway.",
    )
    parser.add_argument(
        "--prompt",
        default="Say hello from the mini LLM serving platform.",
        help="User prompt for the smoke test.",
    )
    parser.add_argument(
        "--skip-streaming",
        action="store_true",
        help="Run only the non-streaming SDK call.",
    )
    return parser.parse_args()


def create_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def run_non_streaming(client: OpenAI, model: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    content = response.choices[0].message.content or ""
    print(f"non_streaming: {content}")
    return content


def run_streaming(client: OpenAI, model: str, prompt: str) -> str:
    chunks = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    parts: list[str] = []
    print("streaming: ", end="", flush=True)
    for chunk in chunks:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            parts.append(delta)
    print()
    return "".join(parts)


def main() -> None:
    args = parse_args()
    client = create_client(base_url=args.base_url, api_key=args.api_key)

    non_streaming_text = run_non_streaming(client, args.model, args.prompt)
    if not non_streaming_text:
        raise RuntimeError("non-streaming response was empty")

    if args.skip_streaming:
        return

    streaming_text = run_streaming(client, args.model, args.prompt)
    if not streaming_text:
        raise RuntimeError("streaming response was empty")


if __name__ == "__main__":
    main()
