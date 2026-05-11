import pytest

from tradingagents.research.models import ManualResearchRequest, ResearchCandidate, ResearchDepth
from tradingagents.research.report_builder import (
    build_manual_research_report,
    render_research_report_markdown,
)


@pytest.mark.unit
class TestReportBuilder:
    def test_builds_no_trigger_manual_report(self):
        request = ManualResearchRequest(
            ticker="AAPL",
            report_date="2026-05-11",
            scanner_window="24h",
            research_depth=ResearchDepth.STANDARD,
            dry_run=True,
        )
        candidate = ResearchCandidate(
            ticker="AAPL",
            company_name="Apple Inc.",
            query="AAPL",
            trigger_found=False,
            matching_signals=[],
        )

        report = build_manual_research_report(request, candidate)
        markdown = render_research_report_markdown(report)

        assert report.social_trigger_found is False
        assert "No strong Social Scanner trigger was found" in report.trigger_signal
        assert "# AAPL Research Report" in markdown
        assert "## 19. Evidence Appendix" in markdown

    def test_graph_context_overrides_placeholders(self):
        request = ManualResearchRequest(
            ticker="NVDA",
            report_date="2026-05-11",
            scanner_window="24h",
            research_depth=ResearchDepth.STANDARD,
            dry_run=False,
        )
        candidate = ResearchCandidate(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            query="NVDA",
            trigger_found=True,
            matching_signals=[],
        )

        report = build_manual_research_report(
            request,
            candidate,
            graph_context={
                "final_trade_decision": "Rating: Buy\nExecutive Summary: Follow through.",
                "market_report": "Market says risk-on.",
                "news_report": "News confirms demand.",
                "fundamentals_report": "Fundamentals still strong.",
                "results_log_path": "/tmp/nvda.json",
                "signal": "Buy",
            },
        )

        assert report.executive_summary.startswith("Rating: Buy")
        assert "Market says risk-on." in report.market_technical_context
        assert "News confirms demand." in report.news_fundamental_verification
        assert report.source_artifacts["graph_signal"] == "Buy"
