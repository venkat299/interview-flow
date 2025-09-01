import os


class Settings:
    """Configuration for the interview session service."""
    # Base URL for the AI orchestration service
    # Use env var in containers; default is for local dev
    ai_service_url: str = os.getenv("AI_SERVICE_URL", "http://localhost:8003")
    # Timeout for outgoing HTTP requests (seconds)
    # Increased default to accommodate slower LLM responses
    ai_timeout: float = float(os.getenv("AI_TIMEOUT", "60.0"))


settings = Settings()
