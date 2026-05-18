import json

from gateway.app.core.config import Settings
from gateway.app.schemas.openai import ModelCard, ModelListResponse


class ModelAliasError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.model = model


def load_model_aliases(settings: Settings) -> dict[str, str]:
    aliases = json.loads(settings.model_aliases_json)
    if not isinstance(aliases, dict):
        raise ValueError("MODEL_ALIASES_JSON must be a JSON object")

    normalized_aliases: dict[str, str] = {}
    for alias, backend_model in aliases.items():
        if not isinstance(alias, str) or not isinstance(backend_model, str):
            raise ValueError("MODEL_ALIASES_JSON keys and values must be strings")
        if not alias.strip() or not backend_model.strip():
            raise ValueError("MODEL_ALIASES_JSON keys and values cannot be empty")
        normalized_aliases[alias.strip()] = backend_model.strip()

    if not normalized_aliases:
        normalized_aliases[settings.default_model] = settings.default_model

    return normalized_aliases


def resolve_model_alias(model: str, settings: Settings) -> str:
    aliases = load_model_aliases(settings)
    try:
        return aliases[model]
    except KeyError as exc:
        raise ModelAliasError(model=model) from exc


def list_gateway_models(settings: Settings) -> ModelListResponse:
    aliases = load_model_aliases(settings)
    return ModelListResponse(
        data=[ModelCard(id=alias, owned_by="gateway") for alias in sorted(aliases)]
    )
