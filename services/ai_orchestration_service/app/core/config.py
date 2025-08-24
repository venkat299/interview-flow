from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and LLM provider configuration."""

    # Which LLM backend to use: "openai", "gemini", or "local"
    llm_provider: str = "openai"

    # API keys or URLs for the various providers
    openai_api_key: str = ""
    # Default OpenAI model to use
    openai_model: str = "gpt-3.5-turbo"
    gemini_api_key: str = ""
    local_llm_url: str = "http://localhost:11434/api/generate"

    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    llm_timeout: float = 10.0


settings = Settings()
