from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from gateway.app.core.token_accounting import DEFAULT_TOKENIZER_PROFILES_JSON


class Settings(BaseSettings):
    app_name: str = "mini-llm-serving-platform"
    env: str = "local"
    log_level: str = "INFO"
    api_keys: str = "dev-key,team-a-key"
    rate_limit_enabled: bool = False
    rate_limit_rpm: int = Field(default=60, gt=0)
    rate_limit_tpm: int = Field(default=60_000, gt=0)
    rate_limit_concurrent_requests: int = Field(default=20, gt=0)
    rate_limit_default_completion_tokens: int = Field(default=256, gt=0)
    rate_limit_tokenizer_profiles_json: str = DEFAULT_TOKENIZER_PROFILES_JSON
    rate_limit_tokenizer_paths_json: str = "{}"
    redis_url: str = "redis://localhost:6379/0"
    max_request_body_bytes: int = Field(default=1_048_576, gt=0)
    max_chat_messages: int = Field(default=64, gt=0)
    max_chat_message_chars: int = Field(default=16_000, gt=0)
    max_chat_total_message_chars: int = Field(default=64_000, gt=0)

    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8080

    backend_type: str = Field(default="mock", pattern="^(mock|vllm)$")
    mock_base_url: str = "http://localhost:9000/v1"
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_api_key: str = ""
    backend_timeout_seconds: float = 120
    streaming_timeout_seconds: float = 300

    default_model: str = "mock"
    model_aliases_json: str = '{"mock":"mock"}'
    model_routes_json: str = "{}"
    metrics_enabled: bool = True

    @property
    def allowed_api_keys(self) -> tuple[str, ...]:
        return tuple(key.strip() for key in self.api_keys.split(",") if key.strip())

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
