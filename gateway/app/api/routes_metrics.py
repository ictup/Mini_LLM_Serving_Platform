from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from gateway.app.core.config import Settings, get_settings
from gateway.app.observability.metrics import render_metrics

router = APIRouter(tags=["metrics"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/metrics", response_class=Response)
async def metrics(settings: SettingsDependency) -> Response:
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return render_metrics()
