import json
from collections.abc import AsyncIterator


async def rewrite_sse_model_events(
    chunks: AsyncIterator[str],
    backend_model: str,
    client_model: str,
) -> AsyncIterator[str]:
    if backend_model == client_model:
        async for chunk in chunks:
            yield chunk
        return

    buffer = ""
    async for chunk in chunks:
        buffer += chunk
        while "\n\n" in buffer:
            event, buffer = buffer.split("\n\n", 1)
            yield f"{rewrite_sse_event_model(event, backend_model, client_model)}\n\n"

    if buffer:
        yield rewrite_sse_event_model(buffer, backend_model, client_model)


def rewrite_sse_event_model(event: str, backend_model: str, client_model: str) -> str:
    rewritten_lines: list[str] = []
    for line in event.splitlines():
        if not line.startswith("data: "):
            rewritten_lines.append(line)
            continue

        payload = line.removeprefix("data: ")
        if payload == "[DONE]":
            rewritten_lines.append(line)
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            rewritten_lines.append(line)
            continue

        if isinstance(data, dict) and data.get("model") == backend_model:
            data["model"] = client_model
            rewritten_lines.append(f"data: {json.dumps(data, separators=(',', ':'))}")
        else:
            rewritten_lines.append(line)

    return "\n".join(rewritten_lines)
