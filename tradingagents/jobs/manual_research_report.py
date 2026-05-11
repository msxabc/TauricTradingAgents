"""Manual symbol-only research report job."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import argparse

from tradingagents.archive import ArchiveWriter
from tradingagents.integrations import (
    SocialScannerClientError,
    build_social_scanner_client,
)
from tradingagents.research.config_loader import load_workflow_config
from tradingagents.research.models import (
    ManualResearchRequest,
    ResearchCandidate,
    ResearchRunResult,
    RunMode,
    RunStatus,
    WorkflowError,
)
from tradingagents.research.report_builder import (
    build_manual_research_report,
    render_research_report_markdown,
)
from tradingagents.research.serialization import model_to_primitive
from tradingagents.research.ticker_utils import normalize_research_ticker


def run_manual_research_report(
    *,
    ticker: str,
    report_date: str,
    config_path: Optional[str] = None,
    archive_path: Optional[str] = None,
    mock: bool = False,
    dry_run: bool = False,
    research_depth: Optional[str] = None,
    scanner_window: Optional[str] = None,
    run_stamp: Optional[str] = None,
) -> Tuple[ResearchRunResult, Dict[str, Any]]:
    normalized_ticker = normalize_research_ticker(ticker)

    cli_overrides: Dict[str, Any] = {"job": {"run": {}, "mock_mode": {}, "social_scanner": {}}}
    if archive_path:
        cli_overrides["job"]["archive"] = {"base_path": archive_path}
    if scanner_window:
        cli_overrides["job"]["run"]["scanner_window"] = scanner_window
    if research_depth:
        cli_overrides["job"]["run"]["research_depth"] = research_depth
    if mock:
        cli_overrides["job"]["mock_mode"]["enabled"] = True
        cli_overrides["job"]["social_scanner"]["mock"] = True

    config = load_workflow_config(
        "manual_research_report",
        config_path=config_path,
        cli_overrides=cli_overrides,
    )

    request = ManualResearchRequest(
        ticker=normalized_ticker,
        report_date=report_date,
        scanner_window=config["job"]["run"]["scanner_window"],
        research_depth=config["job"]["run"]["research_depth"],
        archive_path=config["job"]["archive"]["base_path"],
        mock=bool(config["job"]["mock_mode"].get("enabled", False) or mock),
        dry_run=dry_run,
        allow_best_effort_resolution=False,
    )

    writer = ArchiveWriter(config["job"]["archive"]["base_path"])
    effective_run_stamp = run_stamp or datetime.now().strftime("%H%M%S")
    run_dir = writer.create_manual_run_dir(
        request.report_date,
        normalized_ticker,
        normalized_ticker.lower(),
        run_stamp=effective_run_stamp,
        overwrite_existing_run=bool(config["job"]["archive"].get("overwrite_existing_run", False)),
    )

    errors = []
    client = build_social_scanner_client(config)

    detail = None
    detail_error = None
    try:
        detail = client.fetch_ticker_detail(normalized_ticker)
    except SocialScannerClientError as exc:
        detail_error = str(exc)
        errors.append(
            WorkflowError(
                stage="scanner_detail",
                message=f"Ticker detail unavailable for {normalized_ticker}: {exc}",
                retryable=False,
            )
        )

    signal_response = client.fetch_signals({"ticker": normalized_ticker, "limit": 25})
    matching_signals = [
        signal
        for signal in signal_response["normalized_signals"]
        if signal.ticker == normalized_ticker
    ]

    candidate = build_manual_candidate(
        ticker=normalized_ticker,
        signal_response=signal_response,
        detail=detail,
        detail_error=detail_error,
    )
    report = build_manual_research_report(
        request,
        candidate,
        source_artifacts={
            "run_dir": str(run_dir),
            "ticker_detail_available": "true" if detail else "false",
        },
    )
    markdown = render_research_report_markdown(report)

    run_metadata = {
        "mode": "manual",
        "ticker": normalized_ticker,
        "report_date": report_date,
        "dry_run": dry_run,
        "mock": request.mock,
        "matching_signal_count": len(matching_signals),
        "scanner_schema_version": signal_response.get("schema_version"),
        "scanner_score_model_version": signal_response.get("score_model_version"),
        "scanner_generated_at": signal_response.get("generated_at"),
        "graph_execution": "skipped" if dry_run else "not_implemented",
    }

    result = ResearchRunResult(
        mode=RunMode.MANUAL,
        run_id=run_dir.name,
        status=RunStatus.DRY_RUN if dry_run else RunStatus.SUCCESS,
        report_date=report_date,
        archive_path=str(run_dir),
        reports_generated=1,
        errors=errors,
    )

    writer.write_artifact_bundle(
        run_dir,
        json_artifacts={
            "request.json": request,
            "run_metadata.json": run_metadata,
            "raw_signals.json": signal_response["data"],
            "normalized_signals.json": matching_signals,
            "candidate.json": candidate,
            "report.json": report,
            "result.json": result,
        },
        markdown_artifacts={"report.md": markdown},
    )

    context = {
        "request": request,
        "candidate": candidate,
        "report": report,
        "run_dir": run_dir,
        "run_metadata": run_metadata,
        "result": result,
    }
    return result, context


def build_manual_candidate(
    *,
    ticker: str,
    signal_response: Dict[str, Any],
    detail: Optional[Dict[str, Any]],
    detail_error: Optional[str],
) -> ResearchCandidate:
    matching_signals = [
        signal
        for signal in signal_response["normalized_signals"]
        if signal.ticker == ticker
    ]

    detail_row = {}
    if detail and isinstance(detail.get("data"), dict):
        detail_row = detail["data"]

    primary_signal = matching_signals[0] if matching_signals else None
    company_name = None
    if primary_signal and primary_signal.company_name:
        company_name = primary_signal.company_name
    elif detail_row.get("company_name"):
        company_name = str(detail_row["company_name"])

    ranking_rationale = None
    if primary_signal:
        ranking_rationale = (
            f"Symbol {ticker} has {len(matching_signals)} matching scanner signal(s)"
            f" with primary narrative '{primary_signal.dominant_narrative or 'unknown'}'."
        )
    elif detail_error:
        ranking_rationale = detail_error

    return ResearchCandidate(
        ticker=ticker,
        company_name=company_name,
        query=ticker,
        dominant_narrative=(
            primary_signal.dominant_narrative
            if primary_signal
            else _opt_str(detail_row.get("dominant_theme"))
        ),
        signal_type=(
            primary_signal.signal_type
            if primary_signal
            else _opt_str(detail_row.get("primary_category"))
        ),
        evidence_tier=primary_signal.evidence_tier if primary_signal else None,
        materiality_score=primary_signal.materiality_score if primary_signal else None,
        candidate_score=primary_signal.materiality_score if primary_signal else None,
        ranking_rationale=ranking_rationale,
        catalyst_clock=primary_signal.catalyst_clock if primary_signal else None,
        price_assimilation=_build_price_assimilation(detail_row, primary_signal),
        trigger_found=bool(matching_signals),
        matching_signals=matching_signals,
        resolved_entity=None,
    )


def _build_price_assimilation(detail_row: Dict[str, Any], primary_signal: Optional[Any]) -> Optional[str]:
    if primary_signal and primary_signal.market_confirmation is not None:
        return f"Market confirmation proxy: {primary_signal.market_confirmation:.2f}."

    price_snapshot = detail_row.get("price_snapshot")
    if isinstance(price_snapshot, dict):
        change_30m = price_snapshot.get("price_change_pct_30m")
        if change_30m is not None:
            try:
                return f"30m price change: {float(change_30m):.2f}%."
            except (TypeError, ValueError):
                return None
    return None


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a manual symbol-only research report.")
    parser.add_argument("--ticker", required=True, help="Exact ticker symbol to analyze.")
    parser.add_argument("--date", required=True, help="Research date in YYYY-MM-DD format.")
    parser.add_argument("--config", dest="config_path", help="Optional JSON/YAML config path.")
    parser.add_argument("--archive-path", help="Override archive base path.")
    parser.add_argument("--scanner-window", help="Override scanner lookback window.")
    parser.add_argument("--research-depth", help="Override research depth.")
    parser.add_argument("--mock", action="store_true", help="Use mock scanner fixtures.")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM and graph execution.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    result, _ = run_manual_research_report(
        ticker=args.ticker,
        report_date=args.date,
        config_path=args.config_path,
        archive_path=args.archive_path,
        mock=args.mock,
        dry_run=args.dry_run,
        research_depth=args.research_depth,
        scanner_window=args.scanner_window,
    )
    print(model_to_primitive(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
