import os


class Settings:
    """Simplified settings for LLM configuration."""

    # Which LLM backend to use: "openai" or "local"
    llm_provider: str = os.getenv("LLM_PROVIDER", "local")

    # API keys or URLs for the various providers
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # gpt-3.5-turbo
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    # Model identifier for local OpenAI-compatible servers
    local_model: str = os.getenv("LOCAL_LLM_MODEL", "openai/gpt-oss-20b")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    local_llm_url: str = os.getenv(
        "LOCAL_LLM_URL", "https://8cb5852bd7fb.ngrok-free.app/v1/chat/completions"
    )

    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    # Increase default read timeout to accommodate slower local models.
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "60"))
    # Separate, shorter connect timeout is usually fine.
    llm_connect_timeout: float = float(os.getenv("LLM_CONNECT_TIMEOUT", "10"))

    # Path to local SQLite DB for sample resumes/job descriptions
    samples_db_path: str = os.getenv("SAMPLES_DB_PATH", "data/samples.db")


settings = Settings()
