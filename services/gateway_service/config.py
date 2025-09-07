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

    # --- Logging / Tracing configuration ---
    # Standard log level: DEBUG, INFO, WARNING, ERROR, CRITICAL, or TRACE (custom)
    log_level: str = os.getenv("LOG_LEVEL", "DEBUG")

    # Enable function call tracing across service modules (very verbose)
    # You can enable this either by setting LOG_LEVEL=TRACE or TRACE_CALLS=true.
    trace_calls: bool = os.getenv("TRACE_CALLS", "").strip().lower() in {"1", "true", "yes", "y"}

    # Comma-separated list of module prefixes to trace, e.g. "api_service,orchestrator_service"
    # If empty, path-based filter will be used.
    trace_module_prefixes: str = os.getenv("TRACE_MODULE_PREFIXES", "")

    # Comma-separated substrings; any file path containing one of these will be traced.
    # Defaults to tracing code under the repo's services directory.
    trace_file_path_contains: str = os.getenv("TRACE_FILE_PATH_CONTAINS", "services/")

    # Concise output for trace logs (message only: CALL/RET and function)
    trace_concise: bool = os.getenv("TRACE_CONCISE", "").strip().lower() in {"1", "true", "yes", "y"}

    # Timeout (in seconds) for outgoing HTTP requests to LLM providers
    # Increase default read timeout to accommodate slower local models.
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "60"))
    # Separate, shorter connect timeout is usually fine.
    llm_connect_timeout: float = float(os.getenv("LLM_CONNECT_TIMEOUT", "10"))

    # Path to local SQLite DB for sample resumes/job descriptions
    samples_db_path: str = os.getenv("SAMPLES_DB_PATH", "data/samples.db")


settings = Settings()
