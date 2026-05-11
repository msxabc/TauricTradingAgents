"""Thin wrapper around TradingAgentsGraph for candidate-level research runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from tradingagents.dataflows.utils import safe_ticker_component


class SignalResearchRunnerError(RuntimeError):
    """Raised when graph-backed research execution fails."""


class SignalResearchRunner:
    """Run the existing TradingAgents graph without changing its core contract."""

    def __init__(
        self,
        config: Dict[str, Any],
        *,
        graph_factory: Optional[Callable[..., Any]] = None,
    ):
        self.config = config
        self.graph_factory = graph_factory or self._default_graph_factory

    def run(self, ticker: str, report_date: str) -> Dict[str, Any]:
        try:
            graph = self.graph_factory(debug=False, config=self.config)
            final_state, signal = graph.propagate(ticker, report_date)
        except Exception as exc:  # pragma: no cover - exercised via tests with fake graph
            raise SignalResearchRunnerError(
                f"Graph research execution failed for {ticker} on {report_date}: {exc}"
            ) from exc

        return {
            "ticker": ticker,
            "report_date": report_date,
            "final_state": final_state,
            "signal": signal,
            "results_log_path": self._results_log_path(ticker, report_date),
        }

    def _results_log_path(self, ticker: str, report_date: str) -> str:
        safe_ticker = safe_ticker_component(ticker)
        return str(
            Path(self.config["results_dir"])
            / safe_ticker
            / "TradingAgentsStrategy_logs"
            / f"full_states_log_{report_date}.json"
        )

    @staticmethod
    def _default_graph_factory(**kwargs: Any) -> Any:
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        return TradingAgentsGraph(**kwargs)
