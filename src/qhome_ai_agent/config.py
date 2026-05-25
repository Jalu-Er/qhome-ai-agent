from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_settings(project_root: Path) -> Settings:
    load_env_file(project_root / ".env")
    return Settings(
        api_key=os.getenv("AI_API_KEY", ""),
        base_url=os.getenv("AI_BASE_URL", "https://ai.sumopod.com/v1").rstrip("/"),
        model=os.getenv("AI_MODEL", "gpt-4o-mini"),
    )
