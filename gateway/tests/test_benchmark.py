import argparse

import pytest

from benchmark.run_benchmark import (
    BenchmarkRequestResult,
    OutputTokenCounter,
    apply_profile_defaults,
    calculate_tpot_seconds,
    count_output_tokens,
    extract_error_code,
    extract_non_stream_content,
    extract_stream_content,
    load_prompt_records,
    normalize_prompt_record,
    parse_sse_data_line,
    percentile_ms,
    summarize_results,
)


def test_percentile_ms_interpolates_values() -> None:
    assert percentile_ms([0.1, 0.2, 0.3], 50) == 200.0
    assert percentile_ms([0.1, 0.2, 0.3], 95) == 290.0


def test_summarize_results_counts_success_errors_and_rps() -> None:
    summary = summarize_results(
        concurrency=2,
        duration_seconds=2.0,
        results=[
            BenchmarkRequestResult(latency_seconds=0.1, ok=True, status_code=200),
            BenchmarkRequestResult(latency_seconds=0.2, ok=True, status_code=200),
            BenchmarkRequestResult(
                latency_seconds=0.05,
                ok=False,
                status_code=500,
                error="backend error",
                error_code="backend_error",
            ),
        ],
    )

    assert summary.total_requests == 3
    assert summary.success_count == 2
    assert summary.error_count == 1
    assert summary.error_rate == pytest.approx(1 / 3)
    assert summary.rps == 1.5
    assert summary.p50_latency_ms == 150.0
    assert summary.p99_latency_ms == 199.0
    assert summary.error_status_counts == {"500": 1}
    assert summary.error_code_counts == {"backend_error": 1}


def test_summarize_results_includes_streaming_metrics() -> None:
    summary = summarize_results(
        concurrency=1,
        duration_seconds=1.0,
        results=[
            BenchmarkRequestResult(
                latency_seconds=0.5,
                ok=True,
                status_code=200,
                ttft_seconds=0.1,
                inter_token_latencies_seconds=(0.02, 0.04),
                output_event_count=3,
                output_token_count=6,
                tpot_seconds=0.08,
            ),
            BenchmarkRequestResult(
                latency_seconds=0.7,
                ok=True,
                status_code=200,
                ttft_seconds=0.2,
                inter_token_latencies_seconds=(0.06,),
                output_event_count=2,
                output_token_count=4,
                tpot_seconds=0.1,
            ),
        ],
    )

    assert summary.p50_ttft_ms == 150.0
    assert summary.p95_ttft_ms == 195.0
    assert summary.p99_ttft_ms == 199.0
    assert summary.p50_itl_ms == 40.0
    assert summary.p95_itl_ms == 58.0
    assert summary.mean_itl_ms == 40.0
    assert summary.p50_tpot_ms == 90.0
    assert summary.p95_tpot_ms == 99.0
    assert summary.mean_tpot_ms == 90.0
    assert summary.output_events_per_second == 5.0
    assert summary.output_event_count == 5
    assert summary.output_tokens_per_second == 10.0
    assert summary.output_token_count == 10


def test_apply_profile_defaults_uses_portfolio_values_without_overriding_explicit_values() -> None:
    args = argparse.Namespace(
        profile="portfolio",
        concurrency=None,
        requests_per_level=None,
        max_tokens=64,
        warmup_requests=None,
    )

    apply_profile_defaults(args)

    assert args.concurrency == [1, 4, 8, 16, 32]
    assert args.requests_per_level == 100
    assert args.max_tokens == 64
    assert args.warmup_requests == 10


def test_parse_sse_data_line_extracts_data_payload() -> None:
    assert parse_sse_data_line("data: {\"hello\":\"world\"}") == '{"hello":"world"}'
    assert parse_sse_data_line(": keep-alive") is None


def test_extract_stream_content_reads_delta_content() -> None:
    payload = (
        '{"choices":[{"delta":{"content":"hello"},"index":0,'
        '"finish_reason":null}]}'
    )

    assert extract_stream_content(payload) == "hello"
    assert extract_stream_content("[DONE]") is None


def test_extract_non_stream_content_reads_first_choice_message() -> None:
    payload = {"choices": [{"message": {"role": "assistant", "content": "hello"}}]}

    assert extract_non_stream_content(payload) == "hello"
    assert extract_non_stream_content({"choices": []}) == ""


def test_output_token_counter_counts_with_tokenizer_like_object() -> None:
    class Encoded:
        ids = [1, 2, 3]

    class Tokenizer:
        def encode(self, text: str) -> Encoded:
            assert text == "hello"
            return Encoded()

    counter = OutputTokenCounter(Tokenizer())

    assert count_output_tokens("hello", counter) == 3
    assert count_output_tokens("hello", None) is None


def test_calculate_tpot_seconds_uses_decode_time_after_ttft() -> None:
    assert calculate_tpot_seconds(
        latency_seconds=1.1,
        ttft_seconds=0.1,
        output_token_count=6,
    ) == pytest.approx(0.2)
    assert calculate_tpot_seconds(
        latency_seconds=1.1,
        ttft_seconds=0.1,
        output_token_count=1,
    ) is None


def test_extract_error_code_reads_openai_error_envelope() -> None:
    payload = '{"error":{"message":"rate limit exceeded","code":"rate_limit_exceeded"}}'

    assert extract_error_code(payload) == "rate_limit_exceeded"
    assert extract_error_code("not json") is None


def test_normalize_prompt_record_accepts_prompt() -> None:
    assert normalize_prompt_record({"prompt": " hello "}, line_number=1) == {
        "messages": [{"role": "user", "content": "hello"}]
    }


def test_load_prompt_records_reads_jsonl(tmp_path) -> None:
    prompt_file = tmp_path / "prompts.jsonl"
    prompt_file.write_text(
        '{"prompt":"hello"}\n'
        '{"messages":[{"role":"system","content":"be brief"},{"role":"user","content":"hi"}]}\n',
        encoding="utf-8",
    )

    records = load_prompt_records(prompt_file)

    assert records == [
        {"messages": [{"role": "user", "content": "hello"}]},
        {
            "messages": [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hi"},
            ]
        },
    ]
