class Settings:
    """Simplified settings for LLM configuration."""
    # Which LLM backend to use: "openai" or "local"
    llm_provider: str = "openai"
    # API keys or URLs for the various providers
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    gemini_api_key: str = ""
    local_llm_url: str = ""
    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    llm_timeout: float = 10.0


settings = Settings()
