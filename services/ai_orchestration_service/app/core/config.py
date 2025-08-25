# In services/ai_orchestration_service/app/core/config.py
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and LLM provider configuration."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
    )

    # Which LLM backend to use: "openai", "gemini", or "local"
    llm_provider: str

    # API keys or URLs for the various providers
    openai_api_key: str
    # Default OpenAI model to use
    openai_model: str
    gemini_api_key: str
    # Default endpoint for a locally hosted model.
    # `host.docker.internal` lets containers reach services on the host.
    # local_llm_url: str = "http://host.docker.internal:1234/v1/chat/completions"
    local_llm_url: str

    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    llm_timeout: float


settings = Settings()
