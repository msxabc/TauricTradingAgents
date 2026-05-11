# PRD Supplement: Manual Inquiry Research Mode

## Objective

The signal-driven research agent must support both automated daily top-candidate runs and manual user-triggered research inquiries.

A user should be able to ask for a report on a specific company, ticker, or theme, for example:

```text
Do a report on Google.
```

The agent should resolve the inquiry to the appropriate ticker/entity, gather the same research inputs used by the daily workflow, run the same signal-aware/institutional research process where applicable, and produce a final archived research report.

Manual inquiry mode must be additive. It should not replace the scheduled daily research book workflow.

---

## User Stories

### Manual company/ticker report

As a user, I can ask:

```text
Do a report on Google.
```

The system should:

1. Resolve `Google` to Alphabet / `GOOGL` or `GOOG`.
2. Fetch relevant social scanner data for the resolved ticker.
3. Fetch available market, news, technical, and risk context through existing TradingAgents tooling.
4. Run the institutional research report workflow.
5. Produce a Markdown and JSON report.
6. Archive the report in a manual inquiry folder.

### Manual signal-specific report

As a user, I can ask:

```text
Do a report on SMCI accounting risk.
```

The system should:

1. Resolve `SMCI`.
2. Query the Social Scanner for related narratives/signals around `accounting risk`.
3. Use matching scanner signals as trigger context.
4. Produce a signal-aware institutional research report.

### Manual theme report

As a user, I can ask:

```text
Do a report on AI server demand winners.
```

The system may:

1. Search Social Scanner signals/narratives for relevant companies.
2. Select the best matching ticker/entity or multiple candidates if supported.
3. Produce either a single-company report or a short candidate list, depending on implementation scope.

For MVP, single-company/ticker reports are required. Multi-company theme reports are optional.

---

## Required Manual Mode Entry Points

Implement at least one CLI entrypoint:

```bash
python -m tradingagents.jobs.manual_research_report \
  --query "Google" \
  --config ./configs/daily_signal_research_book.yaml
```

Also support explicit ticker mode:

```bash
python -m tradingagents.jobs.manual_research_report \
  --ticker GOOGL \
  --config ./configs/daily_signal_research_book.yaml
```

Recommended optional flags:

```text
--company "Alphabet"
--date YYYY-MM-DD
--scanner-window 24h
--research-depth fast|standard|full
--archive-path PATH
--mock
--dry-run
```

---

## Entity Resolution Requirements

Manual inquiry mode must include an entity resolution step.

Examples:

```text
Google -> Alphabet Inc. -> GOOGL/GOOG
Meta -> Meta Platforms -> META
Tesla -> Tesla Inc. -> TSLA
Apple -> Apple Inc. -> AAPL
```

If a query maps to multiple tickers, use a deterministic default where obvious and include the mapping rationale in the report.

For ambiguous cases, the CLI may either:

1. choose the highest-confidence public equity match and disclose the mapping, or
2. return a clear ambiguity error listing possible tickers.

Do not silently produce a report for an uncertain entity without disclosing the mapping.

Recommended module:

```text
tradingagents/research/entity_resolver.py
```

Recommended interface:

```python
@dataclass
class ResolvedEntity:
    query: str
    ticker: str
    company_name: str | None
    confidence: float
    rationale: str
    alternatives: list[dict]

class EntityResolver:
    def resolve(self, query: str) -> ResolvedEntity:
        ...
```

---

## Manual Research Context

Manual mode should create a synthetic research candidate object compatible with the daily signal research runner.

If Social Scanner returns relevant signals for the ticker/query, the synthetic candidate should include:

```text
- ticker
- company name
- matching social signals
- dominant narrative if found
- evidence tier
- materiality score
- catalyst clock if inferable
- price assimilation fields if available
```

If no social signal is found, the agent should still produce a report, but explicitly state:

```text
No strong Social Scanner trigger was found for this manual inquiry.
```

In that case, the report should be framed as a manual institutional research report rather than a signal-triggered report.

---

## Manual Report Output

Manual reports should use the same institutional report structure as the daily research book reports, including:

```text
1. Executive summary
2. Query/entity mapping
3. Why this report was requested
4. Trigger signal, if any
5. Materiality assessment
6. Variant view
7. Social/narrative analysis
8. Evidence quality and source hierarchy
9. Price assimilation / what is already priced
10. Market/technical context
11. News/fundamental verification
12. Catalyst clock
13. Bull case
14. Bear case
15. Possible trade expressions
16. Key risks
17. Invalidation conditions
18. Monitoring plan
19. Evidence appendix
```

Manual reports must include:

```text
- original user query
- resolved ticker/entity
- entity resolution confidence
- whether a Social Scanner trigger was found
- research-only disclaimer
```

---

## Manual Archive Structure

Manual inquiry reports should be archived separately from scheduled daily books.

Recommended structure:

```text
research_archive/
  manual/
    2026-05-11/
      GOOGL_google_manual_report.md
      GOOGL_google_manual_report.json
      run_metadata.json
```

If multiple manual reports are generated on the same day for the same ticker, append a timestamp or run suffix:

```text
GOOGL_google_manual_report_143022.md
```

---

## Shared Code Requirement

Manual mode must reuse the same core research pipeline as the daily signal research book wherever possible.

Do not create a totally separate report generator.

Shared components should include:

```text
- SocialScannerClient
- EntityResolver, where applicable
- institutional gates
- SignalResearchRunner or equivalent research runner
- report schema
- report writer
- archive writer
```

Manual mode may create a synthetic `ResearchCandidate` when no daily scanner signal exists.

---

## Acceptance Criteria

Manual inquiry mode is complete when:

```text
1. User can run a CLI command with --query "Google".
2. The system resolves Google to Alphabet / GOOGL or GOOGL/GOOG with disclosed rationale.
3. The system fetches Social Scanner data for the resolved ticker when available.
4. The system still produces a report even if no strong social trigger is found.
5. The output report follows the same institutional report structure as daily reports.
6. The report includes original query, resolved ticker, entity resolution confidence, and social-trigger status.
7. The report is archived under research_archive/manual/YYYY-MM-DD/.
8. Manual mode reuses the same core research/reporting components as the daily research book.
9. --mock and --dry-run modes work without external services.
```

---

## Example Command

```bash
python -m tradingagents.jobs.manual_research_report \
  --query "Google" \
  --scanner-window 24h \
  --research-depth standard \
  --config ./configs/daily_signal_research_book.yaml
```

Expected output:

```text
research_archive/manual/2026-05-11/GOOGL_google_manual_report.md
```

---

## Final Guidance for Codex

Manual inquiry mode should make the research agent useful outside scheduled runs.

The user should be able to ask for a report on a company, ticker, or narrow narrative and receive the same quality of institutional research output produced by the daily research book.

The scheduled workflow answers:

```text
What are the top 5 things I should review today?
```

Manual inquiry mode answers:

```text
I already know what I want to review. Produce the full report now.
```
