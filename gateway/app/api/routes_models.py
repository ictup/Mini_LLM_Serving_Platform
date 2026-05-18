from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request

from gateway.app.core.config import Settings, get_settings
from gateway.app.core.request_id import get_request_id
from gateway.app.core.security import require_api_key
from gateway.app.proxy.model_aliases import list_gateway_models
from gateway.app.schemas.openai import ModelListResponse

router = APIRouter(prefix="/v1", tags=["models"])
logger = structlog.get_logger("gateway.models")
SettingsDependency = Annotated[Settings, Depends(get_settings)]
APIKeyDependency = Annotated[str, Depends(require_api_key)]


@router.get("/models", response_model=None)
async def list_models(
    raw_request: Request,
    settings: SettingsDependency,
    _api_key: APIKeyDependency,
) -> ModelListResponse:
    request_id = get_request_id(raw_request)
    models = list_gateway_models(settings)
    logger.info(
        "models_list_request",
        request_id=request_id,
        backend_type=settings.backend_type,
        model_count=len(models.data),
    )
    return models
