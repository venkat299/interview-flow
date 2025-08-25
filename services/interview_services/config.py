class Settings:
    """Simplified settings for LLM configuration."""
    # Which LLM backend to use: "openai" or "local"
    llm_provider: str = "local"
    # API keys or URLs for the various providers
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    gemini_api_key: str = ""
    local_llm_url: str = "https://248e110186a5.ngrok-free.app/v1/chat/completions"
    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    llm_timeout: float = 10.0


settings = Settings()
