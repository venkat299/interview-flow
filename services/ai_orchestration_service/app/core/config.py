# In services/ai_orchestration_service/app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and LLM provider configuration."""

    # Which LLM backend to use: "openai", "gemini", or "local"
    llm_provider: str = "local"

    # API keys or URLs for the various providers
    openai_api_key: str = ""
    # Default OpenAI model to use
    openai_model: str = "gpt-3.5-turbo"
    gemini_api_key: str = ""
    # Default endpoint for a locally hosted model.
    # `host.docker.internal` lets containers reach services on the host.
    # local_llm_url: str = "http://host.docker.internal:1234/v1/chat/completions"
    local_llm_url: str = "https://248e110186a5.ngrok-free.app/v1/chat/completions"

    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    llm_timeout: float = 10.0


settings = Settings()
