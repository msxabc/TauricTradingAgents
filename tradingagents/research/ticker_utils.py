"""Ticker normalization and validation for research workflows."""

from __future__ import annotations

from tradingagents.dataflows.utils import safe_ticker_component


class TickerValidationError(ValueError):
    """Raised when a manual research ticker is invalid."""


def normalize_research_ticker(value: str) -> str:
    """Normalize symbol-only ticker input for research jobs.

    Rules:
    - trim whitespace
    - allow a leading '$' and strip it
    - uppercase the result
    - preserve exchange suffixes such as `.TO` or `.HK`
    - validate the final value using the repo's safe ticker path rules
    """
    if not isinstance(value, str):
        raise TickerValidationError("ticker must be a string")

    normalized = value.strip()
    if not normalized:
        raise TickerValidationError("ticker must be non-empty")

    if normalized.startswith("$"):
        normalized = normalized[1:]

    normalized = normalized.strip().upper()
    if not normalized:
        raise TickerValidationError("ticker must be non-empty")

    try:
        return safe_ticker_component(normalized)
    except ValueError as exc:
        raise TickerValidationError(str(exc)) from exc
