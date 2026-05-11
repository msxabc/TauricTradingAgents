import json

import pytest

from tradingagents.jobs.manual_research_report import run_manual_research_report


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
