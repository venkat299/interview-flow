import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH, override=True)


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
_LOCAL_BASE_URL_YAML: str = (_LOCAL_PROVIDER.get("base_url") or "") if isinstance(_LOCAL_PROVIDER, dict) else ""
_LOCAL_MODEL_YAML: str = (
    _LOCAL_PROVIDER.get("model") or "openai/gpt-oss-20b"
) if isinstance(_LOCAL_PROVIDER, dict) else "openai/gpt-oss-20b"
_AUTO_PROVIDER: Dict[str, Any] = _PROVIDERS.get("auto_answer", {}) if isinstance(_PROVIDERS, dict) else {}
_AUTO_BASE_URL_YAML: str = (
    _AUTO_PROVIDER.get("base_url") or ""
) if isinstance(_AUTO_PROVIDER, dict) else ""
_AUTO_MODEL_YAML: str = (
    _AUTO_PROVIDER.get("model") or _LOCAL_MODEL_YAML
) if isinstance(_AUTO_PROVIDER, dict) else _LOCAL_MODEL_YAML
_AUTO_API_KEY_YAML: str = (
    _AUTO_PROVIDER.get("api_key") or ""
) if isinstance(_AUTO_PROVIDER, dict) else ""
_GEMINI_PROVIDER: Dict[str, Any] = _PROVIDERS.get("gemini", {}) if isinstance(_PROVIDERS, dict) else {}
_GEMINI_MODEL_YAML: str = (
    _GEMINI_PROVIDER.get("model") or "gemini-2.5-flash"
) if isinstance(_GEMINI_PROVIDER, dict) else "gemini-2.5-flash"
_GEMINI_API_KEY_YAML: str = (
    _GEMINI_PROVIDER.get("api_key") or ""
) if isinstance(_GEMINI_PROVIDER, dict) else ""


class Settings:
    """Simplified settings for LLM configuration."""

    # Which LLM backend to use: "openai" or "local"
    llm_provider: str = os.getenv("LLM_PROVIDER", "local")

    # API keys or URLs for the various providers
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # gpt-3.5-turbo
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", _GEMINI_API_KEY_YAML)
    gemini_model: str = os.getenv("GEMINI_MODEL", _GEMINI_MODEL_YAML)

    # Model identifier for local OpenAI-compatible servers
    # Prefer llm_router_config.yml, allow env override
    local_model: str = os.getenv("LOCAL_LLM_MODEL", _LOCAL_MODEL_YAML)
    # Local OpenAI-compatible server URL; prefer llm_router_config.yml, allow env override
    local_llm_url: str = os.getenv("LOCAL_LLM_URL", _LOCAL_BASE_URL_YAML)
    # Dedicated provider configuration for the auto-answer generator
    auto_llm_url: str = os.getenv("AUTO_LLM_URL", _AUTO_BASE_URL_YAML or _LOCAL_BASE_URL_YAML)
    auto_llm_model: str = os.getenv("AUTO_LLM_MODEL", _AUTO_MODEL_YAML)
    auto_llm_api_key: str = os.getenv("AUTO_LLM_API_KEY", _AUTO_API_KEY_YAML)

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
