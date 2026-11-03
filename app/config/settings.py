from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    app_name: str = Field(default="WebIntelX AI", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    database_url: str = Field(default="sqlite:///./WebIntelXAI.db", alias="DATABASE_URL")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_secret_key: str = Field(default="change-this-in-development", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:8501",
            "http://localhost:8501",
        ],
        alias="CORS_ALLOWED_ORIGINS",
    )
    ingestion_max_batch_size: int = Field(default=50, alias="INGESTION_MAX_BATCH_SIZE")
    ingestion_rate_limit_per_minute: int = Field(default=60, alias="INGESTION_RATE_LIMIT_PER_MINUTE")
    ml_enabled: bool = Field(default=True, alias="ML_ENABLED")
    ml_min_training_events: int = Field(default=20, alias="ML_MIN_TRAINING_EVENTS")
    ml_n_estimators: int = Field(default=100, alias="ML_N_ESTIMATORS")
    ml_contamination: str = Field(default="auto", alias="ML_CONTAMINATION")
    ml_random_state: int = Field(default=42, alias="ML_RANDOM_STATE")
    ml_anomaly_threshold: float = Field(default=0.70, alias="ML_ANOMALY_THRESHOLD")
    ml_model_version: str = Field(default="v1", alias="ML_MODEL_VERSION")
    ml_feature_version: str = Field(default="v1", alias="ML_FEATURE_VERSION")
    ml_model_dir: str = Field(default="data/models", alias="ML_MODEL_DIR")
    llm_provider: str = Field(default="", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, alias="LLM_MAX_TOKENS")
    crewai_enabled: bool = Field(default=False, alias="CREWAI_ENABLED")
    investigation_max_events: int = Field(default=100, alias="INVESTIGATION_MAX_EVENTS")
    investigation_max_findings: int = Field(default=50, alias="INVESTIGATION_MAX_FINDINGS")
    investigation_max_correlations: int = Field(default=50, alias="INVESTIGATION_MAX_CORRELATIONS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
