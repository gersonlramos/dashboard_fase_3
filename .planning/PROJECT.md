# Dashboard Fase 3 — GCP to AWS Migration Tracker

## What This Is

A Streamlit dashboard that gives the migration team real-time visibility into a GCP→AWS migration project tracked in Jira. An automated data pipeline (GitHub Actions + Jira REST API) extracts Epic/Story/Subtask data into CSVs on a schedule, and the dashboard consumes those files to render progress metrics, burndown/burnup charts, SLA tracking, and development cycle analysis across 9 data lakes.

## Core Value

The migration team must always know: **how many items are done, how many remain, and when will it finish** — with a forecast range honest enough to plan around.

## Requirements

### Validated

- ✓ Jira ETL pipeline (3 scripts, GitHub Actions 4×/weekday) — existing
- ✓ Burndown chart with optimistic/pessimistic projections (±30%) — existing
- ✓ Burnup chart with trend lines — existing
- ✓ SLA tracking with business-days calculation — existing
- ✓ Learning curve (sigmoid model per data lake) — existing
- ✓ Development cycle analysis per data lake (9 lakes: BMC, COMPRAS, MOPAR, CLIENTE, SHAREDSERVICES, RH, FINANCE, SUPPLYCHAIN, COMERCIAL) — existing
- ✓ Tab-based layout: Executivo, Gráficos, Detalhes, Pendências — existing
- ✓ Dark/light theme switching — existing
- ✓ Sidebar filters: Data-Lake, Historia, Categoria — existing

### Active

- [ ] Fix deprecated pandas API calls (`fillna(method='ffill')` → `.ffill()`, `applymap` → `map`) — prevents runtime failures on pandas 3.x
- [ ] Add `@st.cache_data` to data loading (`carregar_dados()`, `calcular_ciclo_desenvolvimento()`) — eliminate per-interaction full reloads
- [ ] Test suite for calculation functions (burndown, burnup, SLA, sigmoid, business-days)
- [ ] Test suite for data pipeline (Jira extraction scripts, CSV parsing)
- [ ] Timeline & forecast view: projected end date per epic and overall, optimistic/pessimistic range, velocity trend (accelerating/slowing), milestone markers (cutover dates, phase gates)
- [ ] Migration heatmap: visual grid showing migration status per system/service across all 9 data lakes
- [ ] Visual clarity improvements: better chart labels, hover tooltips, consistent color coding per status/lake

### Out of Scope

- Full monolith refactor (calculations.py, components.py modules) — valuable but disruptive without test coverage first; defer to next milestone
- SSL certificate fix (`verify=False`) — corporate network constraint, accepted risk for now
- Hardcoded config centralization (project keys, epic IDs, Jira URL) — not prioritized by user; defer

## Context

- **Domain:** GCP to AWS migration at scale — Jira project `BF3E4`, 9 business domain epics, 3-level hierarchy (Epic → Story → Subtask)
- **Stack:** Python 3.11, Streamlit 1.55, Plotly 5.24, Pandas 2.2.3, NumPy 2.2.1
- **Data layer:** CSV files in `app/dados/` committed to git by CI — no live database
- **Deployment:** GitHub Codespaces (port 8501), GitHub Actions for automated data refresh
- **Dashboard structure:** Single file `app/dashboard/dashboard.py` (2,351 lines) — monolith, no module separation
- **Known risks from codebase audit:** `FutureWarning` from deprecated pandas API calls (breaks on pandas 3.x), no caching causing slow UX, zero test coverage, `unsafe_allow_html=True` throughout (XSS risk if dashboard ever exposed publicly)

## Constraints

- **Tech:** Python 3.11 + Streamlit — no database, no backend API, CSV-only data layer
- **Deployment:** GitHub Codespaces + GitHub Actions — no separate infra to provision
- **Data source:** Jira project `BF3E4` at `fcagil.atlassian.net` — read-only, credentials via env vars / GitHub Secrets
- **Scope:** Improving existing dashboard — not a rewrite or migration to another framework
- **Testing:** pytest only (no Streamlit integration testing framework) — unit tests for logic, mocked IO for scripts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Tests before refactor | Zero coverage means refactoring is risky; tests come first | — Pending |
| Fix pandas deprecations before new features | Quick win, prevents future breakage, unblocks safer development | — Pending |
| Add caching before new views | New views will add more data loading — fix the root cause first | — Pending |
| Heatmap over other new views | Gives migration-specific insight not available in existing charts | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-25 after initialization*
