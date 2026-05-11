"""Shared research workflow contracts and helpers."""

from .models import (
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
from .report_builder import build_manual_research_report, render_research_report_markdown
from .serialization import model_to_primitive, stable_json_dumps
from .ticker_utils import TickerValidationError, normalize_research_ticker

__all__ = [
    "DailyResearchBookRequest",
    "EntityAlternative",
    "ManualResearchRequest",
    "NormalizedSocialSignal",
    "ResearchCandidate",
    "ResearchDepth",
    "ResearchReport",
    "ResearchRunResult",
    "ResolvedEntity",
    "RunMode",
    "RunStatus",
    "WorkflowError",
    "TickerValidationError",
    "build_manual_research_report",
    "model_to_primitive",
    "normalize_research_ticker",
    "render_research_report_markdown",
    "stable_json_dumps",
]
