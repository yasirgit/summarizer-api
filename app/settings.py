"""Application settings configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Summarizer API"
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # CORS
    allowed_hosts: list[str] = Field(
        default=["*"]
    )

    # Database
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/summarizer",
        env="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434", env="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="gemma3:1b", env="OLLAMA_MODEL")
    ollama_timeout_connect: float = Field(default=30.0, env="OLLAMA_TIMEOUT_CONNECT")
    ollama_timeout_read: float = Field(default=300.0, env="OLLAMA_TIMEOUT_READ")  # 5 minutes for LLM processing
    ollama_timeout_write: float = Field(default=30.0, env="OLLAMA_TIMEOUT_WRITE")
    ollama_timeout_pool: float = Field(default=30.0, env="OLLAMA_TIMEOUT_POOL")
    ollama_max_retries: int = Field(default=2, env="OLLAMA_MAX_RETRIES")

    # Security
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")

    # File upload
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        env="MAX_FILE_SIZE",
    )
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")

    # Metrics
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")

    class Config:
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
