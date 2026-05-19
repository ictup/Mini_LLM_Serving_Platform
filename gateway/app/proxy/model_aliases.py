import hashlib
import json
from dataclasses import dataclass
from typing import Any

from gateway.app.core.config import Settings
from gateway.app.schemas.openai import ModelCard, ModelListResponse


class ModelAliasError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.model = model


@dataclass(frozen=True)
class ModelRouteTarget:
    model: str
    weight: int = 1


@dataclass(frozen=True)
class ModelRoute:
    alias: str
    targets: tuple[ModelRouteTarget, ...]
    strategy: str = "weighted"


@dataclass(frozen=True)
class ModelRouteSelection:
    client_model: str
    backend_model: str
    fallback_models: tuple[str, ...]
    strategy: str

    @property
    def backend_models(self) -> tuple[str, ...]:
        return (self.backend_model, *self.fallback_models)


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


def load_model_routes(settings: Settings) -> dict[str, ModelRoute]:
    payload = json.loads(settings.model_routes_json or "{}")
    if not isinstance(payload, dict):
        raise ValueError("MODEL_ROUTES_JSON must be a JSON object")

    routes: dict[str, ModelRoute] = {}
    for alias, route_config in payload.items():
        if not isinstance(alias, str) or not alias.strip():
            raise ValueError("MODEL_ROUTES_JSON aliases must be non-empty strings")
        routes[alias.strip()] = parse_model_route(alias.strip(), route_config)
    return routes


def parse_model_route(alias: str, route_config: Any) -> ModelRoute:
    if isinstance(route_config, str):
        return ModelRoute(
            alias=alias,
            targets=(ModelRouteTarget(model=normalize_model(route_config)),),
        )

    if isinstance(route_config, list):
        return ModelRoute(alias=alias, targets=parse_route_targets(route_config))

    if isinstance(route_config, dict):
        strategy = route_config.get("strategy", "weighted")
        targets = route_config.get("targets")
        if not isinstance(strategy, str) or strategy.strip() != "weighted":
            raise ValueError("MODEL_ROUTES_JSON currently supports only weighted strategy")
        if not isinstance(targets, list):
            raise ValueError("MODEL_ROUTES_JSON route targets must be a list")
        return ModelRoute(
            alias=alias,
            targets=parse_route_targets(targets),
            strategy=strategy.strip(),
        )

    raise ValueError("MODEL_ROUTES_JSON route values must be strings, lists, or objects")


def parse_route_targets(targets: list[Any]) -> tuple[ModelRouteTarget, ...]:
    parsed_targets: list[ModelRouteTarget] = []
    for target in targets:
        if isinstance(target, str):
            parsed_targets.append(ModelRouteTarget(model=normalize_model(target)))
            continue
        if isinstance(target, dict):
            model = normalize_model(target.get("model"))
            weight = target.get("weight", 1)
            if not isinstance(weight, int) or weight <= 0:
                raise ValueError("MODEL_ROUTES_JSON target weight must be a positive integer")
            parsed_targets.append(ModelRouteTarget(model=model, weight=weight))
            continue
        raise ValueError("MODEL_ROUTES_JSON targets must be strings or objects")

    if not parsed_targets:
        raise ValueError("MODEL_ROUTES_JSON route targets cannot be empty")
    return tuple(parsed_targets)


def normalize_model(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("model route targets must include non-empty model strings")
    return value.strip()


def resolve_model_alias(model: str, settings: Settings) -> str:
    return resolve_model_route(model, settings).backend_model


def resolve_model_route(
    model: str,
    settings: Settings,
    *,
    routing_key: str | None = None,
) -> ModelRouteSelection:
    routes = load_model_routes(settings)
    route = routes.get(model)
    if route is not None:
        return select_model_route(route, routing_key=routing_key or model)

    aliases = load_model_aliases(settings)
    try:
        backend_model = aliases[model]
    except KeyError as exc:
        raise ModelAliasError(model=model) from exc
    return ModelRouteSelection(
        client_model=model,
        backend_model=backend_model,
        fallback_models=(),
        strategy="alias",
    )


def select_model_route(route: ModelRoute, *, routing_key: str) -> ModelRouteSelection:
    selected_index = weighted_target_index(
        route.targets,
        routing_key=f"{route.alias}:{routing_key}",
    )
    selected_target = route.targets[selected_index]
    fallback_models = tuple(
        target.model for index, target in enumerate(route.targets) if index != selected_index
    )
    return ModelRouteSelection(
        client_model=route.alias,
        backend_model=selected_target.model,
        fallback_models=fallback_models,
        strategy=route.strategy,
    )


def weighted_target_index(targets: tuple[ModelRouteTarget, ...], *, routing_key: str) -> int:
    total_weight = sum(target.weight for target in targets)
    slot = stable_hash_int(routing_key) % total_weight
    running_weight = 0
    for index, target in enumerate(targets):
        running_weight += target.weight
        if slot < running_weight:
            return index
    return len(targets) - 1


def stable_hash_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


def list_gateway_models(settings: Settings) -> ModelListResponse:
    aliases = load_model_aliases(settings)
    routes = load_model_routes(settings)
    model_ids = sorted(set(aliases) | set(routes))
    return ModelListResponse(
        data=[ModelCard(id=model_id, owned_by="gateway") for model_id in model_ids]
    )
