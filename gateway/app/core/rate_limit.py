import hashlib
import time
from typing import Annotated, Protocol

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.request_id import get_request_id
from gateway.app.core.security import require_api_key
from gateway.app.schemas.openai import ErrorDetail, ErrorResponse

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_KEY_PREFIX = "rate_limit:rpm"

SettingsDependency = Annotated[Settings, Depends(get_settings)]
APIKeyDependency = Annotated[str, Depends(require_api_key)]


class RedisLike(Protocol):
    async def incr(self, name: str) -> int:
        ...

    async def expire(self, name: str, time: int) -> object:
        ...


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(
        self,
        redis_client: RedisLike,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self.redis_client = redis_client
        self.window_seconds = window_seconds

    async def check(self, api_key: str, limit: int) -> None:
        redis_key = self._redis_key(api_key)
        request_count = await self.redis_client.incr(redis_key)
        if request_count == 1:
            await self.redis_client.expire(redis_key, self.window_seconds)

        if request_count > limit:
            raise RateLimitExceeded

    async def aclose(self) -> None:
        close = getattr(self.redis_client, "aclose", None)
        if close is not None:
            await close()

    def _redis_key(self, api_key: str) -> str:
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        bucket = int(time.time() // self.window_seconds)
        return f"{RATE_LIMIT_KEY_PREFIX}:{key_hash}:{bucket}"


def create_redis_client(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


def create_rate_limiter(settings: Settings) -> RateLimiter:
    return RateLimiter(redis_client=create_redis_client(settings))


async def enforce_rate_limit(
    settings: SettingsDependency,
    api_key: APIKeyDependency,
) -> None:
    if not settings.rate_limit_enabled:
        return

    limiter = create_rate_limiter(settings)
    try:
        await limiter.check(api_key=api_key, limit=settings.rate_limit_rpm)
    finally:
        await limiter.aclose()


async def rate_limit_exception_handler(
    request: Request,
    _exc: RateLimitExceeded,
) -> JSONResponse:
    error = ErrorResponse(
        error=ErrorDetail(
            message="rate limit exceeded",
            type="rate_limit_error",
            code="rate_limit_exceeded",
        ),
        request_id=get_request_id(request),
    )
    return JSONResponse(status_code=429, content=error.model_dump())
