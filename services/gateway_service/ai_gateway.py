"""AI Gateway for routing tasks to LLM providers.

Adds support for selecting a local OpenAI-compatible LLM based on
gateway_service.config.Settings. If a task is not present in the
YAML router config, the gateway falls back to the provider specified in
settings (default: "local").
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json
import re

import httpx
import yaml
from json_repair import repair_json

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
            # Disable HTTP timeouts for LLM requests (per user request)
            self._clients[provider] = httpx.AsyncClient(timeout=None)
        return self._clients[provider]

    async def _ping_provider(self, provider_name: str, *, connect_timeout: float = 5.0, read_timeout: float = 15.0) -> None:
        """Send a minimal chat request to verify provider connectivity.

        Raises an exception on failure.
        """
        tasks = self.config.get("tasks", {})
        providers = self.config.get("providers", {})

        yaml_provider_cfg = providers.get(provider_name) or {}
        default_provider_cfg = self._provider_from_settings(provider_name)
        provider_cfg: Dict[str, Optional[str]] = {**default_provider_cfg, **yaml_provider_cfg}

        model = provider_cfg.get("model")
        url = provider_cfg.get("base_url")
        api_key = provider_cfg.get("api_key")
        if not url or not model:
            raise RuntimeError(f"Provider '{provider_name}' missing url/model configuration")

        headers: Dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": "healthcheck"},
                {"role": "user", "content": "ping"},
            ],
        }

        client = self._get_client(provider_name)
        timeout = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=read_timeout, pool=read_timeout)
        resp = await client.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        # Ensure JSON body is returned
        _ = resp.json()

    async def health_check_active_providers(self) -> None:
        """Check connectivity for providers used by tasks and default provider.

        Raises RuntimeError if any provider fails.
        """
        tasks = self.config.get("tasks", {})
        # Providers explicitly referenced by tasks (fallback to default provider if missing)
        provs = { (settings.llm_provider or "local").lower() }
        for tconf in (tasks.values() if isinstance(tasks, dict) else []):
            if isinstance(tconf, dict):
                name = (tconf.get("provider") or settings.llm_provider or "local").lower()
                provs.add(name)

        errors: list[str] = []
        for name in provs:
            try:
                await self._ping_provider(name)
            except Exception as e:
                errors.append(f"{name}: {e}")

        if errors:
            raise RuntimeError("LLM connectivity check failed for: " + ", ".join(errors))

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
        # Optional generation controls from YAML: task overrides provider
        # Common OpenAI-compatible params: max_tokens, temperature, top_p, n, stop
        for key in ("max_tokens", "temperature", "top_p", "n", "stop", "response_format"):
            if isinstance((task_cfg or {}).get(key), (int, float, str, list, dict)):
                payload[key] = (task_cfg or {}).get(key)
            elif isinstance((provider_cfg or {}).get(key), (int, float, str, list, dict)) and key not in payload:
                payload[key] = (provider_cfg or {}).get(key)
        headers: Dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        client = self._get_client(provider_name)
        # No per-request timeout for LLM calls (disabled by request)
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        raw = response.json()

        # Try to normalize OpenAI-style chat completion output into the
        # JSON object requested by callers. If we cannot parse a JSON object
        # from the assistant's content, provide a best-effort fallback for
        # question generation; otherwise, raise a helpful error.
        # Extract assistant content from typical providers
        content: Optional[str] = None
        if isinstance(raw, dict) and "choices" in raw:
            first = (raw.get("choices") or [{}])[0]
            msg = first.get("message") if isinstance(first, dict) else None
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                content = msg["content"]
            elif isinstance(first.get("text"), str):
                # Some providers use `text` instead of nested message
                content = first["text"]

        # If content is not found, return raw so callers can handle
        if not isinstance(content, str):
            return raw

        # Attempt to parse a JSON object from the content
        # Try to parse JSON content with some light cleaning
        parsed = self._parse_json_like(content)
        if isinstance(parsed, dict):
            # Task-specific normalization into our schemas
            if task_name == "blueprint_generation":
                return self._normalize_blueprint(parsed)
            if task_name == "answer_evaluation":
                return self._normalize_evaluation(parsed)
            return parsed

        # Best-effort fallback for simple question tasks
        if task_name == "question_generation":
            return {"question_text": self._clean_text(content).strip()}

        # Graceful fallbacks for structured tasks when providers emit non-JSON text
        if task_name == "blueprint_generation":
            # Attempt another parse after aggressive cleanup
            salvage = self._parse_json_like(self._clean_text(content))
            if isinstance(salvage, dict):
                return self._normalize_blueprint(salvage)
            # Minimal valid blueprint so the UI can proceed
            return self._normalize_blueprint({})
        if task_name == "answer_evaluation":
            # Conservative default evaluation
            return {
                "score": 0.0,
                "assessed_depth": "Intermediate",
                "llm_confidence": "Low",
                "justification": "Model returned non-JSON output.",
                "is_truthful": True,
            }

        # If we reached here, we couldn't produce the expected object
        raise ValueError(
            "LLM output was not valid JSON for task '"
            + task_name
            + "': "
            + content[:500]
        )

    @staticmethod
    def _parse_json_like(text: str) -> Any:
        """Parse a JSON object from LLM text output.

        Tries direct JSON first, then fenced code blocks, then the first
        object-like substring between braces.
        """
        text = AIGateway._clean_text(text.strip())
        # 1) direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2) fenced code block ```json ... ``` or ``` ... ```
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fence:
            inner = fence.group(1).strip()
            try:
                return json.loads(inner)
            except Exception:
                pass

        # 3) best-effort: find the first {...} block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # 4) attempt to repair malformed JSON
        try:
            repaired = repair_json(text)
            return json.loads(repaired)
        except Exception:
            pass

        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Strip common provider wrappers and artifacts around JSON.

        - Remove tokens like <|channel|>final, <|constrain|>JSON, <|message|>
        - Trim leading/trailing code block markers and stray labels
        """
        # Remove <|...|> tokens that some providers emit
        text = re.sub(r"<\|[^|>]+\|>", " ", text)
        # Remove labels like 'final', 'JSON', 'message' at the start if present
        text = re.sub(r"^(?:\s*(?:final|json|message|output|result)\s*[:\-]?\s*)+", "", text, flags=re.IGNORECASE)
        # Normalize smart quotes
        text = text.replace("“", "\"").replace("”", "\"")
        return text.strip()

    @staticmethod
    def _normalize_blueprint(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM blueprint output to InterviewBlueprintResponse shape.

        - Root keys: interview_title, experience_level, topics
        - Topic item keys: name, relevance_to_role, required_depth, jd_context, resume_evidence
        """
        def pick(*keys: str, default: Optional[Any] = None) -> Optional[Any]:
            for k in keys:
                if k in data and data[k] not in (None, ""):
                    return data[k]
            return default

        title = pick(
            "interview_title",
            "title",
            "interviewTitle",
            "interview_name",
        )
        level = pick(
            "experience_level",
            "level",
            "seniority",
            "candidate_level",
        )

        topics_src = pick("topics", "topics_list", "topic_list", default=[]) or []
        if isinstance(topics_src, dict):
            # Occasionally returned as an object keyed by topic
            topics_iter = [v for v in topics_src.values()]
        elif isinstance(topics_src, list):
            topics_iter = topics_src
        else:
            topics_iter = []

        def to_list(val: Any) -> list[str]:
            if val is None:
                return []
            if isinstance(val, list):
                return [str(x) for x in val]
            return [str(val)]

        def parse_relevance(val: Any) -> int:
            # Accept int, str like "8", "8/10", or words like High/Medium/Low -> 8/5/2
            if isinstance(val, (int, float)):
                try:
                    iv = int(round(float(val)))
                    return max(0, min(10, iv))
                except Exception:
                    return 0
            if isinstance(val, str):
                s = val.strip().lower()
                if s.endswith("/10"):
                    try:
                        return max(0, min(10, int(s.split("/", 1)[0])))
                    except Exception:
                        return 0
                mapping = {"low": 3, "medium": 5, "med": 5, "high": 8, "critical": 10, "essential": 9}
                if s in mapping:
                    return mapping[s]
                try:
                    return max(0, min(10, int(float(s))))
                except Exception:
                    return 0
            return 0

        def norm_depth(val: Any) -> str:
            s = str(val or "").strip().lower()
            if s in ("fundamental", "beginner", "basic", "foundational"):
                return "Fundamental"
            if s in ("intermediate", "mid", "medium"):
                return "Intermediate"
            if s in ("advanced", "strong"):
                return "Advanced"
            if s in ("expert", "senior", "deep"):
                return "Expert"
            # Default to Intermediate if unclear
            return "Intermediate"

        normalized_topics: list[Dict[str, Any]] = []
        for t in topics_iter:
            if not isinstance(t, dict):
                continue
            name = None
            for k in ("name", "topic_name", "topic", "title"):
                if k in t and t[k]:
                    name = str(t[k])
                    break
            rel_val = None
            for k in ("relevance_to_role", "relevance", "relevance_score", "importance"):
                if k in t and t[k] not in (None, ""):
                    rel_val = t[k]
                    break
            depth_val = None
            for k in ("required_depth", "depth", "target_depth", "expected_depth"):
                if k in t and t[k] not in (None, ""):
                    depth_val = t[k]
                    break
            jd = None
            for k in ("jd_context", "job_description_context", "jd_quotes", "jd_evidence"):
                if k in t and t[k] not in (None, ""):
                    jd = t[k]
                    break
            rez = None
            for k in ("resume_evidence", "resume_context", "resume_quotes", "cv_evidence"):
                if k in t and t[k] not in (None, ""):
                    rez = t[k]
                    break

            if not name:
                # Skip invalid entries lacking a name-like field
                continue

            normalized_topics.append(
                {
                    "name": name,
                    "relevance_to_role": parse_relevance(rel_val),
                    "required_depth": norm_depth(depth_val),
                    "jd_context": to_list(jd),
                    "resume_evidence": to_list(rez),
                }
            )

        result = {
            "interview_title": str(title or "Interview"),
            "experience_level": str(level or "Unknown"),
            "topics": normalized_topics,
        }
        return result

    @staticmethod
    def _normalize_evaluation(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM evaluation output to EvaluationResponse shape."""
        def pick(d: Dict[str, Any], *keys: str, default: Optional[Any] = None) -> Optional[Any]:
            for k in keys:
                if k in d and d[k] not in (None, ""):
                    return d[k]
            return default

        score = pick(data, "score", "rating", "grade", default=0)
        try:
            score = float(score)
        except Exception:
            score = 0.0

        depth = pick(data, "assessed_depth", "depth", "level", default="Intermediate")
        conf = pick(data, "llm_confidence", "confidence", "model_confidence", default="Medium")
        just = pick(data, "justification", "rationale", "explanation", default="")
        truthful = pick(data, "is_truthful", "truthful", "truthfulness", default=True)
        truthful = bool(truthful) if isinstance(truthful, bool) else str(truthful).strip().lower() in ("true", "yes", "y", "1")

        return {
            "score": score,
            "assessed_depth": str(depth),
            "llm_confidence": str(conf),
            "justification": str(just),
            "is_truthful": truthful,
        }


# Instantiate a default gateway for module-level use
gateway = AIGateway()
