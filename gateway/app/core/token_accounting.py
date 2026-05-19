import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from gateway.app.schemas.openai import ChatCompletionRequest

CHAT_MESSAGE_OVERHEAD_TOKENS = 4
CHAT_REQUEST_OVERHEAD_TOKENS = 2
TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
TOKENIZER_PROFILE_ESTIMATED = "estimated"
TOKENIZER_PROFILE_QWEN2 = "qwen2"

DEFAULT_TOKENIZER_PROFILES_JSON = json.dumps(
    {
        "mock": TOKENIZER_PROFILE_ESTIMATED,
        "qwen-small": TOKENIZER_PROFILE_QWEN2,
        "Qwen/Qwen2.5-0.5B-Instruct": TOKENIZER_PROFILE_QWEN2,
    },
    separators=(",", ":"),
)

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_TEXT_SEGMENT_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]|[A-Za-z]+|\d+|[^\w\s]",
    re.UNICODE,
)


def estimate_chat_token_cost(
    request: ChatCompletionRequest,
    *,
    default_completion_tokens: int,
    tokenizer_profiles_json: str = "{}",
    tokenizer_paths_json: str = "{}",
    backend_model: str | None = None,
) -> int:
    counter = ModelAwareTokenCounter(
        profiles=load_tokenizer_profiles(tokenizer_profiles_json),
        tokenizer_paths=load_tokenizer_paths(tokenizer_paths_json),
    )
    prompt_tokens = CHAT_REQUEST_OVERHEAD_TOKENS
    for message in request.messages:
        prompt_tokens += CHAT_MESSAGE_OVERHEAD_TOKENS
        prompt_tokens += counter.count_text(
            message.content,
            client_model=request.model,
            backend_model=backend_model,
        )

    completion_budget = request.max_tokens or default_completion_tokens
    return prompt_tokens + completion_budget


def estimate_text_tokens(text: str) -> int:
    return estimate_text_tokens_by_profile(text, TOKENIZER_PROFILE_ESTIMATED)


def estimate_text_tokens_by_profile(text: str, profile: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0

    if profile == TOKENIZER_PROFILE_QWEN2:
        return estimate_qwen2_text_tokens(stripped)

    word_estimate = len(stripped.split())
    char_estimate = math.ceil(len(stripped) / TOKEN_ESTIMATE_CHARS_PER_TOKEN)
    return max(word_estimate, char_estimate, 1)


def estimate_qwen2_text_tokens(text: str) -> int:
    token_count = 0
    for segment in _TEXT_SEGMENT_RE.findall(text):
        if _CJK_RE.fullmatch(segment):
            token_count += 1
        elif segment.isdigit():
            token_count += max(1, math.ceil(len(segment) / 3))
        elif segment.isascii() and segment.isalpha():
            token_count += max(1, math.ceil(len(segment) / 4))
        else:
            token_count += 1
    return max(token_count, 1)


def load_tokenizer_profiles(raw_json: str) -> dict[str, str]:
    payload = json.loads(raw_json or "{}")
    if not isinstance(payload, dict):
        raise ValueError("RATE_LIMIT_TOKENIZER_PROFILES_JSON must be a JSON object")

    profiles: dict[str, str] = {}
    for model, profile in payload.items():
        if not isinstance(model, str) or not isinstance(profile, str):
            raise ValueError("tokenizer profile keys and values must be strings")
        model = model.strip()
        profile = profile.strip().lower()
        if model and profile:
            profiles[model] = profile
    return profiles


def load_tokenizer_paths(raw_json: str) -> dict[str, Path]:
    payload = json.loads(raw_json or "{}")
    if not isinstance(payload, dict):
        raise ValueError("RATE_LIMIT_TOKENIZER_PATHS_JSON must be a JSON object")

    paths: dict[str, Path] = {}
    for model, path in payload.items():
        if not isinstance(model, str) or not isinstance(path, str):
            raise ValueError("tokenizer path keys and values must be strings")
        model = model.strip()
        path = path.strip()
        if model and path:
            paths[model] = Path(path)
    return paths


class ModelAwareTokenCounter:
    def __init__(
        self,
        *,
        profiles: dict[str, str],
        tokenizer_paths: dict[str, Path],
    ) -> None:
        self.profiles = profiles
        self.tokenizer_paths = tokenizer_paths

    def count_text(
        self,
        text: str,
        *,
        client_model: str,
        backend_model: str | None,
    ) -> int:
        exact_count = self.count_with_tokenizer_file(
            text,
            client_model=client_model,
            backend_model=backend_model,
        )
        if exact_count is not None:
            return exact_count

        profile = self.resolve_profile(client_model=client_model, backend_model=backend_model)
        return estimate_text_tokens_by_profile(text, profile)

    def count_with_tokenizer_file(
        self,
        text: str,
        *,
        client_model: str,
        backend_model: str | None,
    ) -> int | None:
        tokenizer_path = self.resolve_tokenizer_path(
            client_model=client_model,
            backend_model=backend_model,
        )
        if tokenizer_path is None:
            return None

        tokenizer = load_huggingface_tokenizer(tokenizer_path)
        if tokenizer is None:
            return None
        return len(tokenizer.encode(text).ids)

    def resolve_profile(self, *, client_model: str, backend_model: str | None) -> str:
        for model in candidate_models(client_model=client_model, backend_model=backend_model):
            profile = self.profiles.get(model)
            if profile is not None:
                return profile

        model_name = (backend_model or client_model).lower()
        if "qwen" in model_name:
            return TOKENIZER_PROFILE_QWEN2
        return TOKENIZER_PROFILE_ESTIMATED

    def resolve_tokenizer_path(
        self,
        *,
        client_model: str,
        backend_model: str | None,
    ) -> Path | None:
        for model in candidate_models(client_model=client_model, backend_model=backend_model):
            path = self.tokenizer_paths.get(model)
            if path is not None:
                return path
        return None


def candidate_models(*, client_model: str, backend_model: str | None) -> tuple[str, ...]:
    if backend_model is None or backend_model == client_model:
        return (client_model,)
    return (client_model, backend_model)


@lru_cache
def load_huggingface_tokenizer(path: Path) -> Any | None:
    try:
        from tokenizers import Tokenizer
    except ModuleNotFoundError:
        return None

    if not path.exists():
        return None
    return Tokenizer.from_file(str(path))
