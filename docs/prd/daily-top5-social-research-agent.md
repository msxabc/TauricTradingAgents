# PRD: Daily Top 5 Social-Signal Trading Research Agent

## 1. Objective

Build a new automated research workflow inside this forked `TauricTradingAgents` codebase.

The new workflow should:

1. Connect to a configurable deployed **Social Scanner API**.
2. Fetch all social trading signals for a configured window/universe.
3. Normalize, deduplicate, group, and rank the signals.
4. Select the top 5 trading research candidates.
5. Run signal-aware TradingAgents research on each selected candidate.
6. Generate 5 structured Markdown research reports.
7. Generate machine-readable JSON artifacts.
8. Archive all outputs into a date-based daily folder for human review.

The system should produce **trading research candidate reports**, not autonomous trade execution decisions.

---

## 2. Important Context for Codex

This implementation is to be developed by modifying this forked TradingAgents codebase.

Upstream repository:

```text
https://github.com/TauricResearch/TradingAgents
```

Codex should inspect the existing repository structure before coding and adapt the implementation to the actual module layout, naming conventions, config system, CLI patterns, and existing agent graph.

Do not assume the exact paths in this PRD already exist. The file paths below are recommended targets. If this fork uses different conventions, place equivalent functionality in the closest appropriate modules.

The Social Scanner is assumed to already be deployed and accessible through an HTTP API.

The Social Scanner API is configurable. The final API documentation / user guide will be provided to Codex separately. Until then, implement the scanner integration behind a clean client abstraction and support mock/local fixture mode for testing.

---

## 3. Product Name

Working name:

```text
Daily Top 5 Trading Research Agent
```

Internal job name:

```text
daily_top5_social_research
```

---

## 4. Product Goal

Every configured run, the agent should answer:

```text
From all social scanner signals in the selected window, what are the 5 most research-worthy trading candidates, and what is the structured trading research case for each?
```

The system should create a daily archive like:

```text
research_archive/
  2026-05-11/
    run_metadata.json
    raw_signals.json
    normalized_signals.json
    candidates_ranked.json
    ranking_rationale.json
    summary.md
    reports/
      01_SMCI_bearish_accounting_risk.md
      02_NVDA_bullish_ai_demand.md
      03_COIN_bullish_crypto_beta.md
      04_TSLA_robotaxi_rumor.md
      05_GME_retail_squeeze.md
```

---

## 5. Non-Goals

Do not implement:

```text
- broker integration
- order execution
- autonomous trading
- portfolio sizing
- live dashboard
- user account system
- paid subscription system
- full backtesting engine
```

This PRD is only for the research-agent workflow and archive generation.

---

## 6. Expected User Workflow

### 6.1 CLI workflow

User runs:

```bash
python -m tradingagents.jobs.daily_top5_social_research \
  --date 2026-05-11 \
  --config ./configs/daily_top5.yaml
```

or:

```bash
python -m tradingagents.jobs.daily_top5_social_research --config ./configs/daily_top5.yaml
```

If `--date` is omitted, use the current local date from config timezone.

### 6.2 Output workflow

After the run, user opens:

```text
research_archive/YYYY-MM-DD/summary.md
```

Then reviews the five detailed reports in:

```text
research_archive/YYYY-MM-DD/reports/
```

---

## 7. Configuration Requirements

Implement a YAML-based config file, environment-variable fallback, or integrate with the existing TradingAgents config system if one already exists.

Recommended config path:

```text
configs/daily_top5_social_research.yaml
```

Example config:

```yaml
daily_top5_social_research:
  enabled: true

  archive:
    base_path: "./research_archive"
    overwrite_existing_run: false

  run:
    timezone: "America/New_York"
    scanner_window: "24h"
    max_reports: 5
    min_candidate_score: 70
    include_watchlist_grade_fallbacks: true
    research_depth: "standard"
    max_raw_signals: 1000

  social_scanner:
    enabled: true
    base_url: "${SOCIAL_SCANNER_BASE_URL}"
    api_key: "${SOCIAL_SCANNER_API_KEY}"
    timeout_seconds: 20
    max_retries: 3
    retry_backoff_seconds: 2
    api_version: "v1"

    # The final API docs/user guide will be provided to the bot.
    # Implement the client so endpoint paths and request parameters
    # are configurable and easy to change.
    endpoints:
      signals: "/v1/signals/social"
      ticker_snapshot: "/v1/tickers/{ticker}/snapshot"
      ticker_narratives: "/v1/tickers/{ticker}/narratives"
      ticker_evidence: "/v1/tickers/{ticker}/evidence"

    default_query_params:
      universe: "default"
      window: "24h"

  ranking:
    diversity:
      max_per_sector: 2
      max_same_signal_type: 2
      max_same_dominant_narrative: 2
      allow_override_if_score_gap_above: 15

    weights:
      attention_anomaly: 0.25
      narrative_velocity: 0.20
      sentiment_delta: 0.15
      source_credibility: 0.10
      source_diversity: 0.05
      market_confirmation: 0.10
      tradability: 0.10
      novelty: 0.05

    penalties:
      spam_risk_weight: 0.20
      stale_signal_weight: 0.15
      low_liquidity_weight: 0.10

  research:
    include_social_analyst: true
    include_market_analyst: true
    include_news_analyst: true
    include_fundamentals_analyst: false
    include_risk_analyst: true
    include_bull_bear_debate: false

    output_format:
      markdown: true
      json: true

  mock_mode:
    enabled: false
    raw_signals_fixture: "./tests/fixtures/social_signals_sample.json"
```

### 7.1 Environment variables

Support:

```bash
SOCIAL_SCANNER_BASE_URL
SOCIAL_SCANNER_API_KEY
DAILY_TOP5_ARCHIVE_PATH
DAILY_TOP5_RESEARCH_DEPTH
```

Do not hardcode scanner URLs or API keys.

---

## 8. Social Scanner API Integration

### 8.1 Requirement

Create a configurable Social Scanner client. The API docs/user guide will be provided separately, so implement the client with clean endpoint configuration and flexible response normalization.

Recommended file:

```text
tradingagents/integrations/social_scanner_client.py
```

or, if the repo has an existing data provider layer:

```text
tradingagents/dataflows/social_scanner_client.py
```

### 8.2 Client class

Implement:

```python
class SocialScannerClient:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: int = 20,
        max_retries: int = 3,
        retry_backoff_seconds: int = 2,
        endpoints: dict | None = None,
        default_query_params: dict | None = None,
    ):
        ...

    def get_social_signals(
        self,
        universe: str = "default",
        window: str = "24h",
        limit: int | None = None,
        extra_params: dict | None = None,
    ) -> list[dict]:
        ...

    def get_ticker_snapshot(
        self,
        ticker: str,
        window: str = "24h",
        extra_params: dict | None = None,
    ) -> dict:
        ...

    def get_ticker_narratives(
        self,
        ticker: str,
        window: str = "24h",
        extra_params: dict | None = None,
    ) -> list[dict]:
        ...

    def get_ticker_evidence(
        self,
        ticker: str,
        signal_id: str | None = None,
        window: str = "24h",
        extra_params: dict | None = None,
    ) -> list[dict]:
        ...
```

### 8.3 HTTP behavior

Implement:

```text
- bearer token auth if api_key is provided
- configurable timeout
- retry on 429, 500, 502, 503, 504
- no retry on 400, 401, 403, 404 unless API docs later require otherwise
- clear error messages
- structured exception type for scanner failures
```

Recommended custom exceptions:

```python
class SocialScannerError(Exception): ...
class SocialScannerAuthError(SocialScannerError): ...
class SocialScannerRateLimitError(SocialScannerError): ...
class SocialScannerResponseError(SocialScannerError): ...
```

### 8.4 Mock mode

If `mock_mode.enabled = true`, bypass HTTP and load raw signals from the fixture path.

This is required so Codex can implement tests without relying on the real deployed scanner.

---

## 9. Internal Data Models

Use dataclasses or Pydantic models depending on existing repo style. Prefer Pydantic if the repo already uses it; otherwise dataclasses are fine.

Recommended file:

```text
tradingagents/research/social_signal_models.py
```

### 9.1 RawSocialSignal

```python
@dataclass
class RawSocialSignal:
    signal_id: str
    ticker: str
    company_name: str | None
    timestamp: str
    signal_type: str
    window: str | None
    mention_count: int | None
    mention_zscore: float | None
    sentiment_score: float | None
    sentiment_delta: float | None
    source_diversity: float | None
    source_credibility: float | None
    spam_risk: float | None
    novelty_score: float | None
    market_confirmation_score: float | None
    tradability_score: float | None
    sector: str | None
    top_narratives: list[dict]
    top_evidence: list[dict]
    raw: dict
```

### 9.2 ResearchCandidate

```python
@dataclass
class ResearchCandidate:
    candidate_id: str
    ticker: str
    company_name: str | None
    dominant_narrative: str
    direction: str
    signal_type: str
    sector: str | None
    source_signal_ids: list[str]
    rolled_up_signals: list[RawSocialSignal]

    attention_anomaly_score: float
    narrative_velocity_score: float
    sentiment_delta_score: float
    source_credibility_score: float
    source_diversity_score: float
    market_confirmation_score: float
    tradability_score: float
    novelty_score: float
    spam_risk_score: float
    stale_signal_score: float

    candidate_score: float
    urgency_score: float
    research_value_score: float
    risk_score: float
    confidence: float

    selection_rationale: str
```

### 9.3 ResearchReport

```python
@dataclass
class ResearchReport:
    ticker: str
    candidate_id: str
    rank: int
    report_date: str
    verdict: str
    directional_bias: str
    confidence: float
    time_horizon: str
    executive_summary: str
    why_selected: str
    trigger_signal_summary: str
    social_analysis: str
    market_analysis: str
    news_verification: str
    bull_case: list[str]
    bear_case: list[str]
    trading_scenarios: list[dict]
    key_risks: list[str]
    invalidation_conditions: list[str]
    monitoring_plan: list[str]
    evidence_appendix: list[dict]
```

---

## 10. Verdict Enum

Each detailed report must include one of these verdicts:

```text
actionable_long
actionable_short
watch_for_confirmation
likely_noise
avoid_due_to_risk
```

These are research verdicts, not trading instructions.

---

## 11. Candidate Pipeline

Recommended files:

```text
tradingagents/ranking/signal_normalizer.py
tradingagents/ranking/candidate_builder.py
tradingagents/ranking/candidate_scorer.py
tradingagents/ranking/candidate_selector.py
```

Codex may place these elsewhere if the repo has an established structure.

### 11.1 Normalize signals

Function:

```python
def normalize_raw_signal(raw: dict) -> RawSocialSignal:
    ...
```

Requirements:

```text
- tolerate missing optional fields
- preserve original raw dict
- normalize ticker to uppercase
- normalize scores to 0.0–1.0 where possible
- infer direction from signal_type, sentiment_score, sentiment_delta, or narrative polarity
- do not crash on malformed signal; log and skip invalid required fields
```

Required fields:

```text
- signal_id, or generate deterministic hash if missing
- ticker
- timestamp
- signal_type
```

### 11.2 Build candidates

Function:

```python
def build_research_candidates(signals: list[RawSocialSignal]) -> list[ResearchCandidate]:
    ...
```

Grouping key:

```text
ticker + dominant_narrative + direction
```

If no dominant narrative exists, group by:

```text
ticker + signal_type + direction
```

Deduplicate duplicate `signal_id`.

Roll up multiple signals into one candidate.

### 11.3 Score candidates

Function:

```python
def score_candidate(candidate: ResearchCandidate, config: dict) -> ResearchCandidate:
    ...
```

Default scoring:

```text
Research Score =
  25% attention anomaly
+ 20% narrative velocity
+ 15% sentiment delta
+ 10% source credibility
+  5% source diversity
+ 10% market confirmation
+ 10% tradability
+  5% novelty
- spam risk penalty
- stale signal penalty
- low liquidity penalty
```

Implementation notes:

```text
- Score should be 0–100.
- Missing fields should not crash the scorer.
- Use conservative defaults for missing fields.
- Preserve component scores for auditability.
- Add selection_rationale text.
```

### 11.4 Select top 5

Function:

```python
def select_top_candidates(
    candidates: list[ResearchCandidate],
    max_reports: int,
    min_candidate_score: float,
    diversity_config: dict,
    include_watchlist_grade_fallbacks: bool,
) -> list[ResearchCandidate]:
    ...
```

Requirements:

```text
- sort by candidate_score descending
- enforce diversity rules where possible
- select up to max_reports
- if fewer than max_reports exceed threshold and fallback enabled, fill remaining slots with lower-scoring candidates labeled as watchlist-grade
- if fewer than max_reports total candidates exist, return fewer and log clearly
```

Diversity defaults:

```text
- max 2 per sector
- max 2 same signal_type
- max 2 same dominant narrative
```

---

## 12. TradingAgents Research Integration

### 12.1 Requirement

Add a signal-aware research runner that uses the existing TradingAgents graph/agent architecture.

Recommended file:

```text
tradingagents/research/signal_research_runner.py
```

The runner should reuse existing TradingAgents components wherever possible.

Do not rewrite the whole TradingAgents framework.

### 12.2 Runner interface

Implement:

```python
class SignalResearchRunner:
    def __init__(
        self,
        trading_agents_config: dict,
        social_scanner_client: SocialScannerClient | None = None,
        research_depth: str = "standard",
    ):
        ...

    def run_for_candidate(
        self,
        candidate: ResearchCandidate,
        rank: int,
        report_date: str,
    ) -> ResearchReport:
        ...
```

### 12.3 Signal-aware research context

Before calling existing TradingAgents graph, construct a context object:

```python
research_context = {
    "ticker": candidate.ticker,
    "company_name": candidate.company_name,
    "candidate_id": candidate.candidate_id,
    "rank": rank,
    "trigger_signal": {
        "signal_type": candidate.signal_type,
        "dominant_narrative": candidate.dominant_narrative,
        "direction": candidate.direction,
        "candidate_score": candidate.candidate_score,
        "urgency_score": candidate.urgency_score,
        "research_value_score": candidate.research_value_score,
        "risk_score": candidate.risk_score,
        "confidence": candidate.confidence,
        "source_signal_ids": candidate.source_signal_ids,
        "selection_rationale": candidate.selection_rationale,
    },
    "social_context": {
        "rolled_up_signals": [...],
        "top_evidence": [...],
        "component_scores": {...},
    },
}
```

### 12.4 Key prompt instruction

Wherever existing TradingAgents prompts are extended, include this instruction:

```text
This research was triggered by a specific social scanner signal.
Do not analyze the ticker generically.
Determine whether the trigger signal is material, confirmed, contradicted, stale, or likely noise.
Use the social signal as the research frame, while checking it against market, news, fundamental, and risk evidence.
```

### 12.5 Social Analyst

Add a new analyst if the existing architecture supports adding analyst nodes.

Recommended file:

```text
tradingagents/agents/analysts/social_analyst.py
```

Social Analyst responsibility:

```text
- interpret social signal
- summarize narrative
- identify sentiment/attention change
- evaluate source diversity/credibility
- evaluate spam/pump risk
- determine whether the signal is new, recycled, coordinated, stale, or meaningful
- produce a concise social analysis section
```

Social Analyst output should include:

```json
{
  "social_view": "bullish|bearish|mixed|neutral",
  "attention_anomaly": "low|medium|high",
  "dominant_narratives": ["..."],
  "credibility": "low|medium|high",
  "spam_risk": "low|medium|high",
  "market_relevance": "low|medium|high",
  "key_evidence": ["..."],
  "open_questions": ["..."],
  "confidence": 0.0
}
```

### 12.6 If adding a new agent is too invasive

If the existing TradingAgents graph is hard to modify, implement a first-pass version by:

```text
1. Prepending social context to the ticker research prompt.
2. Running the existing TradingAgents analysis.
3. Post-processing the result into the required report schema.
```

But structure the code so a true Social Analyst node can be added later.

---

## 13. Research Depth Modes

Implement at least two modes:

```text
fast
standard
```

Optional:

```text
full
```

### 13.1 Fast mode

Use:

```text
- social context
- market/price context if existing tools support it
- news context if existing tools support it
- final synthesizer
```

### 13.2 Standard mode

Use:

```text
- social analyst
- market/technical analyst
- news analyst
- risk analyst
- final synthesizer
```

### 13.3 Full mode

Use as many existing TradingAgents roles as available:

```text
- all standard agents
- fundamentals analyst
- bull/bear debate
- risk committee
```

If the existing repo does not support all of these cleanly, log a warning and fall back to standard.

---

## 14. Report Generation

Recommended files:

```text
tradingagents/research/report_writer.py
tradingagents/research/daily_summary_writer.py
```

### 14.1 Markdown report format

Each report must be written as Markdown.

Template:

```markdown
# {rank}. {ticker} — Signal-Aware Trading Research Report

**Date:** {report_date}  
**Company:** {company_name}  
**Candidate ID:** {candidate_id}  
**Verdict:** {verdict}  
**Directional Bias:** {directional_bias}  
**Confidence:** {confidence}  
**Time Horizon:** {time_horizon}  

> Research only. Not financial advice. No autonomous trade execution.

---

## 1. Executive Summary

{executive_summary}

## 2. Why This Was Selected

{why_selected}

## 3. Trigger Signal

{trigger_signal_summary}

## 4. Social / Narrative Analysis

{social_analysis}

## 5. Market / Technical Context

{market_analysis}

## 6. News / Fundamental Verification

{news_verification}

## 7. Bull Case

{bull_case_bullets}

## 8. Bear Case

{bear_case_bullets}

## 9. Trading Scenarios

{trading_scenarios}

## 10. Key Risks

{key_risks}

## 11. Invalidation Conditions

{invalidation_conditions}

## 12. Monitoring Plan

{monitoring_plan}

## 13. Evidence Appendix

{evidence_appendix}
```

### 14.2 File naming

Sanitize filenames.

Format:

```text
{rank:02d}_{ticker}_{direction}_{dominant_narrative_slug}.md
```

Example:

```text
01_SMCI_bearish_accounting_risk.md
```

If ticker or narrative is missing:

```text
01_UNKNOWN_candidate_{candidate_id}.md
```

### 14.3 JSON report

Also write one JSON file per report if config enables JSON:

```text
reports_json/
  01_SMCI_bearish_accounting_risk.json
```

---

## 15. Daily Summary Generation

Create:

```text
summary.md
```

Required sections:

```markdown
# Daily Top 5 Trading Research Summary — YYYY-MM-DD

## Run Overview

## Top Candidates Table

## Highest Conviction Candidate

## Highest Risk Candidate

## Common Themes

## Rejected / Not Selected Signals

## Suggested Review Order

## Notes and Failures
```

Top candidate table columns:

```text
Rank
Ticker
Dominant Narrative
Direction
Signal Type
Candidate Score
Verdict
Confidence
Report Link
```

---

## 16. Archive Writer

Recommended file:

```text
tradingagents/archive/archive_writer.py
```

Implement:

```python
class DailyArchiveWriter:
    def __init__(self, base_path: str, report_date: str, overwrite_existing_run: bool = False):
        ...

    def prepare_run_directory(self) -> Path:
        ...

    def write_json(self, relative_path: str, data: Any) -> Path:
        ...

    def write_text(self, relative_path: str, content: str) -> Path:
        ...

    def write_report(self, rank: int, candidate: ResearchCandidate, report: ResearchReport) -> Path:
        ...
```

Behavior:

```text
- create date folder if missing
- create reports/ folder
- create reports_json/ folder if needed
- if folder exists and overwrite_existing_run=false, create run suffix:
  research_archive/2026-05-11/run_002/
  or error clearly
```

Preferred behavior: create a run suffix rather than overwriting.

---

## 17. Job Entrypoint

Recommended file:

```text
tradingagents/jobs/daily_top5_social_research.py
```

Implement executable module:

```bash
python -m tradingagents.jobs.daily_top5_social_research --config ./configs/daily_top5_social_research.yaml
```

### 17.1 CLI arguments

Support:

```text
--config PATH
--date YYYY-MM-DD
--archive-path PATH
--scanner-window 24h
--universe default
--max-reports 5
--min-candidate-score 70
--research-depth fast|standard|full
--mock
--raw-signals-fixture PATH
--dry-run
```

### 17.2 Dry run

If `--dry-run`:

```text
- fetch/load raw signals
- normalize
- rank
- write raw_signals.json, normalized_signals.json, candidates_ranked.json
- do not run expensive research
- write a summary stating that research was skipped
```

This is important for testing.

---

## 18. Error Handling

### 18.1 Scanner failures

If scanner API fails:

```text
- if mock fixture exists and config allows fallback, use fixture
- otherwise write run_metadata.json with failure status
- exit non-zero
```

### 18.2 Individual research failures

If one selected candidate fails during research:

```text
- continue remaining candidates
- write error report stub for failed candidate
- include failure in summary.md
- include stack trace or summarized error in run_metadata.json
```

### 18.3 Malformed signals

If individual signals are malformed:

```text
- skip invalid signal
- count skipped signals
- include skipped count in run_metadata.json
```

---

## 19. Run Metadata

Write:

```text
run_metadata.json
```

Required fields:

```json
{
  "run_date": "2026-05-11",
  "run_started_at": "2026-05-11T12:00:00Z",
  "run_completed_at": "2026-05-11T12:18:00Z",
  "status": "completed",
  "scanner_window": "24h",
  "universe": "default",
  "raw_signal_count": 431,
  "valid_signal_count": 402,
  "skipped_signal_count": 29,
  "candidate_count": 37,
  "selected_candidate_count": 5,
  "reports_generated": 5,
  "research_depth": "standard",
  "archive_path": "./research_archive/2026-05-11",
  "errors": []
}
```

If partial failure:

```json
{
  "status": "partial_failure",
  "errors": [
    {
      "stage": "research",
      "ticker": "TSLA",
      "candidate_id": "cand_abc",
      "message": "Research runner timed out"
    }
  ]
}
```

---

## 20. Required JSON Artifacts

### 20.1 raw_signals.json

Exact raw API response or loaded fixture.

### 20.2 normalized_signals.json

List of normalized signals.

### 20.3 candidates_ranked.json

All ranked candidates, not only selected top 5.

Each object should include:

```json
{
  "rank": 1,
  "selected": true,
  "ticker": "SMCI",
  "candidate_id": "SMCI_bearish_accounting_risk",
  "dominant_narrative": "accounting risk",
  "direction": "bearish",
  "signal_type": "bearish_narrative_acceleration",
  "candidate_score": 88.2,
  "urgency_score": 82.1,
  "research_value_score": 91.0,
  "risk_score": 74.4,
  "confidence": 0.68,
  "source_signal_ids": ["sig_123", "sig_456"],
  "selection_rationale": "Highest attention anomaly and fast bearish narrative velocity with moderate source diversity."
}
```

### 20.4 ranking_rationale.json

Include selected and rejected rationale.

```json
{
  "selected": [],
  "not_selected": [],
  "diversity_adjustments": [],
  "threshold": 70
}
```

---

## 21. Report Quality Requirements

Each report must:

```text
- explain why the candidate was selected
- summarize the trigger signal
- discuss social/narrative evidence
- check whether market/news context confirms or contradicts the signal
- include bull and bear cases
- include key risks
- include invalidation conditions
- include monitoring plan
- include confidence score
- include one allowed verdict enum
- include “research only, not financial advice” disclaimer
```

Each report must avoid:

```text
- guaranteed outcomes
- unsupported claims
- direct order placement instructions
- hidden assumptions
```

---

## 22. Testing Requirements

Add unit tests where appropriate.

Recommended tests:

```text
tests/test_social_signal_normalizer.py
tests/test_candidate_builder.py
tests/test_candidate_scorer.py
tests/test_candidate_selector.py
tests/test_archive_writer.py
tests/test_daily_top5_job_dry_run.py
```

### 22.1 Fixture

Create sample fixture:

```text
tests/fixtures/social_signals_sample.json
```

Include at least:

```text
- 10 raw signals
- duplicate ticker/narrative signals
- missing optional fields
- high spam-risk signal
- low-score signal
- multiple sectors
```

### 22.2 Test cases

#### Normalizer

```text
- uppercase ticker
- preserve raw dict
- handle missing optional fields
- skip missing ticker/timestamp/signal_type
```

#### Candidate builder

```text
- group same ticker/narrative/direction
- deduplicate signal_id
- create fallback grouping if narrative missing
```

#### Scorer

```text
- score range is 0–100
- spam risk reduces score
- high mention_zscore increases score
- missing fields do not crash
```

#### Selector

```text
- returns max 5
- respects threshold
- fills fallback if enabled
- enforces diversity where possible
```

#### Archive writer

```text
- creates date folder
- writes JSON
- writes reports
- does not overwrite unless configured
```

#### Dry run

```text
- loads fixture
- writes archive artifacts
- does not call research runner
```

---

## 23. Acceptance Criteria

Implementation is complete when:

```text
1. The repo has a runnable daily_top5_social_research job.
2. The job can run in mock mode using a fixture.
3. The job can be configured with Social Scanner base URL and API key.
4. The job fetches or loads raw signals.
5. The job normalizes, groups, scores, and ranks candidates.
6. The job selects up to 5 candidates.
7. The job runs signal-aware research for selected candidates, or a stubbed research runner in test mode.
8. The job writes a date-based archive folder.
9. The archive includes summary.md, raw_signals.json, normalized_signals.json, candidates_ranked.json, ranking_rationale.json, run_metadata.json, and reports.
10. Each Markdown report follows the required section structure.
11. Unit tests pass.
12. Running `--dry-run --mock` works without external services.
```

---

## 24. Suggested Implementation Order for Codex

Codex should proceed in this order:

### Step 1: Inspect repository

Inspect this TradingAgents fork structure.

Identify:

```text
- package root
- existing config patterns
- existing CLI entrypoints
- existing dataflow / tools modules
- existing agent graph runner
- existing report/output patterns
```

### Step 2: Add models

Implement normalized signal and candidate models.

### Step 3: Add scanner client

Implement configurable SocialScannerClient with mock-mode support.

### Step 4: Add ranking pipeline

Implement normalizer, candidate builder, scorer, selector.

### Step 5: Add archive writer

Implement date-based archive output.

### Step 6: Add dry-run job

Make CLI work end-to-end without research.

### Step 7: Integrate TradingAgents research

Add signal-aware research runner using existing TradingAgents architecture.

### Step 8: Add report writer

Generate Markdown and JSON reports.

### Step 9: Add daily summary

Generate summary.md.

### Step 10: Add tests

Implement fixture-based tests.

---

## 25. Implementation Notes for TradingAgents Integration

Because the actual TradingAgents code structure may vary, Codex should adapt to the existing architecture.

Preferred approach:

```text
- reuse existing graph or CLI research runner
- add trigger_signal and social_context to the research state/input
- add social analyst if graph extension is straightforward
- otherwise prepend social context to the existing research prompt
- post-process result into required ResearchReport schema
```

Do not break existing TradingAgents behavior.

Existing ticker analysis should continue to work.

The new daily top 5 workflow should be additive.

---

## 26. Example Signal-Aware Prompt

Use this as a base prompt for each selected candidate:

```text
You are producing a signal-aware trading research report.

Ticker: {ticker}
Company: {company_name}
Research Date: {report_date}

This research was triggered by the following social scanner candidate:

Signal Type: {signal_type}
Dominant Narrative: {dominant_narrative}
Direction: {direction}
Candidate Score: {candidate_score}
Urgency Score: {urgency_score}
Research Value Score: {research_value_score}
Risk Score: {risk_score}
Confidence: {confidence}

Selection Rationale:
{selection_rationale}

Source Signal IDs:
{source_signal_ids}

Social Evidence:
{top_evidence}

Your task:
Do not analyze this ticker generically. Determine whether this trigger signal is material, confirmed, contradicted, stale, or likely noise.

Produce a structured trading research report with:
1. Executive summary
2. Why selected
3. Trigger signal summary
4. Social/narrative analysis
5. Market/technical context
6. News/fundamental verification
7. Bull case
8. Bear case
9. Trading scenarios
10. Key risks
11. Invalidation conditions
12. Monitoring plan
13. Final verdict

Allowed verdicts:
- actionable_long
- actionable_short
- watch_for_confirmation
- likely_noise
- avoid_due_to_risk

This is research only, not financial advice. Do not recommend autonomous order execution.
```

---

## 27. Final Guidance for Codex

Implement this as an additive feature in this TradingAgents fork.

Prioritize:

```text
1. Working dry-run pipeline
2. Clean scanner API abstraction
3. Robust ranking and archive generation
4. Minimal but functional TradingAgents research integration
5. Tests
```

Do not overbuild dashboard, scheduling infrastructure, or broker integration.

The first milestone is successful local execution:

```bash
python -m tradingagents.jobs.daily_top5_social_research \
  --config ./configs/daily_top5_social_research.yaml \
  --mock \
  --dry-run
```

The second milestone is successful full execution against real Social Scanner API:

```bash
python -m tradingagents.jobs.daily_top5_social_research \
  --config ./configs/daily_top5_social_research.yaml
```

Final deliverable: a repeatable daily archive containing ranked candidates and five structured trading research reports.
