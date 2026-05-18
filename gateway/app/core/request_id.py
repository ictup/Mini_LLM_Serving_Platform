import re
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PREFIX = "req_"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def normalize_request_id(header_value: str | None) -> str:
    if header_value is None:
        return generate_request_id()

    request_id = header_value.strip()
    if not request_id or not REQUEST_ID_PATTERN.fullmatch(request_id):
        return generate_request_id()

    return request_id


def generate_request_id() -> str:
    return f"{REQUEST_ID_PREFIX}{uuid.uuid4().hex}"


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)
