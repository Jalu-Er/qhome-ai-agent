from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings
from .json_utils import parse_json_object


class ChatModel(Protocol):
    def generate_json(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        payload: dict[str, Any],
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        ...


@dataclass
class SumoPodChatModel:
    settings: Settings
    temperature: float = 0.2

    def generate_json(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        payload: dict[str, Any],
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        if not self.settings.api_key:
            raise RuntimeError("AI_API_KEY is empty. Fill .env or use --mode mock.")

        body = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Return only valid JSON. Do not wrap it in markdown.\n\n"
                        + json.dumps(payload, ensure_ascii=False, indent=2)
                    ),
                },
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{agent_name} API error {exc.code}: {detail}") from exc

        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
        return parse_json_object(content)
