# Backlog: Signal-Driven Research Workflows

## Prioritization

- `P0`: required for MVP
- `P1`: strongly recommended after MVP foundation lands
- `P2`: useful follow-up improvements

## P0

### BG-001: Add shared workflow models

- Priority: `P0`
- Goal: define request/result and core domain models for daily and manual workflows
- Target modules:
  - `tradingagents/research/models.py`
  - `tradingagents/research/serialization.py`
- Scope:
  - add request models for daily and manual runs
  - add normalized signal, research candidate, resolved entity, report, and run result models
  - ensure deterministic JSON serialization
- Acceptance criteria:
  - models serialize to primitive JSON-compatible values
  - serialization does not leak exceptions or secrets
  - test fixtures can round-trip cleanly
- Dependencies: none

### BG-002: Add job config loader

- Priority: `P0`
- Goal: load `DEFAULT_CONFIG` plus optional file overlay plus CLI overrides
- Target modules:
  - `tradingagents/research/config_loader.py`
- Scope:
  - load base config from [`tradingagents/default_config.py`](../../tradingagents/default_config.py)
  - support optional config file
  - support env placeholder expansion such as `${SOCIAL_SCANNER_BASE_URL}`
  - keep YAML optional if dependency cost is undesirable
- Acceptance criteria:
  - no config file is required for MVP
  - CLI overrides take highest precedence
  - tests cover precedence and placeholder expansion
- Dependencies:
  - BG-001

### BG-003: Add Social Scanner client interface and mock implementation

- Priority: `P0`
- Goal: support fixture-backed scanner ingestion before real HTTP integration
- Target modules:
  - `tradingagents/integrations/social_scanner_client.py`
  - `tests/fixtures/`
- Scope:
  - define scanner client protocol or abstract base
  - implement mock client reading local fixtures
  - normalize supported raw response shapes into internal signal models
- Acceptance criteria:
  - fixture-backed client works without network
  - raw payload and normalized output are both available to workflow code
  - tests cover array and wrapped `{"data": [...]}` response shapes
- Dependencies:
  - BG-001

### BG-004: Add archive writer

- Priority: `P0`
- Goal: create deterministic daily and manual archive layouts
- Target modules:
  - `tradingagents/archive/archive_writer.py`
- Scope:
  - create run-specific folders
  - write JSON and markdown artifacts
  - implement idempotent folder naming and collision handling
- Acceptance criteria:
  - daily runs use `research_archive/daily/YYYY-MM-DD/run_###/`
  - manual runs use `research_archive/manual/YYYY-MM-DD/HHMMSS_<TICKER>_<slug>/`
  - reruns do not overwrite prior runs unless explicitly allowed
- Dependencies:
  - BG-001

### BG-005: Add daily workflow dry-run job

- Priority: `P0`
- Goal: implement `daily_signal_research_book` dry-run pipeline without LLM calls
- Target modules:
  - `tradingagents/jobs/daily_signal_research_book.py`
  - optional alias `tradingagents/jobs/daily_top5_social_research.py`
  - `tradingagents/research/ranking.py`
- Scope:
  - parse CLI inputs
  - fetch mock signals
  - normalize, deduplicate, group, rank, and select candidates
  - write archive artifacts and summary placeholders
- Acceptance criteria:
  - `--mock --dry-run` succeeds deterministically
  - artifacts include request, metadata, raw signals, normalized signals, ranked candidates, and summary
  - top-N selection respects config inputs
- Dependencies:
  - BG-001
  - BG-002
  - BG-003
  - BG-004

### BG-006: Add entity resolver

- Priority: `P0`
- Goal: resolve manual query inputs deterministically
- Target modules:
  - `tradingagents/research/entity_resolver.py`
  - optional alias map under `configs/` or repo-local data file
- Scope:
  - support ticker-first resolution
  - support query/company alias resolution
  - default `Google -> GOOGL`
  - disclose alternatives and confidence
- Acceptance criteria:
  - exact ticker input is canonical
  - ambiguous matches fail clearly unless best-effort mode is enabled
  - tests cover Google/GOOGL/GOOG policy and ambiguous inputs
- Dependencies:
  - BG-001

### BG-007: Add manual workflow dry-run job

- Priority: `P0`
- Goal: implement `manual_research_report` dry-run pipeline without LLM calls
- Target modules:
  - `tradingagents/jobs/manual_research_report.py`
- Scope:
  - parse `--query`, `--ticker`, `--company`, `--date`
  - resolve entity
  - construct synthetic research candidate
  - fetch mock scanner context when available
  - write manual archive artifacts
- Acceptance criteria:
  - `--mock --dry-run --ticker GOOGL` succeeds deterministically
  - `--mock --dry-run --query "Google"` resolves to `GOOGL`
  - no-signal cases are explicit in outputs
- Dependencies:
  - BG-001
  - BG-002
  - BG-003
  - BG-004
  - BG-006

### BG-008: Add report builder and writers

- Priority: `P0`
- Goal: render PRD-shaped markdown and JSON reports from normalized workflow state
- Target modules:
  - `tradingagents/research/report_builder.py`
- Scope:
  - define `ResearchReport` shape
  - render markdown and JSON outputs
  - use explicit placeholders where current graph output cannot fill required sections
- Acceptance criteria:
  - manual and daily workflows use the same report builder
  - markdown sections are stable and deterministic
  - placeholders are explicit and non-hallucinatory
- Dependencies:
  - BG-001

### BG-009: Add test coverage for dry-run MVP

- Priority: `P0`
- Goal: lock down dry-run behavior before real integrations
- Target modules:
  - `tests/test_*`
- Scope:
  - add unit tests for models, config loader, archive writer, resolver, ranking
  - add workflow tests for daily and manual dry-run entrypoints
- Acceptance criteria:
  - dry-run workflows are covered end-to-end
  - tests do not require network or live model providers
- Dependencies:
  - BG-001 through BG-008

## P1

### BG-010: Add graph-backed SignalResearchRunner

- Priority: `P1`
- Goal: wrap the existing `TradingAgentsGraph` for candidate-level research execution
- Target modules:
  - `tradingagents/research/signal_research_runner.py`
- Scope:
  - run the existing graph with ticker and date
  - capture graph outputs and result paths
  - avoid modifying existing `results_dir` behavior
- Acceptance criteria:
  - a candidate can execute through the graph and return reusable outputs
  - failures surface as structured stage-aware errors
- Dependencies:
  - BG-005
  - BG-007
  - BG-008

### BG-011: Add minimal scanner context injection for research runs

- Priority: `P1`
- Goal: include scanner-derived context in the graph-backed research wrapper
- Target modules:
  - `tradingagents/research/signal_research_runner.py`
  - possible prompt-adjacent helpers
- Scope:
  - prepend or attach limited social context without deep graph rewrite
  - preserve existing graph semantics as much as possible
- Acceptance criteria:
  - injected context is controlled and testable
  - graph integration remains backwards compatible
- Dependencies:
  - BG-010

### BG-012: Add real HTTP Social Scanner client

- Priority: `P1`
- Goal: support configurable live scanner integration
- Target modules:
  - `tradingagents/integrations/social_scanner_client.py`
- Scope:
  - add HTTP implementation
  - configurable endpoints, params, timeout, retries
  - preserve raw payloads
- Acceptance criteria:
  - first-page fetch works for supported response shapes
  - network errors are mapped to structured workflow errors
- Dependencies:
  - BG-003

### BG-013: Add status enums and structured failure artifacts

- Priority: `P1`
- Goal: make workflow state and failure modes explicit
- Target modules:
  - `tradingagents/research/models.py`
  - `tradingagents/archive/archive_writer.py`
- Scope:
  - add stage enum
  - add structured error objects
  - archive partial failures with metadata
- Acceptance criteria:
  - errors include stage, message, and retryability hints where practical
  - archive output remains readable after failures
- Dependencies:
  - BG-001
  - BG-004

### BG-014: Add observability and structured logging

- Priority: `P1`
- Goal: improve debuggability for longer-running workflow jobs
- Target modules:
  - job modules
  - scanner integration
  - runner and archive code
- Scope:
  - consistent run IDs
  - structured stage logging
  - archive references in logs
- Acceptance criteria:
  - logs clearly identify stage transitions and artifact paths
  - failures are actionable without manual code inspection
- Dependencies:
  - BG-010
  - BG-012
  - BG-013

## P2

### BG-015: Add scanner-native analyst integration

- Priority: `P2`
- Goal: move from wrapper-only context injection to first-class scanner-aware analysis
- Scope:
  - augment or replace generic social analyst behavior
  - thread scanner context into analyst prompts and state more directly
- Acceptance criteria:
  - scanner-specific reasoning is visible in analyst outputs
  - prompt changes do not break current graph flow
- Dependencies:
  - BG-011

### BG-016: Add richer ranking and diversity controls

- Priority: `P2`
- Goal: align ranking more closely with PRD diversity and institutional gate rules
- Scope:
  - sector caps
  - dominant narrative diversity
  - signal-type diversity
  - override logic for large score gaps
- Acceptance criteria:
  - ranking decisions are reproducible and explainable
  - tests cover diversity overrides
- Dependencies:
  - BG-005

### BG-017: Add theme-to-multi-candidate manual inquiry support

- Priority: `P2`
- Goal: support manual theme reports beyond single-ticker MVP
- Scope:
  - theme matching
  - candidate shortlist generation
  - optional multi-report output
- Acceptance criteria:
  - multi-candidate results are explicit and bounded
  - archive layout remains understandable
- Dependencies:
  - BG-007
  - BG-012

## Suggested Execution Order

1. BG-001
2. BG-002
3. BG-003
4. BG-004
5. BG-005
6. BG-006
7. BG-007
8. BG-008
9. BG-009
10. BG-010
11. BG-011
12. BG-012
13. BG-013
14. BG-014
15. BG-015
16. BG-016
17. BG-017

## MVP Cut Line

Items required before calling MVP complete:

- BG-001 through BG-009

Items that can land immediately after MVP:

- BG-010 through BG-014
