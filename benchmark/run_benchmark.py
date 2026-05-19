import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "smoke": {
        "concurrency": [1, 2, 4],
        "requests_per_level": 10,
        "max_tokens": 64,
        "warmup_requests": 0,
    },
    "portfolio": {
        "concurrency": [1, 4, 8, 16, 32],
        "requests_per_level": 100,
        "max_tokens": 128,
        "warmup_requests": 10,
    },
    "stress": {
        "concurrency": [1, 4, 8, 16, 32],
        "requests_per_level": 1000,
        "max_tokens": 128,
        "warmup_requests": 20,
    },
}


@dataclass(frozen=True)
class BenchmarkRequestResult:
    latency_seconds: float
    ok: bool
    status_code: int | None
    error: str | None = None
    error_code: str | None = None
    ttft_seconds: float | None = None
    inter_token_latencies_seconds: tuple[float, ...] = ()
    output_event_count: int = 0
    output_token_count: int | None = None
    tpot_seconds: float | None = None


@dataclass(frozen=True)
class BenchmarkSummary:
    concurrency: int
    total_requests: int
    success_count: int
    error_count: int
    error_rate: float
    error_status_counts: dict[str, int]
    error_code_counts: dict[str, int]
    rps: float
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    p99_latency_ms: float | None
    p50_ttft_ms: float | None
    p95_ttft_ms: float | None
    p99_ttft_ms: float | None
    p50_itl_ms: float | None
    p95_itl_ms: float | None
    mean_itl_ms: float | None
    p50_tpot_ms: float | None
    p95_tpot_ms: float | None
    mean_tpot_ms: float | None
    output_events_per_second: float | None
    output_event_count: int
    output_tokens_per_second: float | None
    output_token_count: int | None
    duration_seconds: float


class OutputTokenCounter:
    def __init__(self, tokenizer: Any) -> None:
        self.tokenizer = tokenizer

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self.tokenizer.encode(text).ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal async chat completion benchmark.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_DEFAULTS),
        default="smoke",
        help=(
            "Benchmark profile. Explicit --concurrency, --requests-per-level, "
            "--max-tokens, or --warmup-requests values override the profile defaults."
        ),
    )
    parser.add_argument("--base-url", default="http://localhost:8080/v1")
    parser.add_argument("--api-key", default="dev-key")
    parser.add_argument("--model", default="mock")
    parser.add_argument("--prompts", default="benchmark/prompts/short_prompts.jsonl")
    parser.add_argument("--concurrency", type=int, nargs="+")
    parser.add_argument("--requests-per-level", type=int)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--warmup-requests", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--output-dir", default="benchmark/results")
    parser.add_argument(
        "--output-tokenizer-path",
        help=(
            "Optional Hugging Face tokenizer.json path. When supplied, benchmark output "
            "token counts, output token/s, and TPOT are tokenizer-level metrics."
        ),
    )
    parser.add_argument(
        "--stream",
        choices=["false", "true"],
        default="false",
        help="Use OpenAI-compatible SSE streaming and record TTFT/ITL.",
    )
    args = parser.parse_args()
    apply_profile_defaults(args)
    validate_args(args)
    return args


def apply_profile_defaults(args: argparse.Namespace) -> argparse.Namespace:
    profile = PROFILE_DEFAULTS[args.profile]
    if args.concurrency is None:
        args.concurrency = profile["concurrency"]
    if args.requests_per_level is None:
        args.requests_per_level = profile["requests_per_level"]
    if args.max_tokens is None:
        args.max_tokens = profile["max_tokens"]
    if args.warmup_requests is None:
        args.warmup_requests = profile["warmup_requests"]
    return args


def validate_args(args: argparse.Namespace) -> None:
    if any(concurrency <= 0 for concurrency in args.concurrency):
        raise ValueError("--concurrency values must be positive")
    if args.requests_per_level <= 0:
        raise ValueError("--requests-per-level must be positive")
    if args.max_tokens <= 0:
        raise ValueError("--max-tokens must be positive")
    if args.warmup_requests < 0:
        raise ValueError("--warmup-requests cannot be negative")


def load_prompt_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {path}") from exc
        records.append(normalize_prompt_record(record, line_number=line_number))

    if not records:
        raise ValueError(f"prompt file has no records: {path}")
    return records


def normalize_prompt_record(record: dict[str, Any], line_number: int) -> dict[str, Any]:
    if "messages" in record:
        messages = record["messages"]
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"messages must be a non-empty list on line {line_number}")
        return {"messages": messages}

    prompt = record.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"prompt must be a non-empty string on line {line_number}")
    return {"messages": [{"role": "user", "content": prompt.strip()}]}


async def run_concurrency_level(
    client: httpx.AsyncClient,
    prompts: list[dict[str, Any]],
    model: str,
    concurrency: int,
    requests_per_level: int,
    max_tokens: int,
    stream: bool,
    output_token_counter: OutputTokenCounter | None,
) -> BenchmarkSummary:
    semaphore = asyncio.Semaphore(concurrency)
    started_at = time.perf_counter()

    async def bounded_request(index: int) -> BenchmarkRequestResult:
        prompt_record = prompts[index % len(prompts)]
        async with semaphore:
            return await send_chat_completion_request(
                client=client,
                model=model,
                messages=prompt_record["messages"],
                max_tokens=max_tokens,
                stream=stream,
                output_token_counter=output_token_counter,
            )

    results = await asyncio.gather(
        *(bounded_request(index) for index in range(requests_per_level))
    )
    duration_seconds = time.perf_counter() - started_at
    return summarize_results(
        concurrency=concurrency,
        results=list(results),
        duration_seconds=duration_seconds,
    )


async def run_warmup_requests(
    client: httpx.AsyncClient,
    prompts: list[dict[str, Any]],
    model: str,
    max_tokens: int,
    stream: bool,
    warmup_requests: int,
    output_token_counter: OutputTokenCounter | None,
) -> tuple[int, int]:
    ok_count = 0
    error_count = 0
    for index in range(warmup_requests):
        prompt_record = prompts[index % len(prompts)]
        result = await send_chat_completion_request(
            client=client,
            model=model,
            messages=prompt_record["messages"],
            max_tokens=max_tokens,
            stream=stream,
            output_token_counter=output_token_counter,
        )
        if result.ok:
            ok_count += 1
        else:
            error_count += 1
    return ok_count, error_count


async def send_chat_completion_request(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    stream: bool,
    output_token_counter: OutputTokenCounter | None,
) -> BenchmarkRequestResult:
    if stream:
        return await send_streaming_chat_completion_request(
            client=client,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            output_token_counter=output_token_counter,
        )

    started_at = time.perf_counter()
    try:
        response = await client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        latency_seconds = time.perf_counter() - started_at
        if response.status_code >= 400:
            error_text = response.text[:200]
            return BenchmarkRequestResult(
                latency_seconds=latency_seconds,
                ok=False,
                status_code=response.status_code,
                error=error_text,
                error_code=extract_error_code(error_text),
            )
        response_payload = response.json()
        output_text = extract_non_stream_content(response_payload)
        output_token_count = count_output_tokens(output_text, output_token_counter)
        return BenchmarkRequestResult(
            latency_seconds=latency_seconds,
            ok=True,
            status_code=response.status_code,
            output_token_count=output_token_count,
        )
    except Exception as exc:
        return BenchmarkRequestResult(
            latency_seconds=time.perf_counter() - started_at,
            ok=False,
            status_code=None,
            error=type(exc).__name__,
            error_code=type(exc).__name__,
        )


async def send_streaming_chat_completion_request(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    output_token_counter: OutputTokenCounter | None,
) -> BenchmarkRequestResult:
    started_at = time.perf_counter()
    first_token_at: float | None = None
    previous_token_at: float | None = None
    inter_token_latencies: list[float] = []
    output_event_count = 0
    output_chunks: list[str] = []

    try:
        async with client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", errors="replace")
                return BenchmarkRequestResult(
                    latency_seconds=time.perf_counter() - started_at,
                    ok=False,
                    status_code=response.status_code,
                    error=body[:200],
                    error_code=extract_error_code(body),
                )

            async for line in response.aiter_lines():
                payload = parse_sse_data_line(line)
                if payload is None:
                    continue
                if payload == "[DONE]":
                    break

                content = extract_stream_content(payload)
                if not content:
                    continue

                now = time.perf_counter()
                output_event_count += 1
                output_chunks.append(content)
                if first_token_at is None:
                    first_token_at = now
                elif previous_token_at is not None:
                    inter_token_latencies.append(now - previous_token_at)
                previous_token_at = now

        latency_seconds = time.perf_counter() - started_at
        ttft_seconds = first_token_at - started_at if first_token_at is not None else None
        output_token_count = count_output_tokens("".join(output_chunks), output_token_counter)
        return BenchmarkRequestResult(
            latency_seconds=latency_seconds,
            ok=True,
            status_code=response.status_code,
            ttft_seconds=ttft_seconds,
            inter_token_latencies_seconds=tuple(inter_token_latencies),
            output_event_count=output_event_count,
            output_token_count=output_token_count,
            tpot_seconds=calculate_tpot_seconds(
                latency_seconds=latency_seconds,
                ttft_seconds=ttft_seconds,
                output_token_count=output_token_count,
            ),
        )
    except Exception as exc:
        return BenchmarkRequestResult(
            latency_seconds=time.perf_counter() - started_at,
            ok=False,
            status_code=None,
            error=type(exc).__name__,
            error_code=type(exc).__name__,
        )


def parse_sse_data_line(line: str) -> str | None:
    if not line.startswith("data:"):
        return None
    return line.removeprefix("data:").strip()


def extract_stream_content(payload: str) -> str | None:
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(event, dict):
        return None

    choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None

    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        return None

    content = delta.get("content")
    if isinstance(content, str) and content:
        return content
    return None


def extract_non_stream_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str):
        return content
    return ""


def count_output_tokens(text: str, counter: OutputTokenCounter | None) -> int | None:
    if counter is None:
        return None
    return counter.count(text)


def calculate_tpot_seconds(
    *,
    latency_seconds: float,
    ttft_seconds: float | None,
    output_token_count: int | None,
) -> float | None:
    if ttft_seconds is None or output_token_count is None or output_token_count <= 1:
        return None
    decode_seconds = max(0.0, latency_seconds - ttft_seconds)
    return decode_seconds / (output_token_count - 1)


def extract_error_code(payload: str) -> str | None:
    try:
        error_response = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(error_response, dict):
        return None

    error = error_response.get("error")
    if not isinstance(error, dict):
        return None

    code = error.get("code")
    if isinstance(code, str) and code:
        return code
    return None


def summarize_results(
    concurrency: int,
    results: list[BenchmarkRequestResult],
    duration_seconds: float,
) -> BenchmarkSummary:
    total_requests = len(results)
    successful_latencies = [result.latency_seconds for result in results if result.ok]
    successful_ttfts = [
        result.ttft_seconds for result in results if result.ok and result.ttft_seconds is not None
    ]
    inter_token_latencies = [
        latency
        for result in results
        if result.ok
        for latency in result.inter_token_latencies_seconds
    ]
    tpot_values = [
        result.tpot_seconds for result in results if result.ok and result.tpot_seconds is not None
    ]
    output_event_count = sum(result.output_event_count for result in results if result.ok)
    output_token_counts = [
        result.output_token_count
        for result in results
        if result.ok and result.output_token_count is not None
    ]
    output_token_count = sum(output_token_counts) if output_token_counts else None
    success_count = len(successful_latencies)
    error_count = total_requests - success_count
    error_rate = error_count / total_requests if total_requests else 0.0
    rps = total_requests / duration_seconds if duration_seconds > 0 else 0.0
    error_status_counts = count_error_statuses(results)
    error_code_counts = count_error_codes(results)

    return BenchmarkSummary(
        concurrency=concurrency,
        total_requests=total_requests,
        success_count=success_count,
        error_count=error_count,
        error_rate=error_rate,
        error_status_counts=error_status_counts,
        error_code_counts=error_code_counts,
        rps=rps,
        p50_latency_ms=percentile_ms(successful_latencies, 50),
        p95_latency_ms=percentile_ms(successful_latencies, 95),
        p99_latency_ms=percentile_ms(successful_latencies, 99),
        p50_ttft_ms=percentile_ms(successful_ttfts, 50),
        p95_ttft_ms=percentile_ms(successful_ttfts, 95),
        p99_ttft_ms=percentile_ms(successful_ttfts, 99),
        p50_itl_ms=percentile_ms(inter_token_latencies, 50),
        p95_itl_ms=percentile_ms(inter_token_latencies, 95),
        mean_itl_ms=mean_ms(inter_token_latencies),
        p50_tpot_ms=percentile_ms(tpot_values, 50),
        p95_tpot_ms=percentile_ms(tpot_values, 95),
        mean_tpot_ms=mean_ms(tpot_values),
        output_events_per_second=rate_per_second(output_event_count, duration_seconds),
        output_event_count=output_event_count,
        output_tokens_per_second=rate_per_second(output_token_count, duration_seconds)
        if output_token_count is not None
        else None,
        output_token_count=output_token_count,
        duration_seconds=duration_seconds,
    )


def percentile_ms(values_seconds: list[float], percentile: float) -> float | None:
    if not values_seconds:
        return None

    sorted_values = sorted(values_seconds)
    if len(sorted_values) == 1:
        return round(sorted_values[0] * 1000, 2)

    rank = (len(sorted_values) - 1) * (percentile / 100)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = rank - lower_index
    value = sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    return round(value * 1000, 2)


def mean_ms(values_seconds: list[float]) -> float | None:
    if not values_seconds:
        return None
    return round((sum(values_seconds) / len(values_seconds)) * 1000, 2)


def rate_per_second(count: int, duration_seconds: float) -> float | None:
    if duration_seconds <= 0:
        return None
    return round(count / duration_seconds, 2)


def count_error_statuses(results: list[BenchmarkRequestResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        if result.ok:
            continue
        key = str(result.status_code) if result.status_code is not None else "exception"
        counts[key] = counts.get(key, 0) + 1
    return counts


def count_error_codes(results: list[BenchmarkRequestResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        if result.ok:
            continue
        key = result.error_code or result.error or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


async def run_benchmark(args: argparse.Namespace) -> list[BenchmarkSummary]:
    stream = args.stream == "true"
    prompts = load_prompt_records(Path(args.prompts))
    output_token_counter = load_output_token_counter(args.output_tokenizer_path)
    headers = {"Authorization": f"Bearer {args.api_key}"}
    timeout = httpx.Timeout(args.timeout_seconds)
    summaries: list[BenchmarkSummary] = []

    async with httpx.AsyncClient(
        base_url=args.base_url,
        headers=headers,
        timeout=timeout,
    ) as client:
        if args.warmup_requests:
            ok_count, error_count = await run_warmup_requests(
                client=client,
                prompts=prompts,
                model=args.model,
                max_tokens=args.max_tokens,
                stream=stream,
                warmup_requests=args.warmup_requests,
                output_token_counter=output_token_counter,
            )
            print(
                f"warmup_requests={args.warmup_requests} "
                f"ok={ok_count} errors={error_count}"
            )

        for concurrency in args.concurrency:
            summary = await run_concurrency_level(
                client=client,
                prompts=prompts,
                model=args.model,
                concurrency=concurrency,
                requests_per_level=args.requests_per_level,
                max_tokens=args.max_tokens,
                stream=stream,
                output_token_counter=output_token_counter,
            )
            summaries.append(summary)
            print_summary_row(summary)

    write_results(args, summaries)
    return summaries


def print_summary_row(summary: BenchmarkSummary) -> None:
    p50 = format_optional_float(summary.p50_latency_ms)
    p95 = format_optional_float(summary.p95_latency_ms)
    p99 = format_optional_float(summary.p99_latency_ms)
    p50_ttft = format_optional_float(summary.p50_ttft_ms)
    p95_ttft = format_optional_float(summary.p95_ttft_ms)
    p99_ttft = format_optional_float(summary.p99_ttft_ms)
    p50_itl = format_optional_float(summary.p50_itl_ms)
    p95_itl = format_optional_float(summary.p95_itl_ms)
    mean_itl = format_optional_float(summary.mean_itl_ms)
    p50_tpot = format_optional_float(summary.p50_tpot_ms)
    p95_tpot = format_optional_float(summary.p95_tpot_ms)
    mean_tpot = format_optional_float(summary.mean_tpot_ms)
    output_rate = format_optional_float(summary.output_events_per_second)
    output_token_rate = format_optional_float(summary.output_tokens_per_second)
    output_token_count = format_optional_int(summary.output_token_count)
    error_statuses = format_count_map(summary.error_status_counts)
    error_codes = format_count_map(summary.error_code_counts)
    print(
        f"concurrency={summary.concurrency} total={summary.total_requests} "
        f"ok={summary.success_count} errors={summary.error_count} "
        f"rps={summary.rps:.2f} p50_ms={p50} p95_ms={p95} p99_ms={p99} "
        f"p50_ttft_ms={p50_ttft} p95_ttft_ms={p95_ttft} p99_ttft_ms={p99_ttft} "
        f"p50_itl_ms={p50_itl} p95_itl_ms={p95_itl} mean_itl_ms={mean_itl} "
        f"p50_tpot_ms={p50_tpot} p95_tpot_ms={p95_tpot} mean_tpot_ms={mean_tpot} "
        f"output_events_per_second={output_rate} output_events={summary.output_event_count} "
        f"output_tokens_per_second={output_token_rate} output_tokens={output_token_count} "
        f"error_rate={summary.error_rate:.2%} error_statuses={error_statuses} "
        f"error_codes={error_codes}"
    )


def format_optional_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def format_optional_int(value: int | None) -> str:
    if value is None:
        return "n/a"
    return str(value)


def format_count_map(value: dict[str, int]) -> str:
    if not value:
        return "none"
    return ",".join(f"{key}:{value[key]}" for key in sorted(value))


def write_results(args: argparse.Namespace, summaries: list[BenchmarkSummary]) -> Path:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"benchmark_{int(time.time())}.json"
    payload = {
        "benchmark_schema_version": 3,
        "profile": args.profile,
        "base_url": args.base_url,
        "model": args.model,
        "stream": args.stream == "true",
        "prompts": args.prompts,
        "requests_per_level": args.requests_per_level,
        "concurrency": args.concurrency,
        "max_tokens": args.max_tokens,
        "warmup_requests": args.warmup_requests,
        "timeout_seconds": args.timeout_seconds,
        "output_tokenizer_path": args.output_tokenizer_path,
        "output_token_count_source": (
            "tokenizer_file" if args.output_tokenizer_path else "not_configured"
        ),
        "created_at_unix": int(time.time()),
        "summaries": [asdict(summary) for summary in summaries],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote_results={output_path}")
    return output_path


def load_output_token_counter(tokenizer_path: str | None) -> OutputTokenCounter | None:
    if not tokenizer_path:
        return None

    path = Path(tokenizer_path)
    if not path.exists():
        raise FileNotFoundError(f"output tokenizer file not found: {path}")

    try:
        from tokenizers import Tokenizer
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "output tokenizer counting requires the optional 'tokenizers' package"
        ) from exc

    return OutputTokenCounter(Tokenizer.from_file(str(path)))


def main() -> None:
    args = parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
