from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.error_codes import error_code_headers
from gateway.app.core.rate_limit import enforce_chat_rate_limit
from gateway.app.core.request_id import get_request_id
from gateway.app.core.request_limits import validate_chat_request_limits
from gateway.app.core.security import require_api_key
from gateway.app.observability.metrics import observe_streaming_chunks
from gateway.app.proxy.backend_client import BackendClient, BackendClientError
from gateway.app.proxy.model_aliases import ModelAliasError, resolve_model_alias
from gateway.app.proxy.streaming import rewrite_sse_model_events
from gateway.app.schemas.openai import ChatCompletionRequest, ErrorDetail, ErrorResponse

router = APIRouter(prefix="/v1", tags=["chat"])
logger = structlog.get_logger("gateway.chat")
SettingsDependency = Annotated[Settings, Depends(get_settings)]
APIKeyDependency = Annotated[str, Depends(require_api_key)]


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    raw_request: Request,
    request: ChatCompletionRequest,
    settings: SettingsDependency,
    api_key: APIKeyDependency,
) -> dict | JSONResponse | StreamingResponse:
    request_id = get_request_id(raw_request)
    validate_chat_request_limits(request, settings)
    try:
        backend_model = resolve_model_alias(request.model, settings)
    except ModelAliasError as exc:
        error = ErrorResponse(
            error=ErrorDetail(
                message=f"model not found: {exc.model}",
                type="invalid_request_error",
                code="model_not_found",
            ),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=400,
            content=error.model_dump(),
            headers=error_code_headers("model_not_found"),
        )

    rate_limit_lease = await enforce_chat_rate_limit(
        settings=settings,
        api_key=api_key,
        request=request,
        backend_model=backend_model,
    )
    stream_owns_rate_limit_lease = False

    try:
        logger.info(
            "chat_completion_request",
            request_id=request_id,
            model=request.model,
            backend_model=backend_model,
            stream=request.stream,
            backend_type=settings.backend_type,
        )

        client = BackendClient(settings)
        backend_request = request.model_copy(update={"model": backend_model})
        try:
            if request.stream:
                backend_stream = await client.open_chat_completion_stream(backend_request)
                client_stream = rewrite_sse_model_events(
                    backend_stream.aiter_text(),
                    backend_model=backend_model,
                    client_model=request.model,
                )
                observed_stream = observe_streaming_chunks(
                    client_stream,
                    client_model=request.model,
                    backend_model=backend_model,
                    metrics_enabled=settings.metrics_enabled,
                )
                stream_owns_rate_limit_lease = True
                return StreamingResponse(
                    rate_limit_lease.wrap_stream(observed_stream),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                    },
                )

            response = await client.create_chat_completion(backend_request)
            response["model"] = request.model
            return response
        except BackendClientError as exc:
            logger.warning(
                "chat_completion_backend_error",
                request_id=request_id,
                model=request.model,
                backend_model=backend_model,
                stream=request.stream,
                backend_type=settings.backend_type,
                status_code=exc.status_code,
                error_code=exc.code,
            )
            error = ErrorResponse(
                error=ErrorDetail(
                    message=exc.message,
                    type=exc.error_type,
                    code=exc.code,
                ),
                request_id=request_id,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=error.model_dump(),
                headers=error_code_headers(exc.code),
            )
    finally:
        if not stream_owns_rate_limit_lease:
            await rate_limit_lease.release()
