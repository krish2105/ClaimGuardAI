"""Central app configuration, loaded from environment variables / .env."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    anthropic_api_key: str = ""
    claude_model_reasoning: str = "claude-sonnet-4-5"
    claude_model_extraction: str = "claude-haiku-4-5"

    database_url: str = "postgresql+psycopg2://claimguard:claimguard@localhost:5432/claimguard"

    qdrant_url: str = ""
    qdrant_local_path: str = "./backend/data/qdrant_local"
    qdrant_collection: str = "claimguard_policies"

    fraud_model_path: str = "./backend/models/fraud_model.json"
    fraud_model_meta_path: str = "./backend/models/fraud_model_meta.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_mock_mode(self) -> bool:
        return not bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
