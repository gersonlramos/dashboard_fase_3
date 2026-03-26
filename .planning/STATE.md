# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** The migration team must always know how many items are done, how many remain, and when it will finish — with a forecast range honest enough to plan around.
**Current focus:** Phase 1 — Correctness Fixes

## Current Position

Phase: 1 of 6 (Correctness Fixes)
Plan: 0 of 4 in current phase
Status: Ready to plan
Last activity: 2026-03-25 — Roadmap created, STATE.md initialized

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

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
