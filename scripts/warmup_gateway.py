import argparse
import json
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warm up the Gateway with a small chat request.")
    parser.add_argument("--base-url", default="http://localhost:8080/v1")
    parser.add_argument("--api-key", default="dev-key")
    parser.add_argument("--model", default="mock")
    parser.add_argument("--prompt", default="Respond with one short sentence.")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--sleep-seconds", type=float, default=5)
    return parser.parse_args()


def warmup_once(args: argparse.Namespace) -> dict:
    url = f"{args.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": 8,
        "stream": False,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {args.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body)


def main() -> int:
    args = parse_args()
    last_error: str | None = None

    for attempt in range(1, args.attempts + 1):
        try:
            response = warmup_once(args)
            choice_count = len(response.get("choices", []))
            print(f"gateway warmup succeeded on attempt {attempt}; choices={choice_count}")
            return 0
        except (
            OSError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ) as exc:
            last_error = str(exc)
            print(f"gateway warmup attempt {attempt} failed: {last_error}")
            if attempt < args.attempts:
                time.sleep(args.sleep_seconds)

    print(f"gateway warmup failed after {args.attempts} attempts: {last_error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
