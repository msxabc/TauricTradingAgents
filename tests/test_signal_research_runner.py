from unittest.mock import MagicMock

import pytest

from tradingagents.research.signal_research_runner import (
    SignalResearchRunner,
    SignalResearchRunnerError,
)


class _FakeGraph:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def propagate(self, ticker, report_date):
        return (
            {
                "company_of_interest": ticker,
                "trade_date": report_date,
                "market_report": "Market report.",
                "sentiment_report": "Sentiment report.",
                "news_report": "News report.",
                "fundamentals_report": "Fundamentals report.",
                "investment_plan": "Investment plan.",
                "trader_investment_plan": "Trader plan.",
                "final_trade_decision": "Rating: Buy\nExecutive Summary: Buy.",
            },
            "Buy",
        )


class _FailingGraph:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def propagate(self, ticker, report_date):
        raise RuntimeError("boom")


@pytest.mark.unit
class TestSignalResearchRunner:
    def test_runner_wraps_graph_outputs(self, tmp_path):
        config = {"results_dir": str(tmp_path)}
        runner = SignalResearchRunner(config, graph_factory=_FakeGraph)

        result = runner.run("NVDA", "2026-05-11")

        assert result["ticker"] == "NVDA"
        assert result["signal"] == "Buy"
        assert result["final_state"]["market_report"] == "Market report."
        assert result["results_log_path"].endswith(
            "NVDA/TradingAgentsStrategy_logs/full_states_log_2026-05-11.json"
        )

    def test_runner_maps_graph_failures(self, tmp_path):
        config = {"results_dir": str(tmp_path)}
        runner = SignalResearchRunner(config, graph_factory=_FailingGraph)

        with pytest.raises(SignalResearchRunnerError):
            runner.run("NVDA", "2026-05-11")
