from abc import ABC, abstractmethod
import json
from typing import Any

import httpx

from app.core.config import settings


class AIProvider(ABC):
    """Optional interpretation layer.

    Deterministic evidence checks never call this interface to decide identifier,
    legal-form, wilaya or other rule-based matches.
    """

    provider_id = "abstract"

    @abstractmethod
    async def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        raise NotImplementedError


class DisabledAIProvider(AIProvider):
    provider_id = "disabled"

    async def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        raise RuntimeError("AI_PROVIDER_DISABLED")


class OpenAICompatibleProvider(AIProvider):
    provider_id = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


class OllamaProvider(AIProvider):
    provider_id = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
        content = response.json()["message"]["content"]
        return json.loads(content)


def get_ai_provider() -> AIProvider:
    selected = settings.ai_provider.strip().lower()
    if selected in {"none", "disabled", "off"}:
        return DisabledAIProvider()
    if selected == "ollama":
        return OllamaProvider(settings.ai_base_url, settings.ai_model)
    if selected in {"openai", "openai_compatible"}:
        return OpenAICompatibleProvider(
            settings.ai_base_url,
            settings.ai_model,
            settings.ai_api_key,
        )
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")
