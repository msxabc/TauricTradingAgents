"""Report builder for PRD-shaped research reports."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from tradingagents.research.models import (
    ManualResearchRequest,
    ResearchCandidate,
    ResearchReport,
    RunMode,
)


_PLACEHOLDER = "Not available from current graph output."
_DISCLAIMER = "This report is for research purposes only and is not financial, investment, or trading advice."
_NO_TRIGGER = "No strong Social Scanner trigger was found for this manual inquiry."


def build_manual_research_report(
    request: ManualResearchRequest,
    candidate: ResearchCandidate,
    *,
    source_artifacts: Optional[Mapping[str, str]] = None,
    graph_context: Optional[Mapping[str, Any]] = None,
) -> ResearchReport:
    graph_context = dict(graph_context or {})
    trigger_found = candidate.trigger_found and len(candidate.matching_signals) > 0
    trigger_signal = (
        _build_trigger_signal(candidate) if trigger_found else _NO_TRIGGER
    )
    rationale = candidate.ranking_rationale or _PLACEHOLDER
    dominant_narrative = candidate.dominant_narrative or _PLACEHOLDER
    catalyst_clock = candidate.catalyst_clock or _PLACEHOLDER
    price_assimilation = candidate.price_assimilation or _PLACEHOLDER

    return ResearchReport(
        mode=RunMode.MANUAL,
        report_date=request.report_date,
        ticker=candidate.ticker,
        company_name=candidate.company_name,
        original_query=request.ticker,
        resolved_entity=candidate.resolved_entity,
        social_trigger_found=trigger_found,
        executive_summary=_build_executive_summary(candidate, trigger_found, graph_context),
        why_this_report_was_requested=f"Manual symbol inquiry requested for {candidate.ticker}.",
        trigger_signal=trigger_signal,
        materiality_assessment=(
            f"Scanner materiality score: {candidate.materiality_score:.2f}."
            if candidate.materiality_score is not None
            else _PLACEHOLDER
        ),
        variant_view=rationale,
        social_narrative_analysis=_merge_sections(
            dominant_narrative,
            _opt_text(graph_context.get("sentiment_report")),
        ),
        evidence_quality_and_source_hierarchy=_build_evidence_summary(candidate),
        price_assimilation=price_assimilation,
        market_technical_context=_merge_sections(
            _build_market_context(candidate),
            _opt_text(graph_context.get("market_report")),
        ),
        news_fundamental_verification=_merge_sections(
            _opt_text(graph_context.get("news_report")),
            _opt_text(graph_context.get("fundamentals_report")),
        ),
        catalyst_clock=catalyst_clock,
        bull_case=_build_bull_case(candidate),
        bear_case=_build_bear_case(candidate),
        possible_trade_expressions=_build_trade_expressions(candidate),
        key_risks=_build_key_risks(candidate),
        invalidation_conditions=_build_invalidation(candidate),
        monitoring_plan=_build_monitoring_plan(candidate),
        evidence_appendix=_build_evidence_appendix(candidate),
        research_only_disclaimer=_DISCLAIMER,
        source_artifacts={
            **dict(source_artifacts or {}),
            **_graph_artifact_refs(graph_context),
        },
    )


def render_research_report_markdown(report: ResearchReport) -> str:
    """Render the institutional report as markdown."""
    parts = [
        f"# {report.ticker} Research Report",
        "",
        "## 1. Executive Summary",
        report.executive_summary,
        "",
        "## 2. Query / Entity Mapping",
        _line_or_placeholder(f"Original input: {report.original_query}" if report.original_query else None),
        _line_or_placeholder(f"Ticker: {report.ticker}"),
        _line_or_placeholder(f"Company: {report.company_name}" if report.company_name else None),
        "",
        "## 3. Why This Report Was Requested",
        report.why_this_report_was_requested,
        "",
        "## 4. Trigger Signal",
        report.trigger_signal,
        "",
        "## 5. Materiality Assessment",
        report.materiality_assessment,
        "",
        "## 6. Variant View",
        report.variant_view,
        "",
        "## 7. Social / Narrative Analysis",
        report.social_narrative_analysis,
        "",
        "## 8. Evidence Quality and Source Hierarchy",
        report.evidence_quality_and_source_hierarchy,
        "",
        "## 9. Price Assimilation / What Is Already Priced",
        report.price_assimilation,
        "",
        "## 10. Market / Technical Context",
        report.market_technical_context,
        "",
        "## 11. News / Fundamental Verification",
        report.news_fundamental_verification,
        "",
        "## 12. Catalyst Clock",
        report.catalyst_clock,
        "",
        "## 13. Bull Case",
        report.bull_case,
        "",
        "## 14. Bear Case",
        report.bear_case,
        "",
        "## 15. Possible Trade Expressions",
        report.possible_trade_expressions,
        "",
        "## 16. Key Risks",
        report.key_risks,
        "",
        "## 17. Invalidation Conditions",
        report.invalidation_conditions,
        "",
        "## 18. Monitoring Plan",
        report.monitoring_plan,
        "",
        "## 19. Evidence Appendix",
        report.evidence_appendix,
        "",
        "## Disclaimer",
        report.research_only_disclaimer,
    ]
    return "\n".join(parts).strip() + "\n"


def _build_trigger_signal(candidate: ResearchCandidate) -> str:
    lines = []
    if candidate.dominant_narrative:
        lines.append(f"Dominant narrative: {candidate.dominant_narrative}.")
    if candidate.signal_type:
        lines.append(f"Signal type: {candidate.signal_type}.")
    if candidate.materiality_score is not None:
        lines.append(f"Signal score: {candidate.materiality_score:.2f}.")
    if candidate.matching_signals:
        lines.append(f"Matching signals: {len(candidate.matching_signals)}.")
    return " ".join(lines) if lines else _PLACEHOLDER


def _build_executive_summary(
    candidate: ResearchCandidate,
    trigger_found: bool,
    graph_context: Mapping[str, Any],
) -> str:
    final_decision = _opt_text(graph_context.get("final_trade_decision"))
    if final_decision:
        return final_decision
    if trigger_found:
        return (
            f"{candidate.ticker} has active scanner context tied to "
            f"{candidate.dominant_narrative or 'an unresolved narrative'}. "
            "This is a dry-run research artifact, so downstream graph analysis is not yet included."
        )
    return (
        f"{candidate.ticker} was requested manually, but no current scanner trigger was found. "
        "This report is a structured placeholder for the institutional workflow."
    )


def _build_evidence_summary(candidate: ResearchCandidate) -> str:
    if not candidate.matching_signals:
        return _NO_TRIGGER
    tiers = [signal.evidence_tier for signal in candidate.matching_signals if signal.evidence_tier]
    sources = [signal.source for signal in candidate.matching_signals if signal.source]
    tier_text = ", ".join(sorted(set(tiers))) if tiers else "unknown"
    source_text = ", ".join(sorted(set(sources))) if sources else "unknown"
    return f"Evidence tiers observed: {tier_text}. Primary sources: {source_text}."


def _build_market_context(candidate: ResearchCandidate) -> str:
    if candidate.matching_signals:
        signal = candidate.matching_signals[0]
        details = []
        if signal.tradability is not None:
            details.append(f"Relative volume proxy: {signal.tradability:.2f}.")
        if signal.market_confirmation is not None:
            details.append(f"Market confirmation proxy: {signal.market_confirmation:.2f}.")
        return " ".join(details) if details else _PLACEHOLDER
    return _PLACEHOLDER


def _build_bull_case(candidate: ResearchCandidate) -> str:
    if candidate.dominant_narrative:
        return f"Bull case centers on {candidate.dominant_narrative} gaining traction."
    return _PLACEHOLDER


def _build_bear_case(candidate: ResearchCandidate) -> str:
    if candidate.matching_signals and candidate.matching_signals[0].spam_risk is not None:
        return f"Bear case includes signal fragility and spam burden risk ({candidate.matching_signals[0].spam_risk:.2f})."
    return _PLACEHOLDER


def _build_trade_expressions(candidate: ResearchCandidate) -> str:
    return f"Common stock monitoring for {candidate.ticker}; execution details require downstream graph output."


def _build_key_risks(candidate: ResearchCandidate) -> str:
    if not candidate.trigger_found:
        return "Primary risk is lack of a confirmed current social trigger."
    if candidate.matching_signals and candidate.matching_signals[0].low_liquidity:
        return "Primary risk is weak tradability / liquidity context."
    return "Primary risk is that social attention does not persist."


def _build_invalidation(candidate: ResearchCandidate) -> str:
    if candidate.trigger_found:
        return "Invalidate if narrative attention fades or market confirmation reverses."
    return "Invalidate if later scanner data still fails to surface any signal context."


def _build_monitoring_plan(candidate: ResearchCandidate) -> str:
    return f"Monitor {candidate.ticker} for new scanner signals, focus-list changes, and refreshed price context."


def _build_evidence_appendix(candidate: ResearchCandidate) -> str:
    if not candidate.matching_signals:
        return _NO_TRIGGER
    lines = []
    for signal in candidate.matching_signals:
        lines.append(
            f"- signal_id={signal.signal_id} source={signal.source or 'unknown'} "
            f"narrative={signal.dominant_narrative or 'unknown'}"
        )
    return "\n".join(lines)


def _line_or_placeholder(value: Optional[str]) -> str:
    return value or _PLACEHOLDER


def _opt_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _merge_sections(*sections: Optional[str]) -> str:
    cleaned = [section.strip() for section in sections if section and section.strip()]
    if not cleaned:
        return _PLACEHOLDER
    return "\n\n".join(cleaned)


def _graph_artifact_refs(graph_context: Mapping[str, Any]) -> dict[str, str]:
    refs = {}
    if graph_context.get("results_log_path"):
        refs["graph_results_log_path"] = str(graph_context["results_log_path"])
    if graph_context.get("signal") is not None:
        refs["graph_signal"] = str(graph_context["signal"])
    return refs
