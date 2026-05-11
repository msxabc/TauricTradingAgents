import json

import pytest

from tradingagents.jobs.manual_research_report import run_manual_research_report
from tradingagents.research.signal_research_runner import SignalResearchRunnerError


class _StubRunner:
    def run(self, ticker, report_date):
        return {
            "ticker": ticker,
            "report_date": report_date,
            "signal": "Buy",
            "results_log_path": f"/tmp/{ticker}_{report_date}.json",
            "final_state": {
                "market_report": "Market report from graph.",
                "sentiment_report": "Sentiment report from graph.",
                "news_report": "News report from graph.",
                "fundamentals_report": "Fundamentals report from graph.",
                "investment_plan": "Investment plan.",
                "trader_investment_plan": "Trader plan.",
                "final_trade_decision": "Rating: Buy\nExecutive Summary: Buy the breakout.",
            },
        }


class _FailingRunner:
    def run(self, ticker, report_date):
        raise SignalResearchRunnerError("graph fail")


@pytest.mark.unit
class TestManualResearchReportJob:
    def test_manual_dry_run_writes_archive_for_matching_signal(self, tmp_path):
        result, context = run_manual_research_report(
            ticker="$nvda",
            report_date="2026-05-11",
            archive_path=str(tmp_path / "research_archive"),
            mock=True,
            dry_run=True,
            run_stamp="143022",
        )

        run_dir = context["run_dir"]
        report_json = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))

        assert result.status.value == "dry_run"
        assert run_dir.name == "143022_NVDA_nvda"
        assert report_json["ticker"] == "NVDA"
        assert report_json["social_trigger_found"] is True
        assert metadata["matching_signal_count"] == 1

    def test_manual_dry_run_handles_symbol_with_no_signal(self, tmp_path):
        result, context = run_manual_research_report(
            ticker="AAPL",
            report_date="2026-05-11",
            archive_path=str(tmp_path / "research_archive"),
            mock=True,
            dry_run=True,
            run_stamp="143023",
        )

        run_dir = context["run_dir"]
        report_json = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        result_json = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))

        assert result.status.value == "dry_run"
        assert report_json["ticker"] == "AAPL"
        assert report_json["social_trigger_found"] is False
        assert "No strong Social Scanner trigger was found" in report_json["trigger_signal"]
        assert result_json["errors"][0]["stage"] == "scanner_detail"

    def test_manual_real_run_uses_graph_runner_context(self, tmp_path):
        result, context = run_manual_research_report(
            ticker="NVDA",
            report_date="2026-05-11",
            archive_path=str(tmp_path / "research_archive"),
            mock=True,
            dry_run=False,
            run_stamp="143024",
            graph_runner=_StubRunner(),
        )

        run_dir = context["run_dir"]
        report_json = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        graph_context = json.loads((run_dir / "graph_context.json").read_text(encoding="utf-8"))

        assert result.status.value == "success"
        assert metadata["graph_execution"] == "completed"
        assert report_json["executive_summary"].startswith("Rating: Buy")
        assert graph_context["signal"] == "Buy"

    def test_manual_real_run_degrades_to_partial_success_on_graph_failure(self, tmp_path):
        result, context = run_manual_research_report(
            ticker="NVDA",
            report_date="2026-05-11",
            archive_path=str(tmp_path / "research_archive"),
            mock=True,
            dry_run=False,
            run_stamp="143025",
            graph_runner=_FailingRunner(),
        )

        run_dir = context["run_dir"]
        result_json = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))

        assert result.status.value == "partial_success"
        assert metadata["graph_execution"] == "failed"
        assert result_json["errors"][-1]["stage"] == "research"
