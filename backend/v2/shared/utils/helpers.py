from __future__ import annotations

import json
from typing import Any
from uuid import uuid4


def generate_id() -> str:
    return str(uuid4())


def sanitize_string(value: str) -> str:
    return value.strip()[:5000]


def safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, default=str)


def safe_json_loads(text: str) -> Any:
    return json.loads(text)
