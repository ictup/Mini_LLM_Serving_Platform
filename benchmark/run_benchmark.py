import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class BenchmarkRequestResult:
    latency_seconds: float
    ok: bool
    status_code: int | None
    error: str | None = None
    ttft_seconds: float | None = None
    inter_token_latencies_seconds: tuple[float, ...] = ()
    output_event_count: int = 0


@dataclass(frozen=True)
class BenchmarkSummary:
    concurrency: int
    total_requests: int
    success_count: int
    error_count: int
    error_rate: float
    rps: float
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    p50_ttft_ms: float | None
    p95_ttft_ms: float | None
    mean_itl_ms: float | None
    output_event_count: int
    duration_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal async chat completion benchmark.")
    parser.add_argument("--base-url", default="http://localhost:8080/v1")
    parser.add_argument("--api-key", default="dev-key")
    parser.add_argument("--model", default="mock")
    parser.add_argument("--prompts", default="benchmark/prompts/short_prompts.jsonl")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--requests-per-level", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--output-dir", default="benchmark/results")
    parser.add_argument(
        "--stream",
        choices=["false", "true"],
        default="false",
        help="Use OpenAI-compatible SSE streaming and record TTFT/ITL.",
    )
    return parser.parse_args()


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


async def send_chat_completion_request(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    stream: bool,
) -> BenchmarkRequestResult:
    if stream:
        return await send_streaming_chat_completion_request(
            client=client,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
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
            return BenchmarkRequestResult(
                latency_seconds=latency_seconds,
                ok=False,
                status_code=response.status_code,
                error=response.text[:200],
            )
        response.json()
        return BenchmarkRequestResult(
            latency_seconds=latency_seconds,
            ok=True,
            status_code=response.status_code,
        )
    except Exception as exc:
        return BenchmarkRequestResult(
            latency_seconds=time.perf_counter() - started_at,
            ok=False,
            status_code=None,
            error=type(exc).__name__,
        )


async def send_streaming_chat_completion_request(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
) -> BenchmarkRequestResult:
    started_at = time.perf_counter()
    first_token_at: float | None = None
    previous_token_at: float | None = None
    inter_token_latencies: list[float] = []
    output_event_count = 0

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
                if first_token_at is None:
                    first_token_at = now
                elif previous_token_at is not None:
                    inter_token_latencies.append(now - previous_token_at)
                previous_token_at = now

        latency_seconds = time.perf_counter() - started_at
        return BenchmarkRequestResult(
            latency_seconds=latency_seconds,
            ok=True,
            status_code=response.status_code,
            ttft_seconds=first_token_at - started_at if first_token_at is not None else None,
            inter_token_latencies_seconds=tuple(inter_token_latencies),
            output_event_count=output_event_count,
        )
    except Exception as exc:
        return BenchmarkRequestResult(
            latency_seconds=time.perf_counter() - started_at,
            ok=False,
            status_code=None,
            error=type(exc).__name__,
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
    output_event_count = sum(result.output_event_count for result in results if result.ok)
    success_count = len(successful_latencies)
    error_count = total_requests - success_count
    error_rate = error_count / total_requests if total_requests else 0.0
    rps = total_requests / duration_seconds if duration_seconds > 0 else 0.0

    return BenchmarkSummary(
        concurrency=concurrency,
        total_requests=total_requests,
        success_count=success_count,
        error_count=error_count,
        error_rate=error_rate,
        rps=rps,
        p50_latency_ms=percentile_ms(successful_latencies, 50),
        p95_latency_ms=percentile_ms(successful_latencies, 95),
        p50_ttft_ms=percentile_ms(successful_ttfts, 50),
        p95_ttft_ms=percentile_ms(successful_ttfts, 95),
        mean_itl_ms=mean_ms(inter_token_latencies),
        output_event_count=output_event_count,
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


async def run_benchmark(args: argparse.Namespace) -> list[BenchmarkSummary]:
    stream = args.stream == "true"
    prompts = load_prompt_records(Path(args.prompts))
    headers = {"Authorization": f"Bearer {args.api_key}"}
    timeout = httpx.Timeout(args.timeout_seconds)
    summaries: list[BenchmarkSummary] = []

    async with httpx.AsyncClient(
        base_url=args.base_url,
        headers=headers,
        timeout=timeout,
    ) as client:
        for concurrency in args.concurrency:
            summary = await run_concurrency_level(
                client=client,
                prompts=prompts,
                model=args.model,
                concurrency=concurrency,
                requests_per_level=args.requests_per_level,
                max_tokens=args.max_tokens,
                stream=stream,
            )
            summaries.append(summary)
            print_summary_row(summary)

    write_results(args, summaries)
    return summaries


def print_summary_row(summary: BenchmarkSummary) -> None:
    p50 = format_optional_float(summary.p50_latency_ms)
    p95 = format_optional_float(summary.p95_latency_ms)
    p50_ttft = format_optional_float(summary.p50_ttft_ms)
    p95_ttft = format_optional_float(summary.p95_ttft_ms)
    mean_itl = format_optional_float(summary.mean_itl_ms)
    print(
        f"concurrency={summary.concurrency} total={summary.total_requests} "
        f"ok={summary.success_count} errors={summary.error_count} "
        f"rps={summary.rps:.2f} p50_ms={p50} p95_ms={p95} "
        f"p50_ttft_ms={p50_ttft} p95_ttft_ms={p95_ttft} "
        f"mean_itl_ms={mean_itl} output_events={summary.output_event_count} "
        f"error_rate={summary.error_rate:.2%}"
    )


def format_optional_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def write_results(args: argparse.Namespace, summaries: list[BenchmarkSummary]) -> Path:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"benchmark_{int(time.time())}.json"
    payload = {
        "base_url": args.base_url,
        "model": args.model,
        "stream": args.stream == "true",
        "requests_per_level": args.requests_per_level,
        "concurrency": args.concurrency,
        "summaries": [asdict(summary) for summary in summaries],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote_results={output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
