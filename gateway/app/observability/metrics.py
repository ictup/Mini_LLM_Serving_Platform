import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from gateway.app.core.config import get_settings
from gateway.app.core.error_codes import ERROR_CODE_HEADER, UNKNOWN_ERROR_CODE

HTTP_REQUESTS_TOTAL = Counter(
    "gateway_http_requests_total",
    "Total HTTP requests handled by the gateway.",
    ["method", "path", "status_code"],
)
HTTP_ERRORS_TOTAL = Counter(
    "gateway_http_errors_total",
    "Total HTTP error responses returned by the gateway.",
    ["method", "path", "status_code"],
)
HTTP_REJECTIONS_TOTAL = Counter(
    "gateway_http_rejections_total",
    "Total Gateway error responses grouped by stable rejection reason.",
    ["method", "path", "status_code", "reason"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "gateway_http_request_duration_seconds",
    "Gateway HTTP request duration in seconds.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
STREAM_TTFT_SECONDS = Histogram(
    "gateway_stream_ttft_seconds",
    "Time from Gateway stream start until the first non-empty SSE content chunk.",
    ["model", "backend_model"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
STREAM_DURATION_SECONDS = Histogram(
    "gateway_stream_duration_seconds",
    "Gateway streaming response duration in seconds.",
    ["model", "backend_model", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
STREAM_OUTPUT_CHUNKS_TOTAL = Counter(
    "gateway_stream_output_chunks_total",
    "Total non-empty SSE content chunks emitted by Gateway streaming responses.",
    ["model", "backend_model"],
)


async def prometheus_metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    if not settings.metrics_enabled:
        return await call_next(request)

    started_at = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - started_at

    method = request.method
    path = normalized_route_path(request)
    status_code = str(response.status_code)

    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status_code=status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration_seconds)

    if response.status_code >= 400:
        HTTP_ERRORS_TOTAL.labels(method=method, path=path, status_code=status_code).inc()
        reason = response.headers.get(ERROR_CODE_HEADER, UNKNOWN_ERROR_CODE)
        HTTP_REJECTIONS_TOTAL.labels(
            method=method,
            path=path,
            status_code=status_code,
            reason=reason,
        ).inc()

    return response


def normalized_route_path(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return str(route_path)
    return "unmatched"


def render_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def observe_streaming_chunks(
    chunks: AsyncIterator[str],
    *,
    client_model: str,
    backend_model: str,
    metrics_enabled: bool,
) -> AsyncIterator[str]:
    if not metrics_enabled:
        async for chunk in chunks:
            yield chunk
        return

    started_at = time.perf_counter()
    first_content_seen = False
    status = "completed"
    buffer = ""

    try:
        async for chunk in chunks:
            buffer += chunk
            buffer, content_chunk_count = count_completed_sse_content_chunks(buffer)
            if content_chunk_count:
                now = time.perf_counter()
                if not first_content_seen:
                    STREAM_TTFT_SECONDS.labels(
                        model=client_model,
                        backend_model=backend_model,
                    ).observe(now - started_at)
                    first_content_seen = True
                STREAM_OUTPUT_CHUNKS_TOTAL.labels(
                    model=client_model,
                    backend_model=backend_model,
                ).inc(content_chunk_count)

            yield chunk
    except BaseException:
        status = "interrupted"
        raise
    finally:
        if buffer:
            _, content_chunk_count = count_completed_sse_content_chunks(buffer, flush=True)
            if content_chunk_count:
                now = time.perf_counter()
                if not first_content_seen:
                    STREAM_TTFT_SECONDS.labels(
                        model=client_model,
                        backend_model=backend_model,
                    ).observe(now - started_at)
                STREAM_OUTPUT_CHUNKS_TOTAL.labels(
                    model=client_model,
                    backend_model=backend_model,
                ).inc(content_chunk_count)

        STREAM_DURATION_SECONDS.labels(
            model=client_model,
            backend_model=backend_model,
            status=status,
        ).observe(time.perf_counter() - started_at)


def count_completed_sse_content_chunks(buffer: str, flush: bool = False) -> tuple[str, int]:
    content_chunk_count = 0
    while "\n\n" in buffer:
        event, buffer = buffer.split("\n\n", 1)
        content_chunk_count += count_sse_event_content_chunks(event)

    if flush and buffer:
        content_chunk_count += count_sse_event_content_chunks(buffer)
        buffer = ""

    return buffer, content_chunk_count


def count_sse_event_content_chunks(event: str) -> int:
    content_chunk_count = 0
    for line in event.splitlines():
        if not line.startswith("data:"):
            continue

        payload = line.removeprefix("data:").strip()
        if payload == "[DONE]":
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if sse_payload_has_content(data):
            content_chunk_count += 1

    return content_chunk_count


def sse_payload_has_content(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return False

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return False

    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        return False

    content = delta.get("content")
    return isinstance(content, str) and bool(content)
