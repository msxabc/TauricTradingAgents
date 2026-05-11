from pathlib import Path

import pytest

from tradingagents.integrations.social_scanner_client import (
    HttpSocialScannerClient,
    MockSocialScannerClient,
    SocialScannerClientError,
    build_social_scanner_client,
)


FIXTURE_PATH = Path("tests/fixtures/social_scanner_signals.json")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return _FakeResponse(self.payload)


@pytest.mark.unit
class TestMockSocialScannerClient:
    def test_fetch_signals_returns_envelope_and_normalized_signals(self):
        client = MockSocialScannerClient(str(FIXTURE_PATH))

        response = client.fetch_signals({"limit": 2})

        assert response["schema_version"] == "phase3-v0.5.0"
        assert len(response["data"]) == 2
        assert len(response["normalized_signals"]) == 2
        assert response["normalized_signals"][0].ticker == "NVDA"
        assert response["normalized_signals"][0].signal_type == "active_momentum"
        assert response["normalized_signals"][1].low_liquidity is True

    def test_fetch_ticker_detail_uses_fixture_rows(self):
        client = MockSocialScannerClient(str(FIXTURE_PATH))

        detail = client.fetch_ticker_detail("SMCI")

        assert detail["data"]["ticker"] == "SMCI"
        assert detail["data"]["dominant_theme"] == "accounting_risk"

    def test_build_client_uses_mock_mode(self):
        client = build_social_scanner_client(
            {
                "job": {
                    "social_scanner": {"mock": True},
                    "mock_mode": {"enabled": True, "raw_signals_fixture": str(FIXTURE_PATH)},
                }
            }
        )

        assert isinstance(client, MockSocialScannerClient)


@pytest.mark.unit
class TestHttpSocialScannerClient:
    def test_http_client_uses_live_envelope_shape(self):
        payload = MockSocialScannerClient(str(FIXTURE_PATH)).fetch_signals()
        session = _FakeSession(payload)
        client = HttpSocialScannerClient(
            "http://127.0.0.1:3001",
            api_key="secret",
            timeout_seconds=9,
            default_query_params={"limit": 25},
            session=session,
        )

        response = client.fetch_signals({"ticker": "NVDA"})

        assert response["normalized_signals"][0].ticker == "NVDA"
        assert session.calls[0]["url"] == "http://127.0.0.1:3001/v1/signals"
        assert session.calls[0]["params"] == {"limit": 25, "ticker": "NVDA"}
        assert session.calls[0]["headers"] == {"Authorization": "Bearer secret"}
        assert session.calls[0]["timeout"] == 9

    def test_error_envelope_raises(self):
        session = _FakeSession({"error": {"code": "bad_request", "message": "broken"}})
        client = HttpSocialScannerClient("http://127.0.0.1:3001", session=session)

        with pytest.raises(SocialScannerClientError):
            client.fetch_signals()

    def test_build_client_requires_live_base_url(self):
        with pytest.raises(SocialScannerClientError):
            build_social_scanner_client({"job": {"social_scanner": {}}})
