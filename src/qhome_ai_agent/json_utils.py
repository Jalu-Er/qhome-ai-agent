from __future__ import annotations

import json
from typing import Any


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        value = json.loads(text[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object from model response.")
    return value
