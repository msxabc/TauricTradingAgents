"""Config loader for signal-driven research workflow jobs."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from string import Template
from typing import Any, Dict, Mapping, MutableMapping, Optional

from tradingagents.default_config import DEFAULT_CONFIG


SHARED_JOB_DEFAULTS = {
    "archive": {
        "base_path": "research_archive",
        "overwrite_existing_run": False,
    },
    "social_scanner": {
        "enabled": True,
        "base_url": "${SOCIAL_SCANNER_BASE_URL}",
        "api_key": "${SOCIAL_SCANNER_API_KEY}",
        "timeout_seconds": 15,
        "max_retries": 2,
        "retry_backoff_seconds": 1,
        "api_version": "v1",
        "endpoints": {
            "health": "/health",
            "status": "/internal/phase1/status",
            "signals": "/v1/signals",
            "focus_lists": "/v1/focus-lists",
            "ticker_detail": "/v1/tickers/{ticker}",
            "posts": "/v1/posts",
        },
        "default_query_params": {},
    },
    "research": {
        "output_format": {
            "markdown": True,
            "json": True,
        }
    },
    "mock_mode": {
        "enabled": False,
        "raw_signals_fixture": "tests/fixtures/social_scanner_signals.json",
    },
}


JOB_DEFAULTS = {
    "daily_signal_research_book": {
        "enabled": True,
        "run": {
            "timezone": "America/New_York",
            "scanner_window": "24h",
            "max_reports": 5,
            "min_candidate_score": 70,
            "research_depth": "standard",
            "max_raw_signals": 1000,
            "universe": "default",
            "universe_mode": "default",
        },
        "ranking": {
            "weights": {
                "attention_anomaly": 0.25,
                "narrative_velocity": 0.20,
                "sentiment_delta": 0.15,
                "source_credibility": 0.10,
                "source_diversity": 0.05,
                "market_confirmation": 0.10,
                "tradability": 0.10,
                "novelty": 0.05,
            },
            "penalties": {
                "spam_risk_weight": 0.20,
                "stale_signal_weight": 0.15,
                "low_liquidity_weight": 0.10,
            },
        },
    },
    "manual_research_report": {
        "enabled": True,
        "run": {
            "timezone": "America/New_York",
            "scanner_window": "24h",
            "research_depth": "standard",
            "allow_best_effort_resolution": False,
        },
    },
}


JOB_ALIASES = {
    "daily_top5_social_research": "daily_signal_research_book",
}


def canonical_job_name(job_name: str) -> str:
    return JOB_ALIASES.get(job_name, job_name)


def load_workflow_config(
    job_name: str,
    *,
    config_path: Optional[str] = None,
    cli_overrides: Optional[Mapping[str, Any]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    canonical_name = canonical_job_name(job_name)
    if canonical_name not in JOB_DEFAULTS:
        raise ValueError("Unsupported workflow job '%s'." % job_name)

    env_map = dict(os.environ if environ is None else environ)
    base_config = copy.deepcopy(DEFAULT_CONFIG)
    result = copy.deepcopy(base_config)
    result["job_name"] = canonical_name
    result["job"] = _deep_merge(copy.deepcopy(SHARED_JOB_DEFAULTS), copy.deepcopy(JOB_DEFAULTS[canonical_name]))

    overlay = {}
    if config_path:
        overlay = _load_config_file(Path(config_path), env_map)

    _apply_overlay(result, overlay, canonical_name)
    if cli_overrides:
        _apply_overlay(result, dict(cli_overrides), canonical_name)

    return _expand_env_placeholders(result, env_map)


def _load_config_file(path: Path, env_map: Mapping[str, str]) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix == ".json":
        return json.loads(text)
    if suffix in (".yml", ".yaml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PyYAML is required to load YAML workflow config files.") from exc
        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Workflow config file must contain a top-level object.")
        return _expand_env_placeholders(loaded, env_map)
    raise ValueError("Unsupported config file format '%s'." % suffix)


def _apply_overlay(result: MutableMapping[str, Any], overlay: Mapping[str, Any], canonical_name: str) -> None:
    overlay_copy = copy.deepcopy(dict(overlay))

    namespaced_job_overlay = overlay_copy.pop(canonical_name, None)
    if namespaced_job_overlay:
        _deep_merge(result["job"], namespaced_job_overlay)

    if "job" in overlay_copy and isinstance(overlay_copy["job"], Mapping):
        _deep_merge(result["job"], overlay_copy.pop("job"))

    top_level_job_overlay = {}
    for key in list(overlay_copy.keys()):
        if key in result["job"]:
            top_level_job_overlay[key] = overlay_copy.pop(key)
    if top_level_job_overlay:
        _deep_merge(result["job"], top_level_job_overlay)

    _deep_merge(result, overlay_copy)


def _deep_merge(base: MutableMapping[str, Any], overlay: Mapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in overlay.items():
        if (
            key in base
            and isinstance(base[key], MutableMapping)
            and isinstance(value, Mapping)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _expand_env_placeholders(value: Any, env_map: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return Template(value).safe_substitute(env_map)
    if isinstance(value, list):
        return [_expand_env_placeholders(item, env_map) for item in value]
    if isinstance(value, dict):
        return {
            key: _expand_env_placeholders(inner_value, env_map)
            for key, inner_value in value.items()
        }
    return value
