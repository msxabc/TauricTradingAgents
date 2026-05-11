# Codex Implementation Decisions: Signal-Driven Research Agent

This document answers implementation questions that affect module boundaries, testability, and compatibility with the existing TradingAgents codebase.

## 1. Canonical naming

Use the newer naming scheme as canonical.

```text
Scheduled workflow/job:
daily_signal_research_book

Manual workflow/job:
manual_research_report

Shared config:
configs/daily_signal_research_book.yaml

Daily archive root:
research_archive/daily/

Manual archive root:
research_archive/manual/
```

Backward-compatible aliases are acceptable but not required for MVP. If aliases are cheap, add:

```text
tradingagents.jobs.daily_top5_social_research -> delegates to daily_signal_research_book
```

Internally, use `daily_signal_research_book` everywhere.

---

## 2. TradingAgents graph integration strategy

MVP should wrap the existing graph largely as-is first, then inject Social Scanner context through a controlled prompt/context layer.

Do not perform a deep graph rewrite as the first milestone.

Recommended sequence:

### Milestone 1

```text
- Build scanner client, models, ranking, archive, dry-run pipeline.
- Add SignalResearchRunner wrapper around the existing TradingAgentsGraph.
- Pass ticker/company/date as existing graph expects.
- Add social/institutional context to the research prompt or preamble where least invasive.
- Post-process existing graph outputs into the PRD report schema.
```

### Milestone 2

```text
- Add first-class social scanner context to analyst prompts.
- Replace/augment the existing generic sentiment/news-backed social analyst with scanner-specific context.
- Add a true Social Scanner analyst node only after the wrapper flow is stable.
```

The graph currently only takes company_name + trade_date, and the existing social/sentiment analyst is not scanner-specific. Do not block MVP on graph surgery. Build the shared pipeline and wrapper first.

---

## 3. Manual inquiry share-class policy

For ambiguous names like Google / Alphabet, MVP should resolve to `GOOGL` unless the user explicitly asks for `GOOG`.

Default:

```text
Google -> Alphabet Inc. -> GOOGL
GOOG -> alternate Alphabet share class
```

Report must disclose:

```text
- original query
- resolved ticker
- resolution rationale
- alternatives, including GOOG where relevant
```

If the user passes `--ticker GOOG`, use GOOG.

---

## 4. YAML config policy

Do not introduce a large parallel config framework.

Use the existing `DEFAULT_CONFIG` + environment-variable approach as the base, and add a small optional YAML overlay for these new jobs only.

Implementation policy:

```text
1. Load DEFAULT_CONFIG from existing TradingAgents config.
2. Load optional YAML file if --config is provided.
3. Merge YAML values into a job-specific config namespace.
4. Apply CLI overrides last.
5. Resolve environment placeholders such as ${SOCIAL_SCANNER_BASE_URL}.
```

If PyYAML is already available, use it. If not, prefer adding a small dependency only if acceptable under existing project dependency style. Otherwise support JSON config first and leave YAML as a TODO.

MVP must work without YAML by using DEFAULT_CONFIG + env vars + CLI flags.

---

## 5. Social Scanner API contract

Treat mock/fixture mode as the first milestone.

The real Social Scanner API contract is not final. Build the HTTP client behind an interface and keep endpoint paths/params configurable.

Implementation order:

```text
1. Implement fixture-backed mock client.
2. Implement SocialScannerClient interface.
3. Implement best-effort HTTP client with configurable endpoints.
4. Add response normalization hooks so the real schema can be mapped later.
```

Do not hardcode assumptions beyond the PRD fields. Preserve raw API payloads in `raw_signals.json`.

The client should support common response shapes:

```json
[{"signal_id": "..."}]
```

and:

```json
{"data": [{"signal_id": "..."}], "next_page_token": null}
```

If pagination is unclear, implement first-page only and leave a clear TODO.

---

## 6. Final report generation strategy

MVP should post-process existing agent outputs into the PRD’s institutional report structure.

Do not require every underlying agent to natively emit the full 19-section report on day one.

Implementation policy:

```text
1. Run existing graph through SignalResearchRunner.
2. Collect existing decision/report outputs.
3. Combine those outputs with social/institutional context.
4. Produce a ResearchReport object with the required fields.
5. Render Markdown and JSON from ResearchReport.
```

Where existing graph output cannot populate a field, use explicit placeholders such as:

```text
Not available from current graph output.
```

or:

```text
No strong Social Scanner trigger was found for this manual inquiry.
```

Do not hallucinate missing fields.

Future improvement:

```text
Update underlying prompts/schema so agents generate structured sections natively.
```

---

## 7. Archive integration with existing results_dir

Keep the new archive system separate from the existing `results_dir` / per-ticker state logs for MVP.

Reason:

```text
- Existing logs belong to the original TradingAgents execution model.
- The new archive is a user-facing research book and audit artifact.
- Mixing them would create fragile coupling and migration risk.
```

Policy:

```text
- Do not remove or rewrite existing results_dir behavior.
- New jobs write to research_archive/daily/ and research_archive/manual/.
- Where useful, include references to existing TradingAgents output paths in run_metadata.json.
- Do not fold existing state logs into the new archive in MVP.
```

Future work may copy or link selected existing outputs into the research archive.

---

## Implementation priority

Build in this order:

```text
1. Models and serialization helpers.
2. Config loader with DEFAULT_CONFIG + optional YAML/JSON overlay + CLI overrides.
3. Mock Social Scanner client and fixtures.
4. Archive writer with idempotent run folders.
5. Daily dry-run pipeline.
6. Manual dry-run pipeline.
7. Real HTTP Social Scanner client behind interface.
8. SignalResearchRunner wrapper around existing TradingAgentsGraph.
9. Report post-processor and Markdown/JSON writers.
10. Tests.
```

MVP success criterion:

```text
Both commands work with --mock --dry-run and produce deterministic archive artifacts without network or LLM calls.
```

Then implement full research runs against the existing graph.
