import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingagents.research.models import (
    DailyResearchBookRequest,
    EntityAlternative,
    ManualResearchRequest,
    NormalizedSocialSignal,
    ResearchCandidate,
    ResearchDepth,
    ResearchReport,
    ResearchRunResult,
    ResolvedEntity,
    RunMode,
    RunStatus,
    WorkflowError,
)
from tradingagents.research.serialization import model_to_primitive, stable_json_dumps


@pytest.mark.unit
class TestWorkflowRequests:
    def test_daily_request_uses_expected_defaults(self):
        request = DailyResearchBookRequest(report_date="2026-05-11")

        assert request.scanner_window == "24h"
        assert request.max_reports == 5
        assert request.research_depth == ResearchDepth.STANDARD
        assert request.mock is False
        assert request.dry_run is False

    def test_manual_request_supports_resolution_flag(self):
        request = ManualResearchRequest(
            query="Google",
            report_date="2026-05-11",
            dry_run=True,
            allow_best_effort_resolution=True,
        )

        assert request.query == "Google"
        assert request.allow_best_effort_resolution is True
        assert request.research_depth == ResearchDepth.STANDARD

    def test_request_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            DailyResearchBookRequest(report_date="2026-05-11", unknown_field="bad")


@pytest.mark.unit
class TestResearchModels:
    def test_resolved_entity_enforces_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ResolvedEntity(
                original_query="Google",
                ticker="GOOGL",
                confidence=1.5,
                rationale="bad",
            )

    def test_candidate_and_run_result_round_trip_to_primitives(self):
        entity = ResolvedEntity(
            original_query="Google",
            ticker="GOOGL",
            company_name="Alphabet Inc.",
            confidence=0.91,
            rationale="Default Alphabet share class for generic Google queries.",
            alternatives=[
                EntityAlternative(
                    ticker="GOOG",
                    company_name="Alphabet Inc.",
                    confidence=0.72,
                    rationale="Alternate share class.",
                )
            ],
        )
        signal = NormalizedSocialSignal(
            signal_id="sig-1",
            ticker="GOOGL",
            company_name="Alphabet Inc.",
            signal_type="narrative",
            dominant_narrative="AI demand",
            source="scanner_fixture",
            raw_payload={"foo": "bar"},
        )
        candidate = ResearchCandidate(
            ticker="GOOGL",
            company_name="Alphabet Inc.",
            query="Google",
            dominant_narrative="AI demand",
            trigger_found=True,
            matching_signals=[signal],
            resolved_entity=entity,
        )
        result = ResearchRunResult(
            mode=RunMode.MANUAL,
            run_id="manual-001",
            status=RunStatus.DRY_RUN,
            report_date="2026-05-11",
            archive_path="research_archive/manual/2026-05-11/120000_GOOGL_google",
            reports_generated=1,
            errors=[
                WorkflowError(
                    stage="research",
                    message="Skipped graph execution in dry-run mode.",
                    retryable=False,
                )
            ],
        )

        primitive = model_to_primitive({"candidate": candidate, "result": result})

        assert primitive["candidate"]["resolved_entity"]["ticker"] == "GOOGL"
        assert primitive["candidate"]["matching_signals"][0]["raw_payload"] == {"foo": "bar"}
        assert primitive["result"]["status"] == "dry_run"
        assert primitive["result"]["errors"][0]["stage"] == "research"

    def test_report_model_captures_prd_shape(self):
        report = ResearchReport(
            mode=RunMode.MANUAL,
            report_date="2026-05-11",
            ticker="GOOGL",
            company_name="Alphabet Inc.",
            original_query="Google",
            social_trigger_found=False,
            executive_summary="Research-only summary.",
            why_this_report_was_requested="Manual inquiry requested.",
            trigger_signal="No strong Social Scanner trigger was found for this manual inquiry.",
            materiality_assessment="Large-cap AI platform with active narrative flow.",
            variant_view="Expectations may still underestimate monetization.",
            social_narrative_analysis="Mixed but constructive discussion.",
            evidence_quality_and_source_hierarchy="Mostly secondary social chatter.",
            price_assimilation="Partially priced.",
            market_technical_context="Range-bound.",
            news_fundamental_verification="No decisive contradiction found.",
            catalyst_clock="Earnings in two weeks.",
            bull_case="Cloud and AI upside.",
            bear_case="Valuation already rich.",
            possible_trade_expressions="Common stock or options watchlist.",
            key_risks="Crowded positioning.",
            invalidation_conditions="Growth decelerates sharply.",
            monitoring_plan="Track earnings revisions and ad trends.",
            evidence_appendix="Append fixture references here.",
            research_only_disclaimer="For research purposes only.",
        )

        primitive = model_to_primitive(report)
        assert primitive["ticker"] == "GOOGL"
        assert primitive["social_trigger_found"] is False


@pytest.mark.unit
class TestSerializationHelpers:
    def test_stable_json_dumps_sorts_keys(self):
        payload = {"z": 1, "a": {"d": 4, "b": 2}}

        rendered = stable_json_dumps(payload)
        parsed = json.loads(rendered)

        assert rendered.index('"a"') < rendered.index('"z"')
        assert rendered.index('"b"') < rendered.index('"d"')
        assert parsed == {"a": {"b": 2, "d": 4}, "z": 1}

    def test_serialization_sanitizes_paths_and_exceptions(self):
        payload = {
            "path": Path("/tmp/report.json"),
            "error": RuntimeError("boom"),
        }

        primitive = model_to_primitive(payload)

        assert primitive["path"] == "/tmp/report.json"
        assert primitive["error"] == {"type": "RuntimeError", "message": "boom"}
