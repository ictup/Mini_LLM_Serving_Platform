from fastapi import FastAPI

from gateway.app.api.routes_chat import router as chat_router
from gateway.app.api.routes_health import router as health_router
from gateway.app.api.routes_metrics import router as metrics_router
from gateway.app.api.routes_models import router as models_router
from gateway.app.core.config import get_settings
from gateway.app.core.logging import configure_logging, structured_logging_middleware
from gateway.app.core.rate_limit import RateLimitExceeded, rate_limit_exception_handler
from gateway.app.core.request_id import request_id_middleware
from gateway.app.core.request_limits import (
    ChatRequestLimitExceeded,
    chat_request_limit_exception_handler,
    request_body_size_middleware,
)
from gateway.app.core.security import APIKeyAuthError, api_key_auth_exception_handler
from gateway.app.observability.metrics import prometheus_metrics_middleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.middleware("http")(request_id_middleware)
    app.middleware("http")(request_body_size_middleware)
    app.middleware("http")(structured_logging_middleware)
    app.middleware("http")(prometheus_metrics_middleware)
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(models_router)
    app.include_router(metrics_router)
    app.add_exception_handler(APIKeyAuthError, api_key_auth_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(ChatRequestLimitExceeded, chat_request_limit_exception_handler)
    return app


app = create_app()
