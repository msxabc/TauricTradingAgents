"""Deterministic serialization helpers for research workflow artifacts."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import BaseModel


def _serialize_exception(error: Exception) -> dict[str, str]:
    return {
        "type": error.__class__.__name__,
        "message": str(error),
    }


def _to_primitive(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _to_primitive(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Exception):
        return _serialize_exception(value)
    if isinstance(value, Mapping):
        return {str(key): _to_primitive(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_primitive(item) for item in value]
    return value


def model_to_primitive(value: Any) -> Any:
    """Convert nested models into JSON-safe primitives with stable mapping keys."""
    return _to_primitive(value)


def stable_json_dumps(value: Any, *, indent: int = 2) -> str:
    """Render a deterministic JSON string for archive artifacts and tests."""
    return json.dumps(
        model_to_primitive(value),
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
    )
