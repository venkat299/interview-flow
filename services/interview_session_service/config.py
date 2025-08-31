class Settings:
    """Configuration for the interview session service."""
    # Base URL for the AI orchestration service
    ai_service_url: str = "http://localhost:8003"
    # Timeout for outgoing HTTP requests
    ai_timeout: float = 10.0


settings = Settings()
