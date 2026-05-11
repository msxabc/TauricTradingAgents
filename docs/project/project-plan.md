# Project Plan: Signal-Driven Research Workflows

## Objective

Implement two new research workflows in this forked `TradingAgents` repo:

1. `daily_signal_research_book`
2. `manual_research_report`

The new workflows should wrap the existing single-ticker `TradingAgentsGraph` engine, add Social Scanner ingestion and normalization, generate structured research artifacts, and write deterministic archives under `research_archive/`.

This plan follows:

- [`docs/prd/daily-top5-social-research-agent.md`](../prd/daily-top5-social-research-agent.md)
- [`docs/prd/manual-inquiry-research-mode.md`](../prd/manual-inquiry-research-mode.md)
- [`docs/prd/full-prd-software-engineering-review.md`](../prd/full-prd-software-engineering-review.md)
- [`docs/prd/codex-implementation-decisions.md`](../prd/codex-implementation-decisions.md)

## Current Repo Baseline

The current repo already provides:

- Core analysis engine via [`tradingagents/graph/trading_graph.py`](../../tradingagents/graph/trading_graph.py)
- Default config via [`tradingagents/default_config.py`](../../tradingagents/default_config.py)
- Structured decision schemas via [`tradingagents/agents/schemas.py`](../../tradingagents/agents/schemas.py)
- Interactive CLI via [`cli/main.py`](../../cli/main.py)
- Existing persistence for per-run graph logs and decision memory

The current repo does not yet provide:

- `tradingagents.jobs.*` workflow entrypoints
- Social Scanner client abstraction
- Request/result models for the new workflows
- Entity resolution for manual inquiry
- Research archive writer
- Candidate ranking and selection pipeline
- Report post-processing into PRD institutional report format

## Delivery Strategy

Build the new workflows as a thin orchestration layer around the existing graph first. Avoid graph surgery in MVP.

MVP success criteria:

- Both workflows run in `--mock --dry-run` mode
- No network access or LLM calls are required in dry-run mode
- Archive artifacts are deterministic and schema-shaped
- Manual and daily workflows share core models, config loading, report writing, and archive writing

After dry-run stability, add real HTTP scanner support and graph-backed research execution.

## Architecture Direction

Recommended new modules:

```text
tradingagents/
  jobs/
    daily_signal_research_book.py
    manual_research_report.py
    daily_top5_social_research.py        # optional alias
  research/
    models.py
    serialization.py
    config_loader.py
    entity_resolver.py
    ranking.py
    report_builder.py
    signal_research_runner.py
  integrations/
    social_scanner_client.py
  archive/
    archive_writer.py
```

Recommended archive layout:

```text
research_archive/
  daily/
    YYYY-MM-DD/
      run_001/
  manual/
    YYYY-MM-DD/
      HHMMSS_<TICKER>_<slug>/
```

## Phases

### Phase 1: Foundations

Goal: establish stable contracts before workflow code expands.

Deliverables:

- Shared request/result models for daily and manual workflows
- Deterministic serialization helpers
- Config loader using `DEFAULT_CONFIG` plus optional overlay plus CLI overrides
- Initial test fixtures for dry-run mode

Exit criteria:

- Request/result objects exist and can be serialized without custom cleanup
- Config loading works without YAML and supports env placeholders where applicable

### Phase 2: Archive and Mock Scanner

Goal: make dry-run artifact generation possible.

Deliverables:

- `SocialScannerClient` interface
- Fixture-backed mock scanner implementation
- Archive writer with idempotent run folder behavior
- Daily workflow skeleton that writes request, metadata, raw signals, normalized signals, ranked candidates, and summary placeholders

Exit criteria:

- Daily dry-run command produces deterministic archive output from fixtures
- No network or LLM dependency in dry-run mode

### Phase 3: Manual Workflow and Entity Resolution

Goal: complete the second user-facing workflow on top of shared components.

Deliverables:

- Deterministic entity resolver for ticker/company/query inputs
- Manual workflow job
- Manual synthetic candidate construction
- Manual archive layout and metadata outputs

Exit criteria:

- Manual dry-run command produces deterministic archive output for `--ticker` and `--query`
- Ambiguous inputs fail clearly unless best-effort resolution is explicitly enabled

### Phase 4: Research Runner Integration

Goal: connect workflows to the existing graph without rewriting the graph internals.

Deliverables:

- `SignalResearchRunner` wrapper around `TradingAgentsGraph`
- Minimal context injection strategy for social scanner signal context
- Post-processing from graph outputs into PRD report schema

Exit criteria:

- A selected candidate can run through the existing graph and produce a structured markdown and JSON research report
- Existing `results_dir` behavior remains untouched

### Phase 5: Real Scanner Client and Hardening

Goal: replace fixture-only operation with real integration and production guardrails.

Deliverables:

- HTTP scanner client behind the same interface
- Response normalization hooks
- Error/status model with stage-aware failures
- Logging and observability improvements
- Expanded integration test coverage

Exit criteria:

- Real scanner fetch works with configurable endpoints
- Failure modes are explicit and archived

## Dependencies and Sequencing

Sequence that should be preserved:

1. Shared models and config loader
2. Mock scanner and archive writer
3. Daily dry-run workflow
4. Manual dry-run workflow
5. Graph-backed research runner
6. Real scanner HTTP client
7. Hardening and coverage expansion

Rationale:

- Dry-run mode de-risks interfaces before LLM and API variability enters the system
- Archive output becomes the stable contract early
- The existing graph can be wrapped after upstream request/result boundaries are fixed

## Testing Strategy

Unit tests should cover:

- config loading and override precedence
- serialization stability
- archive writer idempotency
- scanner response normalization
- entity resolution
- ranking logic
- report builder placeholder behavior

Workflow tests should cover:

- daily dry-run end-to-end
- manual dry-run end-to-end
- graph-backed runner with mocked graph outputs
- scanner client response validation

Testing principle:

- MVP tests should prefer deterministic fixtures and mocked graph responses over live LLM or HTTP execution

## Risks

### Risk 1: Graph input surface is too narrow

Current graph only accepts `company_name` and `trade_date`.

Mitigation:

- keep scanner context injection outside the graph first
- treat report-building as a wrapper concern in MVP

### Risk 2: Scanner API contract is unstable

Mitigation:

- isolate behind client interface
- preserve raw payloads in archive
- validate only the normalized contract required by the workflows

### Risk 3: Config sprawl

Mitigation:

- reuse `DEFAULT_CONFIG`
- isolate new options in a job-specific namespace
- keep YAML overlay optional

### Risk 4: Report completeness mismatch

Current graph outputs do not map perfectly to the PRD’s 19-section format.

Mitigation:

- use explicit placeholders instead of inference
- treat native structured report generation as later enhancement

## Out of Scope for MVP

- broker integration
- autonomous execution
- backtesting engine
- dashboard UI
- first-class graph refactor for scanner-native analyst prompts
- multi-company manual theme reports

## Definition of Done

The project is complete for MVP when:

- `daily_signal_research_book` runs in dry-run mode and writes deterministic daily archives
- `manual_research_report` runs in dry-run mode and writes deterministic manual archives
- both workflows share common models, config loading, archive writing, and report generation code
- graph-backed research execution works behind a wrapper without breaking current repo behavior
- tests cover the new contracts at unit and workflow level
