"""Social Scanner client abstraction, mock client, and HTTP client."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol

import requests

from tradingagents.research.models import NormalizedSocialSignal


DEFAULT_ENDPOINTS = {
    "health": "/health",
    "status": "/internal/phase1/status",
    "signals": "/v1/signals",
    "focus_lists": "/v1/focus-lists",
    "ticker_detail": "/v1/tickers/{ticker}",
    "posts": "/v1/posts",
}


class SocialScannerClientError(RuntimeError):
    """Raised when the scanner response shape or request fails."""


class SocialScannerClient(Protocol):
    def fetch_signals(self, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        ...

    def fetch_ticker_detail(self, ticker: str) -> Dict[str, Any]:
        ...

    def fetch_health(self) -> Dict[str, Any]:
        ...

    def fetch_status(self) -> Dict[str, Any]:
        ...


class BaseSocialScannerClient:
    def fetch_signals(self, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        payload = self._get_json(self._render_endpoint("signals"), params=dict(params or {}))
        return self._normalize_signal_list_response(payload, request_echo=dict(params or {}))

    def fetch_ticker_detail(self, ticker: str) -> Dict[str, Any]:
        payload = self._get_json(self._render_endpoint("ticker_detail", ticker=ticker))
        return self._normalize_detail_response(payload)

    def fetch_health(self) -> Dict[str, Any]:
        payload = self._get_json(self._render_endpoint("health"))
        if not isinstance(payload, dict):
            raise SocialScannerClientError("Health response must be a JSON object.")
        return payload

    def fetch_status(self) -> Dict[str, Any]:
        payload = self._get_json(self._render_endpoint("status"))
        if not isinstance(payload, dict):
            raise SocialScannerClientError("Status response must be a JSON object.")
        return payload

    def _render_endpoint(self, endpoint_name: str, **params: Any) -> str:
        endpoint_template = self.endpoints.get(endpoint_name)
        if not endpoint_template:
            raise SocialScannerClientError("Missing scanner endpoint configuration for '%s'." % endpoint_name)
        return endpoint_template.format(**params)

    def _normalize_detail_response(self, payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise SocialScannerClientError("Detail response must be a JSON object.")
        if "error" in payload:
            raise SocialScannerClientError(self._format_error(payload["error"]))
        return payload

    def _normalize_signal_list_response(
        self,
        payload: Any,
        *,
        request_echo: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if isinstance(payload, list):
            rows = payload
            envelope = {
                "data": rows,
                "next_cursor": None,
                "request_echo": request_echo or {},
                "schema_version": None,
                "score_model_version": None,
                "generated_at": None,
            }
        elif isinstance(payload, dict):
            if "error" in payload:
                raise SocialScannerClientError(self._format_error(payload["error"]))
            if "data" not in payload or not isinstance(payload["data"], list):
                raise SocialScannerClientError("Signal list response missing list-valued 'data'.")
            envelope = {
                "data": payload["data"],
                "next_cursor": payload.get("next_cursor"),
                "request_echo": payload.get("request_echo", request_echo or {}),
                "schema_version": payload.get("schema_version"),
                "score_model_version": payload.get("score_model_version"),
                "generated_at": payload.get("generated_at"),
            }
        else:
            raise SocialScannerClientError("Signal list response must be a JSON array or object envelope.")

        normalized = [
            self._normalize_signal_row(row, generated_at=envelope.get("generated_at"))
            for row in envelope["data"]
        ]
        envelope["normalized_signals"] = normalized
        return envelope

    def _normalize_signal_row(
        self,
        row: Mapping[str, Any],
        *,
        generated_at: Optional[str] = None,
    ) -> NormalizedSocialSignal:
        if not isinstance(row, Mapping):
            raise SocialScannerClientError("Signal row must be a JSON object.")

        score_snapshot = self._as_dict(row.get("score_snapshot"))
        price_snapshot = self._as_dict(row.get("price_snapshot"))
        catalyst_summary = self._as_dict(row.get("catalyst_summary"))
        platform_breakdown = row.get("platform_breakdown") if isinstance(row.get("platform_breakdown"), list) else []

        signal_id = str(
            row.get("signal_id")
            or row.get("id")
            or row.get("ticker")
            or row.get("symbol")
            or ""
        ).strip()
        if not signal_id:
            raise SocialScannerClientError("Signal row missing stable identifier/ticker.")

        ticker = str(row.get("ticker") or row.get("symbol") or "").replace("$", "").upper().strip()
        if not ticker:
            raise SocialScannerClientError("Signal row missing ticker.")

        return NormalizedSocialSignal(
            signal_id=signal_id,
            ticker=ticker,
            company_name=self._opt_str(row.get("company_name")),
            signal_type=self._opt_str(row.get("primary_category")),
            dominant_narrative=self._opt_str(
                row.get("dominant_theme")
                or catalyst_summary.get("summary")
                or catalyst_summary.get("headline")
            ),
            source=self._infer_source(platform_breakdown),
            sentiment=self._infer_sentiment(score_snapshot),
            evidence_tier=self._bucket_credibility(score_snapshot.get("credibility_score")),
            materiality_score=self._as_float(score_snapshot.get("signal_score")),
            attention_anomaly=self._as_float(score_snapshot.get("attention_score")),
            narrative_velocity=self._as_float(score_snapshot.get("social_acceleration_score")),
            sentiment_delta=self._as_float(score_snapshot.get("sentiment_balance")),
            source_credibility=self._as_float(score_snapshot.get("credibility_score")),
            source_diversity=self._count_platforms(platform_breakdown),
            market_confirmation=self._as_float(score_snapshot.get("price_confirmation_score")),
            tradability=self._as_float(price_snapshot.get("relative_volume")),
            novelty=self._as_float(score_snapshot.get("lead_lag_edge_score")),
            spam_risk=self._as_float(score_snapshot.get("spam_burden")),
            stale_signal=False,
            low_liquidity=self._infer_low_liquidity(price_snapshot.get("relative_volume")),
            catalyst_clock=self._opt_str(
                catalyst_summary.get("timing")
                or catalyst_summary.get("timeframe")
                or catalyst_summary.get("time_horizon")
            ),
            timestamp=self._opt_str(row.get("generated_at") or row.get("window_end") or generated_at),
            raw_payload=dict(row),
        )

    @staticmethod
    def _format_error(error_payload: Any) -> str:
        if isinstance(error_payload, Mapping):
            code = error_payload.get("code")
            message = error_payload.get("message")
            if code and message:
                return f"{code}: {message}"
            if message:
                return str(message)
        return str(error_payload)

    @staticmethod
    def _as_dict(value: Any) -> Dict[str, Any]:
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _opt_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _count_platforms(platform_breakdown: List[Any]) -> Optional[int]:
        valid = [
            item for item in platform_breakdown
            if isinstance(item, Mapping) and item.get("platform")
        ]
        return len(valid) if valid else None

    @staticmethod
    def _infer_source(platform_breakdown: List[Any]) -> str:
        valid = [
            item for item in platform_breakdown
            if isinstance(item, Mapping) and item.get("platform")
        ]
        if not valid:
            return "social_scanner"
        best = max(valid, key=lambda item: float(item.get("mentions") or 0))
        return str(best.get("platform"))

    @staticmethod
    def _infer_sentiment(score_snapshot: Mapping[str, Any]) -> Optional[str]:
        value = score_snapshot.get("signed_momentum_score")
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric > 0:
            return "positive"
        if numeric < 0:
            return "negative"
        return "neutral"

    @staticmethod
    def _bucket_credibility(value: Any) -> Optional[str]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric >= 7:
            return "high"
        if numeric >= 4:
            return "medium"
        return "low"

    @staticmethod
    def _infer_low_liquidity(relative_volume: Any) -> bool:
        try:
            numeric = float(relative_volume)
        except (TypeError, ValueError):
            return False
        return numeric < 1.0

    def _get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        raise NotImplementedError


class MockSocialScannerClient(BaseSocialScannerClient):
    def __init__(
        self,
        fixture_path: str,
        *,
        endpoints: Optional[Mapping[str, str]] = None,
    ):
        self.fixture_path = Path(fixture_path)
        self.endpoints = dict(DEFAULT_ENDPOINTS)
        if endpoints:
            self.endpoints.update(dict(endpoints))

    def _get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if endpoint == self.endpoints["health"]:
            return {"status": "ok", "source": "mock"}
        if endpoint == self.endpoints["status"]:
            return {"hasStoredSnapshot": True, "source": "mock"}

        payload = self._read_fixture()
        if endpoint == self.endpoints["signals"]:
            return self._filter_signal_payload(payload, params or {})
        if endpoint.startswith("/v1/tickers/"):
            ticker = endpoint.rsplit("/", 1)[-1].upper()
            rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
            for row in rows:
                if str(row.get("ticker", "")).upper() == ticker:
                    if isinstance(payload, dict):
                        return {
                            "data": row,
                            "schema_version": payload.get("schema_version"),
                            "score_model_version": payload.get("score_model_version"),
                            "generated_at": payload.get("generated_at"),
                        }
                    return {"data": row}
            raise SocialScannerClientError("Mock fixture has no ticker detail for %s." % ticker)
        return payload

    def _read_fixture(self) -> Any:
        import json

        return json.loads(self.fixture_path.read_text(encoding="utf-8"))

    @staticmethod
    def _filter_signal_payload(payload: Any, params: Dict[str, Any]) -> Any:
        if not isinstance(payload, dict) or "data" not in payload or not isinstance(payload["data"], list):
            return payload

        rows = list(payload["data"])
        ticker_value = params.get("ticker")
        if ticker_value:
            if isinstance(ticker_value, list):
                normalized_tickers = {str(item).replace("$", "").upper() for item in ticker_value}
            else:
                normalized_tickers = {str(ticker_value).replace("$", "").upper()}
            rows = [
                row for row in rows
                if str(row.get("ticker", "")).replace("$", "").upper() in normalized_tickers
            ]

        limit_value = params.get("limit")
        if limit_value is not None:
            try:
                limit = max(int(limit_value), 0)
                rows = rows[:limit]
            except (TypeError, ValueError):
                pass

        filtered = dict(payload)
        filtered["data"] = rows
        filtered["request_echo"] = dict(params)
        return filtered


class HttpSocialScannerClient(BaseSocialScannerClient):
    def __init__(
        self,
        base_url: str,
        *,
        api_key: Optional[str] = None,
        timeout_seconds: int = 15,
        endpoints: Optional[Mapping[str, str]] = None,
        default_query_params: Optional[Mapping[str, Any]] = None,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.endpoints = dict(DEFAULT_ENDPOINTS)
        if endpoints:
            self.endpoints.update(dict(endpoints))
        self.default_query_params = dict(default_query_params or {})
        self.session = session or requests.Session()

    def _get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        merged_params = dict(self.default_query_params)
        if params:
            merged_params.update(params)

        response = self.session.get(
            f"{self.base_url}{endpoint}",
            params=merged_params or None,
            headers=headers or None,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()


def build_social_scanner_client(config: Mapping[str, Any]) -> SocialScannerClient:
    scanner_cfg = dict(config.get("social_scanner") or config.get("job", {}).get("social_scanner", {}))
    mock_cfg = dict(config.get("mock_mode") or config.get("job", {}).get("mock_mode", {}))

    if scanner_cfg.get("mock") or mock_cfg.get("enabled"):
        fixture_path = mock_cfg.get("raw_signals_fixture")
        if not fixture_path:
            raise SocialScannerClientError("Mock scanner mode requires 'raw_signals_fixture'.")
        return MockSocialScannerClient(
            fixture_path=str(fixture_path),
            endpoints=scanner_cfg.get("endpoints"),
        )

    base_url = scanner_cfg.get("base_url")
    if not base_url:
        raise SocialScannerClientError("Live scanner client requires 'base_url'.")

    return HttpSocialScannerClient(
        base_url=str(base_url),
        api_key=scanner_cfg.get("api_key"),
        timeout_seconds=int(scanner_cfg.get("timeout_seconds", 15)),
        endpoints=scanner_cfg.get("endpoints"),
        default_query_params=scanner_cfg.get("default_query_params"),
    )
