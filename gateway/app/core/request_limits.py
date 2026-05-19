from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.request_id import REQUEST_ID_HEADER, get_request_id, normalize_request_id
from gateway.app.schemas.openai import ChatCompletionRequest, ErrorDetail, ErrorResponse


class ChatRequestLimitExceeded(Exception):
    def __init__(self, *, message: str, code: str, param: str) -> None:
        self.message = message
        self.code = code
        self.param = param


async def request_body_size_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    content_length = _parse_content_length(request.headers.get("content-length"))

    if content_length is not None and content_length > settings.max_request_body_bytes:
        request_id = get_request_id(request) or normalize_request_id(
            request.headers.get(REQUEST_ID_HEADER)
        )
        error = ErrorResponse(
            error=ErrorDetail(
                message="request body too large",
                type="invalid_request_error",
                code="request_body_too_large",
            ),
            request_id=request_id,
        )
        response = JSONResponse(status_code=413, content=error.model_dump())
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    return await call_next(request)


def validate_chat_request_limits(
    request: ChatCompletionRequest,
    settings: Settings,
) -> None:
    if len(request.messages) > settings.max_chat_messages:
        raise ChatRequestLimitExceeded(
            message="too many chat messages",
            code="too_many_messages",
            param="messages",
        )

    total_chars = 0
    for index, message in enumerate(request.messages):
        message_chars = len(message.content)
        if message_chars > settings.max_chat_message_chars:
            raise ChatRequestLimitExceeded(
                message="chat message too large",
                code="chat_message_too_large",
                param=f"messages[{index}].content",
            )
        total_chars += message_chars

    if total_chars > settings.max_chat_total_message_chars:
        raise ChatRequestLimitExceeded(
            message="chat messages too large",
            code="chat_messages_too_large",
            param="messages",
        )


async def chat_request_limit_exception_handler(
    request: Request,
    exc: ChatRequestLimitExceeded,
) -> JSONResponse:
    error = ErrorResponse(
        error=ErrorDetail(
            message=exc.message,
            type="invalid_request_error",
            code=exc.code,
            param=exc.param,
        ),
        request_id=get_request_id(request),
    )
    return JSONResponse(status_code=400, content=error.model_dump())


def _parse_content_length(header_value: str | None) -> int | None:
    if header_value is None:
        return None

    try:
        content_length = int(header_value)
    except ValueError:
        return None

    if content_length < 0:
        return None

    return content_length
