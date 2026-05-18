import asyncio
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from gateway.app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    ModelCard,
    ModelListResponse,
    Usage,
)

MOCK_MODEL_ID = "mock"

app = FastAPI(
    title="mock-llm-backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    return ModelListResponse(data=[ModelCard(id=MOCK_MODEL_ID, owned_by="mock-backend")])


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    if request.stream:
        return StreamingResponse(
            _stream_chat_completion(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    prompt_text = _last_user_message(request)
    content = f"Mock response to: {prompt_text}"
    prompt_tokens = _estimate_tokens(request)
    completion_tokens = len(content.split())

    return ChatCompletionResponse(
        id=f"chatcmpl-mock-{uuid.uuid4().hex[:12]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def _last_user_message(request: ChatCompletionRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content
    return request.messages[-1].content


def _estimate_tokens(request: ChatCompletionRequest) -> int:
    return sum(len(message.content.split()) for message in request.messages)


async def _stream_chat_completion(request: ChatCompletionRequest) -> AsyncIterator[str]:
    completion_id = f"chatcmpl-mock-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    prompt_text = _last_user_message(request)
    tokens = ["Mock", " streaming", " response", " to:", f" {prompt_text}"]

    for index, token in enumerate(tokens):
        chunk = ChatCompletionChunk(
            id=completion_id,
            created=created,
            model=request.model,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(
                        role="assistant" if index == 0 else None,
                        content=token,
                    ),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
        await asyncio.sleep(0.01)

    done_chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=request.model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {done_chunk.model_dump_json(exclude_none=True)}\n\n"
    yield "data: [DONE]\n\n"
