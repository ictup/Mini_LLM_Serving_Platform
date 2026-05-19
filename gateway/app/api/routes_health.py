from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.error_codes import error_code_headers
from gateway.app.proxy.backend_client import BackendClient, BackendClientError

router = APIRouter(tags=["health"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    backend: str
    backend_type: str
    models: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready(settings: SettingsDependency) -> ReadyResponse | JSONResponse:
    client = BackendClient(settings)
    try:
        models_response = await client.list_models()
    except BackendClientError as exc:
        return JSONResponse(
            status_code=503,
            content=ReadyResponse(
                status="not_ready",
                backend=exc.code,
                backend_type=settings.backend_type,
                models="unavailable",
            ).model_dump(),
            headers=error_code_headers(exc.code),
        )

    model_count = count_models(models_response)
    if model_count == 0:
        return JSONResponse(
            status_code=503,
            content=ReadyResponse(
                status="not_ready",
                backend="ok",
                backend_type=settings.backend_type,
                models="empty",
            ).model_dump(),
            headers=error_code_headers("backend_model_list_empty"),
        )

    return ReadyResponse(
        status="ready",
        backend="ok",
        backend_type=settings.backend_type,
        models=str(model_count),
    )


def count_models(models_response: dict) -> int:
    models = models_response.get("data")
    if not isinstance(models, list):
        return 0
    return len(models)
