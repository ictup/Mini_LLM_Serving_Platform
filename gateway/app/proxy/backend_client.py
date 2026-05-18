from collections.abc import AsyncIterator
from typing import Any

import httpx

from gateway.app.core.config import Settings
from gateway.app.schemas.openai import ChatCompletionRequest


class BackendClientError(Exception):
    def __init__(self, status_code: int, message: str, error_type: str, code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        self.code = code


class BackendStream:
    def __init__(
        self,
        client: httpx.AsyncClient,
        stream_context: Any,
        response: httpx.Response,
    ) -> None:
        self._client = client
        self._stream_context = stream_context
        self._response = response

    async def aiter_text(self) -> AsyncIterator[str]:
        try:
            async for chunk in self._response.aiter_text():
                if chunk:
                    yield chunk
        finally:
            await self._stream_context.__aexit__(None, None, None)
            await self._client.aclose()


class BackendClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def list_models(self) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self.settings.backend_timeout_seconds,
            ) as client:
                response = await client.get("/models")
        except httpx.TimeoutException as exc:
            raise BackendClientError(
                status_code=504,
                message="model backend timed out",
                error_type="timeout_error",
                code="backend_timeout",
            ) from exc
        except httpx.RequestError as exc:
            raise BackendClientError(
                status_code=502,
                message="model backend unavailable",
                error_type="backend_error",
                code="backend_unavailable",
            ) from exc

        if response.status_code >= 500:
            self._raise_backend_unavailable()

        if response.status_code >= 400:
            raise BackendClientError(
                status_code=response.status_code,
                message="model backend rejected the request",
                error_type="backend_error",
                code="backend_rejected_request",
            )

        return response.json()

    async def create_chat_completion(self, request: ChatCompletionRequest) -> dict:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = False

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self.settings.backend_timeout_seconds,
            ) as client:
                response = await client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise BackendClientError(
                status_code=504,
                message="model backend timed out",
                error_type="timeout_error",
                code="backend_timeout",
            ) from exc
        except httpx.RequestError as exc:
            raise BackendClientError(
                status_code=502,
                message="model backend unavailable",
                error_type="backend_error",
                code="backend_unavailable",
            ) from exc

        if response.status_code >= 500:
            self._raise_backend_unavailable()

        if response.status_code >= 400:
            raise BackendClientError(
                status_code=response.status_code,
                message="model backend rejected the request",
                error_type="backend_error",
                code="backend_rejected_request",
            )

        return response.json()

    async def open_chat_completion_stream(self, request: ChatCompletionRequest) -> BackendStream:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True

        client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=httpx.Timeout(
                self.settings.backend_timeout_seconds,
                read=self.settings.streaming_timeout_seconds,
            ),
        )
        stream_context = client.stream("POST", "/chat/completions", json=payload)

        try:
            response = await stream_context.__aenter__()
        except httpx.TimeoutException as exc:
            await client.aclose()
            raise BackendClientError(
                status_code=504,
                message="model backend timed out",
                error_type="timeout_error",
                code="backend_timeout",
            ) from exc
        except httpx.RequestError as exc:
            await client.aclose()
            raise BackendClientError(
                status_code=502,
                message="model backend unavailable",
                error_type="backend_error",
                code="backend_unavailable",
            ) from exc

        try:
            if response.status_code >= 500:
                self._raise_backend_unavailable()

            if response.status_code >= 400:
                raise BackendClientError(
                    status_code=response.status_code,
                    message="model backend rejected the request",
                    error_type="backend_error",
                    code="backend_rejected_request",
                )
        except BackendClientError:
            await stream_context.__aexit__(None, None, None)
            await client.aclose()
            raise

        return BackendStream(client=client, stream_context=stream_context, response=response)

    @property
    def _base_url(self) -> str:
        if self.settings.backend_type == "vllm":
            return self.settings.vllm_base_url
        return self.settings.mock_base_url

    @property
    def _headers(self) -> dict[str, str]:
        if self.settings.backend_type == "vllm" and self.settings.vllm_api_key:
            return {"Authorization": f"Bearer {self.settings.vllm_api_key}"}
        return {}

    def _raise_backend_unavailable(self) -> None:
        raise BackendClientError(
            status_code=502,
            message="model backend unavailable",
            error_type="backend_error",
            code="backend_unavailable",
        )
