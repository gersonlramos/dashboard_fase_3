# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** The migration team must always know how many items are done, how many remain, and when it will finish — with a forecast range honest enough to plan around.
**Current focus:** Phase 3 — Extract Calculations Module

## Current Position

Phase: 2 of 6 (Performance) — COMPLETE
Plan: 2 of 2 completed
Status: Phase complete — ready for Phase 3
Last activity: 2026-03-26 — Phase 2 executed: cache decorators + refresh button + orjson

Progress: [████░░░░░░] 33% (phases 1-2/6 done)

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: —
- Total execution time: <1 hour

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 1 | 4 | <1h | — |

**Recent Trend:**
- Last 5 plans: 01-01, 01-02, 01-03, 01-04, 02-01, 02-02
- Trend: all completed across two sessions

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 1 must come before Phase 3: `filterwarnings = error::FutureWarning` in pytest.ini will fail the test run if deprecated API calls are still present.
- Phase 2 must come before Phases 5 and 6: new views add more CSV reads; caching must be in place first.
- Do not import `dashboard.py` directly in tests — it runs Streamlit at import time; extract pure functions to `calculations.py` first.

### Pending Todos

None yet.

### Blockers/Concerns

- Installed pandas (2.1.4) differs from pinned version (2.2.3); verify deployment target before any upgrade path during Phase 1.
- `calcular_ciclo_ideal` reads module-level `df_lake` — flag during Phase 3 extraction; may need to pass `df_lake` as a parameter instead of extracting verbatim.
- As of 2026-03-25 only COMPRAS has meaningful Done counts; Monte Carlo in Phase 6 will fall back to ±30% linear projection for most lakes — display this limitation clearly to users.

## Session Continuity

Last session: 2026-03-25
Stopped at: Roadmap and STATE.md initialized; no plans executed yet.
Resume file: None

### Technique Notes

-  semantics: use shifted bounds  to match the while-loop's exclusive-start / inclusive-end counting.
- Dashboard.py cannot be imported in tests (Streamlit runs set_page_config at module scope). Reproduce logic inline in test functions.
