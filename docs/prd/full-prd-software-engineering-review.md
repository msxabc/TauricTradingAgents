# Full PRD Software Engineering Review

## Scope

This review covers the full PRD set for the signal-driven trading research agent, including both the scheduled daily workflow and the manual inquiry workflow:

```text
docs/prd/daily-top5-social-research-agent.md
docs/prd/manual-inquiry-research-mode.md
```

The review perspective is a software developer building production-quality research infrastructure in a Citadel-like environment.

The goal is not to critique the trading idea. The goal is to make the PRDs implementation-ready for Codex or another coding agent.

---

## Executive Engineering Verdict

The PRD direction is strong. The product boundary is sensible:

```text
Social Scanner = external signal source
TradingAgents fork = research and reasoning engine
Daily workflow = scheduled discovery and ranking
Manual workflow = user-triggered research report generation
Archive = persistent research book and audit trail
```

However, the PRDs need stronger engineering contracts before implementation. They currently describe the desired behavior well, but leave too much ambiguity around exact interfaces, data contracts, deterministic edge-case handling, failure semantics, artifact layout, and testability.

Before Codex implements, the PRDs should be updated to specify:

```text
1. canonical naming
2. shared pipeline architecture
3. strict request/result schemas
4. deterministic entity resolution
5. idempotent archive layout
6. status enum and failure semantics
7. no-network dry-run contract
8. scanner API validation and pagination behavior
9. schema-backed report generation
10. structured logging and observability
11. dependency/config rules
12. required test matrix
```

---

## 1. Canonical Naming

### Issue

The PRDs currently use several names for the same concept:

```text
Daily Top 5 Social-Signal Trading Research Agent
Daily Signal-Driven Trading Research Book
daily_top5_social_research
daily_signal_research_book
```

This will lead to inconsistent modules, configs, archive paths, CLI commands, and tests.

### Required Update

Declare one canonical naming scheme:

```text
Scheduled job module:
tradingagents.jobs.daily_signal_research_book

Manual job module:
tradingagents.jobs.manual_research_report

Shared config:
configs/daily_signal_research_book.yaml

Daily archive root:
research_archive/daily/

Manual archive root:
research_archive/manual/
```

Backward-compatible aliases may exist, but canonical names must be used internally.

---

## 2. Shared Pipeline Architecture

### Issue

The scheduled and manual workflows are described separately. Manual mode says it should reuse the same components, but the main PRD should define a single shared architecture explicitly.

### Required Update

Define a shared pipeline:

```text
Input Request
  -> Config Load + Validation
  -> Entity/Ticker Resolution, if needed
  -> Social Scanner Fetch
  -> Signal Normalization
  -> Candidate Construction
  -> Institutional Gates
  -> Candidate Scoring / Selection, scheduled mode only
  -> SignalResearchRunner
  -> ResearchReport schema
  -> ReportWriter
  -> ArchiveWriter
  -> Metadata + Feedback + Outcome Artifacts
```

Scheduled mode:

```text
all scanner signals -> grouped candidates -> rank -> top N -> reports
```

Manual mode:

```text
user query/ticker -> resolved entity -> matching scanner context -> synthetic candidate -> report
```

Manual mode must not implement a separate report generator.

---

## 3. Data Contracts

### Issue

The PRDs define some models, but they do not define enough orchestration-level request/result schemas.

### Required Update

Add explicit models. Use Pydantic if already used in the repo; otherwise use dataclasses plus deterministic serialization helpers.

```python
@dataclass
class DailyResearchBookRequest:
    report_date: str
    scanner_window: str
    universe: str
    universe_mode: str
    max_reports: int
    min_candidate_score: float
    research_depth: str
    archive_path: str | None
    mock: bool
    dry_run: bool

@dataclass
class ManualResearchRequest:
    query: str | None
    ticker: str | None
    company: str | None
    report_date: str
    scanner_window: str
    research_depth: str
    archive_path: str | None
    mock: bool
    dry_run: bool
    allow_best_effort_resolution: bool

@dataclass
class ResearchRunResult:
    mode: str  # daily|manual
    run_id: str
    status: str
    report_date: str
    archive_path: str
    reports_generated: int
    errors: list[dict]
```

All persisted data objects must support deterministic serialization:

```text
- stable key order where practical
- JSON-serializable primitive values
- no raw exception objects in JSON
- no API keys or secrets in serialized payloads
```

---

## 4. Entity Resolution

### Issue

Manual mode allows ambiguous behavior: choose a best match or return an error. This is too loose.

### Required Update

Define deterministic precedence:

```text
1. If --ticker is provided, it is canonical for data fetching.
2. If --ticker and --company are both provided, ticker is canonical and company is display metadata.
3. If --ticker and --query are both provided, ticker is canonical; preserve query as original_user_query.
4. If --query exactly matches a known ticker, use that ticker.
5. If --query maps to exactly one known alias with confidence >= 0.85, use it.
6. If multiple matches exist or confidence < 0.85, fail with AmbiguousEntityError unless --allow-best-effort-resolution is provided.
7. Every report must disclose original query, resolved ticker, confidence, rationale, and alternatives.
```

Default mapping:

```text
Google -> Alphabet Inc. -> GOOGL
GOOG -> alternate Alphabet share class
```

MVP resolver source:

```text
configs/entity_aliases.yaml
```

---

## 5. Archive Idempotency

### Issue

Archive folders are described, but overwrite and collision behavior is ambiguous.

### Required Update

Use run-specific folders for both scheduled and manual workflows.

Scheduled:

```text
research_archive/daily/YYYY-MM-DD/run_001/
  request.json
  run_metadata.json
  raw_signals.json
  normalized_signals.json
  candidates_ranked.json
  ranking_rationale.json
  review_feedback.yaml
  outcome_tracking.json
  summary.md
  reports/
  reports_json/
```

Manual:

```text
research_archive/manual/YYYY-MM-DD/HHMMSS_<TICKER>_<slug>/
  request.json
  resolved_entity.json
  run_metadata.json
  raw_social_context.json
  synthetic_candidate.json
  report.md
  report.json
```

Rules:

```text
- Never overwrite an existing run folder unless overwrite_existing_run=true.
- If scheduled run_001 exists, create run_002.
- Manual runs always include HHMMSS in folder name.
- ArchiveWriter is responsible for atomic-ish writes where practical: write temp file then rename.
```

---

## 6. Status Enum and Failure Semantics

### Issue

The PRDs mention statuses informally, but implementation needs a single enum.

### Required Update

Define statuses:

```text
completed
partial_failure
failed
dry_run_completed
skipped_no_candidates
ambiguous_entity
scanner_unavailable
research_failed
archive_failed
config_error
```

Every `run_metadata.json` must include:

```json
{
  "run_id": "...",
  "mode": "daily|manual",
  "status": "completed",
  "started_at": "...",
  "completed_at": "...",
  "errors": []
}
```

Error objects should use this shape:

```json
{
  "stage": "scanner_fetch|entity_resolution|ranking|research|archive|config",
  "ticker": "GOOGL",
  "candidate_id": "...",
  "error_type": "SocialScannerRateLimitError",
  "message": "sanitized error message"
}
```

Do not serialize stack traces by default. Stack traces may be logged locally in debug mode.

---

## 7. No-Network Dry Run Contract

### Issue

The PRDs require `--dry-run`, but do not define exactly what must not happen.

### Required Update

For `--dry-run --mock`, guarantee:

```text
- no Social Scanner API calls
- no LLM provider calls
- no market data API calls
- no news API calls
- no external entity lookup service calls
- fixtures only
- all expected artifact stubs written
```

Daily dry-run must write:

```text
request.json
run_metadata.json
raw_signals.json
normalized_signals.json
candidates_ranked.json
ranking_rationale.json
summary.md with research_skipped notice
review_feedback.yaml
outcome_tracking.json
```

Manual dry-run must write:

```text
request.json
resolved_entity.json
raw_social_context.json, fixture or empty
synthetic_candidate.json
run_metadata.json
report.md stub
report.json stub
```

This is essential for CI tests.

---

## 8. Social Scanner API Contract

### Issue

The SocialScannerClient interface is good, but response validation and pagination are under-specified.

### Required Update

Add these requirements:

```text
- Client must validate response shape before returning.
- Client must return list[dict] for get_social_signals.
- Client must unwrap common response shapes such as {"data": [...]}.
- If API pagination is supported, fetch pages until max_raw_signals or no next page.
- If pagination docs are unavailable, implement first-page-only and mark TODO clearly.
- Client must never expose raw transport exceptions to callers.
- Client must raise SocialScannerError subclasses.
- Client must not log API keys, auth headers, or secrets.
```

Suggested pagination behavior:

```text
- support next_page_token if present
- support page/per_page if configured
- enforce max_raw_signals
```

---

## 9. Schema-Backed Report Generation

### Issue

The PRDs describe report sections, but implementation must avoid directly writing unstructured LLM blobs.

### Required Update

Require:

```text
- LLM/research output must be parsed into ResearchReport schema before Markdown rendering.
- Markdown should be rendered from ResearchReport fields.
- JSON report should be serialized from the same ResearchReport object.
- If parsing fails, write fallback error report and mark partial_failure or research_failed.
```

Temporary fallback is allowed only if existing TradingAgents cannot emit structured output yet:

```text
- store raw model output in raw_research_output field
- still populate required report fields with best-effort placeholders
- mark structured_parse_status = failed
```

---

## 10. Config and Dependency Rules

### Issue

The PRDs mention YAML and environment variables, but dependency behavior is not specified.

### Required Update

Add:

```text
- Do not add heavy dependencies unless necessary.
- Prefer existing repo config loader if present.
- If PyYAML is not already available, either use the existing config mechanism or add PyYAML explicitly with tests.
- Environment placeholders like ${SOCIAL_SCANNER_BASE_URL} must resolve from os.environ.
- Missing required env vars fail clearly unless mock mode is enabled.
- Config validation errors must produce status=config_error.
```

Config loader should validate:

```text
- archive base path
- scanner base URL unless mock mode
- max_reports > 0
- min_candidate_score within 0-100
- research_depth in fast|standard|full
- scanner_window non-empty
```

---

## 11. Structured Logging and Observability

### Issue

The PRDs do not specify logs.

### Required Update

Use structured logging with these fields where possible:

```text
run_id
mode=daily|manual
ticker
candidate_id
stage
status
elapsed_ms
```

Log events:

```text
run_started
config_loaded
entity_resolved
scanner_fetch_started
scanner_fetch_completed
signals_normalized
candidates_built
candidates_ranked
research_started
research_completed
archive_written
run_completed
run_failed
```

Never log:

```text
API keys
Authorization headers
raw secrets
full private payloads unless debug mode explicitly enabled
```

---

## 12. Institutional Gates Need Fallback Behavior

### Issue

The main PRD calls for materiality, evidence quality, price assimilation, catalyst, and tradability gates. It should also specify how to behave when required data is unavailable.

### Required Update

For unavailable data:

```text
- Use null for unknown raw fields.
- Use conservative default scores.
- Add explicit reason strings.
- Do not crash candidate scoring.
```

Example:

```json
{
  "market_cap": null,
  "tradability_gate_passed": false,
  "tradability_reason": "Market cap unavailable; conservative tradability score applied."
}
```

Do not hallucinate values for missing market or social data.

---

## 13. Manual Synthetic Candidate Contract

### Issue

Manual mode says create a synthetic candidate, but not exactly how.

### Required Update

If social trigger exists:

```text
signal_type = manual_inquiry_with_social_trigger
source_signal_ids = matching scanner signal IDs
```

If no social trigger exists:

```json
{
  "candidate_id": "manual_GOOGL_2026-05-11_143022",
  "ticker": "GOOGL",
  "company_name": "Alphabet Inc.",
  "dominant_narrative": "manual_inquiry",
  "direction": "neutral",
  "signal_type": "manual_inquiry_no_social_trigger",
  "source_signal_ids": [],
  "candidate_score": null,
  "selection_rationale": "Manual inquiry requested by user; no strong Social Scanner trigger found."
}
```

Do not fake ranked-signal scores for manual no-trigger reports.

---

## 14. Scheduled Candidate Selection Contract

### Issue

The main PRD defines ranking weights, but not enough about tie-breaking and fallback behavior.

### Required Update

Tie-break order:

```text
1. higher candidate_score
2. higher materiality_score
3. higher evidence_quality_score
4. lower already_priced_score
5. higher tradability_score
6. alphabetical ticker for deterministic final tie-break
```

If fewer than max_reports pass threshold:

```text
- include watchlist-grade candidates only if configured
- mark watchlist_grade=true
- disclose in summary.md
```

If zero candidates:

```text
- status=skipped_no_candidates
- still write run_metadata.json, raw_signals.json, normalized_signals.json, candidates_ranked.json, summary.md
```

---

## 15. Testing Matrix

### Issue

The PRDs list some tests, but not the minimum no-network acceptance matrix.

### Required Update

Minimum tests:

```text
test_config_loader_env_expansion.py
test_social_scanner_client_mock.py
test_social_scanner_client_response_validation.py
test_signal_normalizer.py
test_candidate_builder.py
test_institutional_gates.py
test_candidate_scorer.py
test_candidate_selector.py
test_entity_resolver.py
test_manual_candidate_factory.py
test_archive_writer_idempotency.py
test_report_writer_schema.py
test_daily_signal_research_book_dry_run.py
test_manual_research_report_dry_run.py
```

CI-safe tests must not require:

```text
- real Social Scanner API
- LLM API keys
- market data API keys
- news API keys
```

---

## 16. CLI Acceptance Examples

### Daily dry run

```bash
python -m tradingagents.jobs.daily_signal_research_book \
  --config ./configs/daily_signal_research_book.yaml \
  --mock \
  --dry-run
```

Expected:

```text
research_archive/daily/YYYY-MM-DD/run_001/summary.md
```

### Manual dry run

```bash
python -m tradingagents.jobs.manual_research_report \
  --query "Google" \
  --config ./configs/daily_signal_research_book.yaml \
  --mock \
  --dry-run
```

Expected:

```text
research_archive/manual/YYYY-MM-DD/HHMMSS_GOOGL_google/report.md
```

### Manual explicit ticker

```bash
python -m tradingagents.jobs.manual_research_report \
  --ticker GOOGL \
  --company "Alphabet Inc." \
  --config ./configs/daily_signal_research_book.yaml
```

---

## 17. Documentation Gaps

The PRDs should include a concise implementation roadmap:

```text
Milestone 1: config, models, archive writer, dry-run fixtures
Milestone 2: scanner client and normalization
Milestone 3: gates, scoring, candidate selection
Milestone 4: report schema and report writer
Milestone 5: integrate TradingAgents research runner
Milestone 6: manual inquiry mode
Milestone 7: tests and CLI polish
```

This sequencing minimizes risk by proving the pipeline before adding LLM/research complexity.

---

## Final Recommendation

Before coding, update the PRDs with the engineering requirements above. The product idea is solid, but implementation needs stricter contracts.

Most important changes:

```text
1. Standardize canonical naming.
2. Define one shared pipeline for daily and manual modes.
3. Add request/result schemas.
4. Require idempotent run folders.
5. Define status enum and error objects.
6. Define no-network dry-run behavior.
7. Require scanner response validation and pagination handling.
8. Require schema-backed reports, not raw LLM blobs.
9. Add structured logging.
10. Add a CI-safe test matrix.
```

If these are added, Codex should be able to implement the feature with far less ambiguity and much lower risk of producing a brittle one-off script.
