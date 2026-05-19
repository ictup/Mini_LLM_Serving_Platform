import pytest

from gateway.app.core.config import Settings
from gateway.app.proxy.model_aliases import (
    ModelAliasError,
    load_model_routes,
    resolve_model_route,
)


def test_model_routes_support_string_shorthand() -> None:
    settings = Settings(model_routes_json='{"friendly":"backend-model"}')

    route = load_model_routes(settings)["friendly"]

    assert route.alias == "friendly"
    assert route.targets[0].model == "backend-model"
    assert route.targets[0].weight == 1


def test_weighted_route_selection_is_stable_for_same_key() -> None:
    settings = Settings(
        model_routes_json=(
            '{"canary":{"targets":['
            '{"model":"stable","weight":90},'
            '{"model":"candidate","weight":10}'
            "]}}"
        )
    )

    first = resolve_model_route("canary", settings, routing_key="request-123")
    second = resolve_model_route("canary", settings, routing_key="request-123")

    assert first.backend_model == second.backend_model
    assert set(first.backend_models) == {"stable", "candidate"}


def test_model_routes_take_precedence_over_legacy_aliases() -> None:
    settings = Settings(
        model_aliases_json='{"canary":"legacy"}',
        model_routes_json='{"canary":{"targets":[{"model":"routed","weight":1}]}}',
    )

    selection = resolve_model_route("canary", settings, routing_key="request-123")

    assert selection.backend_model == "routed"
    assert selection.strategy == "weighted"


def test_unknown_model_without_alias_or_route_raises() -> None:
    with pytest.raises(ModelAliasError):
        resolve_model_route("missing", Settings())


def test_weighted_target_index_rejects_empty_targets() -> None:
    with pytest.raises(ValueError):
        load_model_routes(Settings(model_routes_json='{"bad":{"targets":[]}}'))
