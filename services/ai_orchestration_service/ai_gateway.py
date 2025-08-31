"""AI Gateway for routing tasks to LLM providers.

Adds support for selecting a local OpenAI-compatible LLM based on
ai_orchestration_service.config.Settings. If a task is not present in the
YAML router config, the gateway falls back to the provider specified in
settings (default: "local").
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import yaml

from .config import settings


class AIGateway:
    """Singleton gateway managing HTTP clients for LLM providers."""

    _instance: Optional["AIGateway"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        cfg_path = config_path or Path(__file__).with_name("llm_router_config.yml")
        try:
            with cfg_path.open("r", encoding="utf-8") as fh:
                self.config = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            self.config = {}
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def _provider_from_settings(self, provider_name: Optional[str]) -> Dict[str, Optional[str]]:
        """Return a provider config derived from settings for known providers.

        The shape matches entries under `providers` in llm_router_config.yml.
        """
        name = (provider_name or settings.llm_provider or "local").lower()
        if name == "openai":
            return {
                "base_url": "https://api.openai.com/v1/chat/completions",
                "api_key": settings.openai_api_key or None,
                "model": settings.openai_model,
            }
        # Default to local OpenAI-compatible endpoint
        return {
            "base_url": settings.local_llm_url,
            "api_key": None,  # set an env-specific token here if your server needs it
            "model": settings.local_model,
        }

    def _get_client(self, provider: str) -> httpx.AsyncClient:
        if provider not in self._clients:
            timeout = settings.llm_timeout
            self._clients[provider] = httpx.AsyncClient(timeout=timeout)
        return self._clients[provider]

    async def execute_task(self, task_name: str, system_prompt: str, user_prompt: Optional[str] = None) -> Any:
        """Execute a task by routing it to the configured LLM provider.

        Resolution order:
        - If settings.llm_provider is set, prefer that provider.
        - Else use the provider configured for the task in YAML.
        - If the task is missing in YAML, fall back to settings.llm_provider.
        """
        tasks = self.config.get("tasks", {})
        providers = self.config.get("providers", {})

        # Choose provider with settings taking precedence
        task_cfg = tasks.get(task_name)
        provider_name = (settings.llm_provider or (task_cfg or {}).get("provider") or "local").lower()

        # Merge provider config: YAML overrides filled by settings defaults
        yaml_provider_cfg = providers.get(provider_name) or {}
        default_provider_cfg = self._provider_from_settings(provider_name)
        provider_cfg: Dict[str, Optional[str]] = {**default_provider_cfg, **yaml_provider_cfg}

        # Resolve model: task->provider->settings default
        model = (task_cfg or {}).get("model") or provider_cfg.get("model") or default_provider_cfg.get("model")
        url = provider_cfg.get("base_url")
        api_key = provider_cfg.get("api_key")
        if not url or not model:
            raise ValueError(f"Provider '{provider_name}' missing required configuration (url/model)")

        messages = [{"role": "system", "content": system_prompt}]
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})

        payload: Dict[str, Any] = {"model": model, "messages": messages}
        headers: Dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        client = self._get_client(provider_name)
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


# Instantiate a default gateway for module-level use
gateway = AIGateway()
