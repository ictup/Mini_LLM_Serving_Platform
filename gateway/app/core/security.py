from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.responses import JSONResponse

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.error_codes import error_code_headers
from gateway.app.core.request_id import get_request_id
from gateway.app.schemas.openai import ErrorDetail, ErrorResponse

SettingsDependency = Annotated[Settings, Depends(get_settings)]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


class APIKeyAuthError(Exception):
    pass


async def require_api_key(
    settings: SettingsDependency,
    authorization: AuthorizationHeader = None,
) -> str:
    token = extract_bearer_token(authorization)
    if token is None or not is_allowed_api_key(token, settings.allowed_api_keys):
        raise APIKeyAuthError
    return token


def extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        return None

    return token.strip()


def is_allowed_api_key(candidate: str, allowed_keys: tuple[str, ...]) -> bool:
    return any(compare_digest(candidate, allowed_key) for allowed_key in allowed_keys)


async def api_key_auth_exception_handler(
    request: Request,
    _exc: APIKeyAuthError,
) -> JSONResponse:
    error = ErrorResponse(
        error=ErrorDetail(
            message="invalid api key",
            type="authentication_error",
            code="invalid_api_key",
        ),
        request_id=get_request_id(request),
    )
    return JSONResponse(
        status_code=401,
        content=error.model_dump(),
        headers=error_code_headers("invalid_api_key", {"WWW-Authenticate": "Bearer"}),
    )
