"""AI Gateway for routing tasks to LLM providers."""
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
        with cfg_path.open("r", encoding="utf-8") as fh:
            self.config = yaml.safe_load(fh)
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def _get_client(self, provider: str) -> httpx.AsyncClient:
        if provider not in self._clients:
            timeout = settings.llm_timeout
            self._clients[provider] = httpx.AsyncClient(timeout=timeout)
        return self._clients[provider]

    async def execute_task(self, task_name: str, system_prompt: str, user_prompt: Optional[str] = None) -> Any:
        """Execute a task by routing it to the configured LLM provider."""
        tasks = self.config.get("tasks", {})
        providers = self.config.get("providers", {})
        task_cfg = tasks.get(task_name)
        if not task_cfg:
            raise ValueError(f"Task '{task_name}' not configured")
        provider_name = task_cfg.get("provider")
        provider_cfg = providers.get(provider_name)
        if not provider_cfg:
            raise ValueError(f"Provider '{provider_name}' not configured")

        model = task_cfg.get("model") or provider_cfg.get("model")
        url = provider_cfg.get("base_url")
        api_key = provider_cfg.get("api_key")

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

