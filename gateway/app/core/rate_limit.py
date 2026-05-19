import hashlib
import math
import time
from collections.abc import AsyncIterator
from typing import Annotated, Protocol

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.request_id import get_request_id
from gateway.app.core.security import require_api_key
from gateway.app.schemas.openai import ChatCompletionRequest, ErrorDetail, ErrorResponse

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_RPM_KEY_PREFIX = "rate_limit:rpm"
RATE_LIMIT_TPM_KEY_PREFIX = "rate_limit:tpm"
RATE_LIMIT_CONCURRENT_KEY_PREFIX = "rate_limit:concurrent"
RATE_LIMIT_KEY_PREFIX = RATE_LIMIT_RPM_KEY_PREFIX
CHAT_MESSAGE_OVERHEAD_TOKENS = 4
CHAT_REQUEST_OVERHEAD_TOKENS = 2
TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
CONCURRENT_REQUEST_TTL_SECONDS = 3600

SettingsDependency = Annotated[Settings, Depends(get_settings)]
APIKeyDependency = Annotated[str, Depends(require_api_key)]


class RedisLike(Protocol):
    async def incr(self, name: str) -> int:
        ...

    async def incrby(self, name: str, amount: int) -> int:
        ...

    async def decr(self, name: str) -> int:
        ...

    async def expire(self, name: str, time: int) -> object:
        ...


class RateLimitExceeded(Exception):
    def __init__(self, *, kind: str = "requests") -> None:
        super().__init__(kind)
        self.kind = kind


class RateLimitLease:
    def __init__(
        self,
        limiter: "RateLimiter | None",
        api_key: str | None = None,
        acquired: bool = False,
    ) -> None:
        self.limiter = limiter
        self.api_key = api_key
        self.acquired = acquired
        self.released = False

    @classmethod
    def noop(cls) -> "RateLimitLease":
        return cls(limiter=None)

    async def release(self) -> None:
        if self.released:
            return

        self.released = True
        try:
            if self.acquired and self.limiter is not None and self.api_key is not None:
                await self.limiter.release_concurrent(api_key=self.api_key)
        finally:
            if self.limiter is not None:
                await self.limiter.aclose()

    async def wrap_stream(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        try:
            async for chunk in stream:
                yield chunk
        finally:
            await self.release()


class RateLimiter:
    def __init__(
        self,
        redis_client: RedisLike,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self.redis_client = redis_client
        self.window_seconds = window_seconds

    async def check_requests(self, api_key: str, limit: int) -> None:
        redis_key = self._redis_key(api_key, RATE_LIMIT_RPM_KEY_PREFIX)
        request_count = await self.redis_client.incr(redis_key)
        if request_count == 1:
            await self.redis_client.expire(redis_key, self.window_seconds)

        if request_count > limit:
            raise RateLimitExceeded(kind="requests")

    async def check_tokens(self, api_key: str, token_cost: int, limit: int) -> None:
        if token_cost > limit:
            raise RateLimitExceeded(kind="tokens")

        redis_key = self._redis_key(api_key, RATE_LIMIT_TPM_KEY_PREFIX)
        token_count = await self.redis_client.incrby(redis_key, token_cost)
        if token_count == token_cost:
            await self.redis_client.expire(redis_key, self.window_seconds)

        if token_count > limit:
            raise RateLimitExceeded(kind="tokens")

    async def check_chat_request(
        self,
        *,
        api_key: str,
        request_limit: int,
        token_limit: int,
        token_cost: int,
    ) -> None:
        await self.check_requests(api_key=api_key, limit=request_limit)
        await self.check_tokens(api_key=api_key, token_cost=token_cost, limit=token_limit)

    async def acquire_concurrent(self, api_key: str, limit: int) -> RateLimitLease:
        redis_key = self._stable_redis_key(api_key, RATE_LIMIT_CONCURRENT_KEY_PREFIX)
        request_count = await self.redis_client.incr(redis_key)
        await self.redis_client.expire(redis_key, CONCURRENT_REQUEST_TTL_SECONDS)

        if request_count > limit:
            await self.redis_client.decr(redis_key)
            raise RateLimitExceeded(kind="concurrency")

        return RateLimitLease(limiter=self, api_key=api_key, acquired=True)

    async def release_concurrent(self, api_key: str) -> None:
        redis_key = self._stable_redis_key(api_key, RATE_LIMIT_CONCURRENT_KEY_PREFIX)
        await self.redis_client.decr(redis_key)

    async def aclose(self) -> None:
        close = getattr(self.redis_client, "aclose", None)
        if close is not None:
            await close()

    def _redis_key(self, api_key: str, prefix: str) -> str:
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        bucket = int(time.time() // self.window_seconds)
        return f"{prefix}:{key_hash}:{bucket}"

    def _stable_redis_key(self, api_key: str, prefix: str) -> str:
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return f"{prefix}:{key_hash}"


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
        await limiter.check_requests(api_key=api_key, limit=settings.rate_limit_rpm)
    finally:
        await limiter.aclose()


async def enforce_chat_rate_limit(
    *,
    settings: Settings,
    api_key: str,
    request: ChatCompletionRequest,
) -> RateLimitLease:
    if not settings.rate_limit_enabled:
        return RateLimitLease.noop()

    token_cost = estimate_chat_token_cost(
        request,
        default_completion_tokens=settings.rate_limit_default_completion_tokens,
    )
    limiter = create_rate_limiter(settings)
    lease: RateLimitLease | None = None
    try:
        lease = await limiter.acquire_concurrent(
            api_key=api_key,
            limit=settings.rate_limit_concurrent_requests,
        )
        await limiter.check_chat_request(
            api_key=api_key,
            request_limit=settings.rate_limit_rpm,
            token_limit=settings.rate_limit_tpm,
            token_cost=token_cost,
        )
        return lease
    except Exception:
        if lease is not None:
            await lease.release()
        else:
            await limiter.aclose()
        raise


def estimate_chat_token_cost(
    request: ChatCompletionRequest,
    *,
    default_completion_tokens: int,
) -> int:
    prompt_tokens = CHAT_REQUEST_OVERHEAD_TOKENS
    for message in request.messages:
        prompt_tokens += CHAT_MESSAGE_OVERHEAD_TOKENS
        prompt_tokens += estimate_text_tokens(message.content)

    completion_budget = request.max_tokens or default_completion_tokens
    return prompt_tokens + completion_budget


def estimate_text_tokens(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0

    word_estimate = len(stripped.split())
    char_estimate = math.ceil(len(stripped) / TOKEN_ESTIMATE_CHARS_PER_TOKEN)
    return max(word_estimate, char_estimate, 1)


async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    if exc.kind == "tokens":
        message = "token rate limit exceeded"
        code = "token_rate_limit_exceeded"
    elif exc.kind == "concurrency":
        message = "concurrent request limit exceeded"
        code = "concurrent_request_limit_exceeded"
    else:
        message = "rate limit exceeded"
        code = "rate_limit_exceeded"

    error = ErrorResponse(
        error=ErrorDetail(
            message=message,
            type="rate_limit_error",
            code=code,
        ),
        request_id=get_request_id(request),
    )
    return JSONResponse(status_code=429, content=error.model_dump())
