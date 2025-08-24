from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    openai_api_key: str = ""

settings = Settings()
