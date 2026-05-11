"""Shared domain models for signal-driven research workflows."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ResearchModel(BaseModel):
    """Base model with strict-ish validation and deterministic export behavior."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )


class RunMode(str, Enum):
    DAILY = "daily"
    MANUAL = "manual"


class RunStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    DRY_RUN = "dry_run"
    FAILED = "failed"


class ResearchDepth(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    FULL = "full"


class WorkflowError(ResearchModel):
    stage: str = Field(description="Workflow stage that failed.")
    message: str = Field(description="Human-readable failure description.")
    code: Optional[str] = Field(default=None, description="Optional machine-readable error code.")
    retryable: bool = Field(default=False, description="Whether retry may succeed.")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured details safe to serialize into archives.",
    )


class DailyResearchBookRequest(ResearchModel):
    report_date: str = Field(description="Target research date in YYYY-MM-DD format.")
    scanner_window: str = Field(default="24h", description="Scanner lookback window.")
    universe: str = Field(default="default", description="Target scanner universe.")
    universe_mode: str = Field(default="default", description="How the universe should be interpreted.")
    max_reports: int = Field(default=5, ge=1, description="Maximum reports to produce.")
    min_candidate_score: Optional[float] = Field(
        default=None,
        description="Optional minimum candidate score threshold.",
    )
    research_depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Requested research depth.",
    )
    archive_path: Optional[str] = Field(default=None, description="Optional archive root override.")
    mock: bool = Field(default=False, description="Use mock scanner fixtures instead of live services.")
    dry_run: bool = Field(default=False, description="Build artifacts without network or LLM calls.")


class ManualResearchRequest(ResearchModel):
    query: Optional[str] = Field(default=None, description="Original free-text user query.")
    ticker: Optional[str] = Field(default=None, description="Explicit ticker override.")
    company: Optional[str] = Field(default=None, description="Optional company name hint.")
    report_date: str = Field(description="Target research date in YYYY-MM-DD format.")
    scanner_window: str = Field(default="24h", description="Scanner lookback window.")
    research_depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Requested research depth.",
    )
    archive_path: Optional[str] = Field(default=None, description="Optional archive root override.")
    mock: bool = Field(default=False, description="Use mock scanner fixtures instead of live services.")
    dry_run: bool = Field(default=False, description="Build artifacts without network or LLM calls.")
    allow_best_effort_resolution: bool = Field(
        default=False,
        description="Allow non-deterministic entity resolution when confidence is weak.",
    )


class EntityAlternative(ResearchModel):
    ticker: str = Field(description="Alternative ticker candidate.")
    company_name: Optional[str] = Field(default=None, description="Display company name.")
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Alternative match confidence if available.",
    )
    rationale: Optional[str] = Field(default=None, description="Why this alternative exists.")


class ResolvedEntity(ResearchModel):
    original_query: str = Field(description="User-supplied query before resolution.")
    ticker: str = Field(description="Canonical resolved ticker.")
    company_name: Optional[str] = Field(default=None, description="Resolved company name.")
    confidence: float = Field(ge=0.0, le=1.0, description="Resolution confidence.")
    rationale: str = Field(description="Explanation for the resolution decision.")
    alternatives: List[EntityAlternative] = Field(
        default_factory=list,
        description="Alternative candidates considered during resolution.",
    )


class NormalizedSocialSignal(ResearchModel):
    signal_id: str = Field(description="Stable signal identifier.")
    ticker: str = Field(description="Canonical ticker mentioned by the signal.")
    company_name: Optional[str] = Field(default=None, description="Display company name.")
    signal_type: Optional[str] = Field(default=None, description="Signal category or subtype.")
    dominant_narrative: Optional[str] = Field(default=None, description="Main narrative or topic.")
    source: Optional[str] = Field(default=None, description="Originating platform or feed.")
    sentiment: Optional[str] = Field(default=None, description="High-level sentiment label.")
    evidence_tier: Optional[str] = Field(default=None, description="Evidence quality bucket if available.")
    materiality_score: Optional[float] = Field(default=None, description="Importance score if available.")
    attention_anomaly: Optional[float] = Field(default=None, description="Attention anomaly feature.")
    narrative_velocity: Optional[float] = Field(default=None, description="Narrative velocity feature.")
    sentiment_delta: Optional[float] = Field(default=None, description="Sentiment change feature.")
    source_credibility: Optional[float] = Field(default=None, description="Source credibility feature.")
    source_diversity: Optional[int] = Field(default=None, ge=0, description="Unique-source count.")
    market_confirmation: Optional[float] = Field(default=None, description="Market confirmation feature.")
    tradability: Optional[float] = Field(default=None, description="Tradability feature.")
    novelty: Optional[float] = Field(default=None, description="Novelty feature.")
    spam_risk: Optional[float] = Field(default=None, description="Spam-risk feature.")
    stale_signal: bool = Field(default=False, description="Whether the signal is stale.")
    low_liquidity: bool = Field(default=False, description="Whether the signal fails liquidity checks.")
    catalyst_clock: Optional[str] = Field(default=None, description="Timing note for catalyst proximity.")
    timestamp: Optional[str] = Field(default=None, description="Original signal timestamp if available.")
    raw_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original provider payload for audit and replay.",
    )


class ResearchCandidate(ResearchModel):
    ticker: str = Field(description="Canonical ticker selected for research.")
    company_name: Optional[str] = Field(default=None, description="Display company name.")
    query: Optional[str] = Field(default=None, description="Original query, mainly for manual mode.")
    dominant_narrative: Optional[str] = Field(default=None, description="Main candidate narrative.")
    signal_type: Optional[str] = Field(default=None, description="Primary signal type.")
    evidence_tier: Optional[str] = Field(default=None, description="Evidence quality bucket.")
    materiality_score: Optional[float] = Field(default=None, description="Importance score.")
    candidate_score: Optional[float] = Field(default=None, description="Ranking score.")
    ranking_rationale: Optional[str] = Field(default=None, description="Why this candidate ranked where it did.")
    catalyst_clock: Optional[str] = Field(default=None, description="Timing note for catalyst proximity.")
    price_assimilation: Optional[str] = Field(default=None, description="What appears priced in already.")
    trigger_found: bool = Field(default=True, description="Whether scanner trigger context was found.")
    matching_signals: List[NormalizedSocialSignal] = Field(
        default_factory=list,
        description="Normalized signals associated with the candidate.",
    )
    resolved_entity: Optional[ResolvedEntity] = Field(
        default=None,
        description="Entity resolution output for manual mode.",
    )


class ResearchReport(ResearchModel):
    mode: RunMode = Field(description="Daily or manual report mode.")
    report_date: str = Field(description="Target research date.")
    ticker: str = Field(description="Canonical ticker for the report.")
    company_name: Optional[str] = Field(default=None, description="Display company name.")
    original_query: Optional[str] = Field(default=None, description="Original user query for manual mode.")
    resolved_entity: Optional[ResolvedEntity] = Field(default=None, description="Entity resolution details.")
    social_trigger_found: bool = Field(default=False, description="Whether scanner trigger context exists.")
    executive_summary: str = Field(description="Top-line summary of the research case.")
    why_this_report_was_requested: str = Field(description="Why the system produced this report.")
    trigger_signal: str = Field(description="Trigger signal summary or explicit no-trigger note.")
    materiality_assessment: str = Field(description="Why the situation matters.")
    variant_view: str = Field(description="What variant perception or setup exists.")
    social_narrative_analysis: str = Field(description="Narrative and sentiment analysis.")
    evidence_quality_and_source_hierarchy: str = Field(description="Source and evidence discussion.")
    price_assimilation: str = Field(description="What seems priced in already.")
    market_technical_context: str = Field(description="Market and technical context.")
    news_fundamental_verification: str = Field(description="News and fundamental verification.")
    catalyst_clock: str = Field(description="Timing and catalyst framing.")
    bull_case: str = Field(description="Bull case summary.")
    bear_case: str = Field(description="Bear case summary.")
    possible_trade_expressions: str = Field(description="Possible trade expressions.")
    key_risks: str = Field(description="Key risks to monitor.")
    invalidation_conditions: str = Field(description="What would invalidate the thesis.")
    monitoring_plan: str = Field(description="How the setup should be monitored.")
    evidence_appendix: str = Field(description="Evidence appendix.")
    research_only_disclaimer: str = Field(description="Research-only disclaimer text.")
    source_artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional references to source artifacts or graph outputs.",
    )


class ResearchRunResult(ResearchModel):
    mode: RunMode = Field(description="Daily or manual workflow mode.")
    run_id: str = Field(description="Stable run identifier.")
    status: RunStatus = Field(description="Overall run status.")
    report_date: str = Field(description="Target research date.")
    archive_path: str = Field(description="Path to the written archive root.")
    reports_generated: int = Field(ge=0, description="Number of reports generated.")
    errors: List[WorkflowError] = Field(
        default_factory=list,
        description="Structured non-fatal or fatal errors captured during the run.",
    )
