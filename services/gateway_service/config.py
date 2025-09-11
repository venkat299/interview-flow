from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _load_router_config() -> Dict[str, Any]:
    """Load llm_router_config.yml next to this module.

    Returns an empty dict if the file is missing or invalid.
    """
    try:
        cfg_path = Path(__file__).with_name("llm_router_config.yml")
        with cfg_path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


_ROUTER_CFG: Dict[str, Any] = _load_router_config()
_PROVIDERS: Dict[str, Any] = _ROUTER_CFG.get("providers", {}) if isinstance(_ROUTER_CFG, dict) else {}
_LOCAL_PROVIDER: Dict[str, Any] = _PROVIDERS.get("local", {}) if isinstance(_PROVIDERS, dict) else {}
_LOCAL_BASE_URL_YAML: str = (
    (_LOCAL_PROVIDER.get("base_url") or "") if isinstance(_LOCAL_PROVIDER, dict) else ""
)
_LOCAL_MODEL_YAML: str = (
    (_LOCAL_PROVIDER.get("model") or "openai/gpt-oss-20b")
    if isinstance(_LOCAL_PROVIDER, dict)
    else "openai/gpt-oss-20b"
)


class Settings(BaseSettings):
    """Settings powered by Pydantic for type-safe env access."""

    llm_provider: str = Field(default="local", alias="LLM_PROVIDER")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", alias="OPENAI_MODEL")

    local_model: str = Field(default=_LOCAL_MODEL_YAML, alias="LOCAL_LLM_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    local_llm_url: str = Field(default=_LOCAL_BASE_URL_YAML, alias="LOCAL_LLM_URL")

    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")
    trace_calls: bool = Field(default=False, alias="TRACE_CALLS")
    trace_module_prefixes: str = Field(default="", alias="TRACE_MODULE_PREFIXES")
    trace_file_path_contains: str = Field(default="services/", alias="TRACE_FILE_PATH_CONTAINS")
    trace_concise: bool = Field(default=False, alias="TRACE_CONCISE")

    llm_timeout: float = Field(default=60.0, alias="LLM_TIMEOUT")
    llm_connect_timeout: float = Field(default=10.0, alias="LLM_CONNECT_TIMEOUT")

    samples_db_path: str = Field(default="data/samples.db", alias="SAMPLES_DB_PATH")


settings = Settings()
