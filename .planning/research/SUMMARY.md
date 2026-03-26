# Research Summary

**Synthesized:** 2026-03-25
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md, PROJECT.md
**Overall Confidence:** HIGH — all four research areas backed by official docs and direct codebase verification

---

## Project Goal

A Streamlit dashboard giving a GCP→AWS migration team real-time visibility into Jira-tracked progress across 9 data lakes, with the core question always answered: how many items are done, how many remain, and when will it finish — with a forecast range honest enough to plan around. The active work adds test coverage, fixes correctness hazards, and extends the dashboard with a migration heatmap and probabilistic forecast view.

---

## Key Technical Decisions

### Confirmed Stack (all verified in the actual environment)

| Tool | Installed Version | Requirement Version | Notes |
|------|------------------|---------------------|-------|
| Python | 3.12.5 | 3.11+ | Confirmed working |
| Streamlit | 1.55.0 | 1.55 | AppTest importable and functional |
| pandas | 2.1.4 | 2.2.3 (pinned) | Mismatch — deprecated APIs are FutureWarning in both |
| numpy | 1.26.4 | 2.2.1 (pinned) | Mismatch — no impact on current work |
| pytest | 8.4.1 | — | Installed, ready |
| responses | 0.25.7 | — | Installed, covers HTTP mocking needs |

**The installed versions differ from requirements.txt pins.** The deprecated API fixes (`ffill`, `map`) are valid for both the installed and pinned versions.

### Architecture: Do Not Refactor, Extend

The 2,351-line `app/dashboard/dashboard.py` monolith runs Streamlit calls at module top level. The correct extension pattern — confirmed by direct codebase analysis — is:

1. Extract pure calculation functions to `app/dashboard/calculations.py` (enables unit testing without touching Streamlit)
2. Add new views as `elif` branches at the END of the existing `aba_selecionada` radio chain
3. Define new render helpers in the existing `# Funções de renderização de tabelas` block (~line 1168)
4. Never move existing code as part of adding a new view

### Testing Strategy: Two Layers, Not AppTest-First

- **Layer 1 (primary):** Pure pytest unit tests on extracted calculation functions — no Streamlit runtime needed
- **Layer 2 (smoke only):** One `AppTest.from_file()` test that verifies the app loads without exceptions
- AppTest cannot inspect Plotly chart contents — chart correctness requires manual verification
- `pytest-mock` is NOT needed — `unittest.mock` + `monkeypatch` covers all mocking requirements

### New Chart Approaches (confirmed against official docs)

- **Migration heatmap:** `px.imshow()` on a `(9 lakes × 5 status buckets)` percentage matrix — preferred over deprecated `ff.create_annotated_heatmap`
- **Forecast bands:** `go.Scatter` with `fill='tonexty'` between P50 and P85 Monte Carlo percentiles
- **Milestone markers:** `add_vline` with date strings (not Timestamps) on timeline x-axis
- **Velocity trend:** Rolling 7-day and 14-day means on `burn_real`, displayed on secondary y-axis via `yaxis2`

---

## Implementation Sequence (Critical Path)

Dependencies flow strictly in this order. Starting on phases 3–4 before phase 1 is complete creates correctness and performance risk.

### Phase 1: Deprecation Fixes (unblocks everything)
**Must come first.** Two confirmed broken calls will raise `TypeError` on pandas 3.0. With `filterwarnings = error::FutureWarning` in pytest.ini, these also block the test suite.

1. `dashboard.py:48` — `fillna(method='ffill')` → `.ffill()`
2. `dashboard.py:1214` — `style.applymap(colorir_status)` → `style.map(colorir_status)`
3. `dashboard.py:2158–2171` — `while` loop in `dias_uteis_restantes()` → `np.busday_count()`
4. `dashboard.py:536` — bare `except:` in `parse_data_criacao()` → `except (ValueError, TypeError)`
5. `dashboard.py:1912` — `df_filtrado['Historia']` → guard with `if 'Historia' in df_filtrado.columns:`

**Dependency:** None. Start immediately.

### Phase 2: Caching (unblocks new views)
**Must come before adding new views.** New views add more CSV reads. Without caching, each new view worsens the UX regression on every user interaction.

1. Add `@st.cache_data(ttl=900)` to `carregar_dados()` at line 383
2. Add `@st.cache_data(ttl=900)` to `calcular_ciclo_desenvolvimento()` at line 609 (or extract its disk-read portion to a separately cached function)
3. Add `orjson` to `requirements.txt` — no code changes, 8× chart serialization speedup

**Dependency:** Phase 1 complete (clean state before adding decorators)

### Phase 3: Test Suite (unblocks safe refactoring)
**Must come before new feature extraction.** The chicken-and-egg problem: extraction is needed for tests, but tests are needed before extraction. Resolution: extract only the pure functions, write tests, do not touch UI code.

1. Create `app/dashboard/calculations.py` — move these functions verbatim, no signature changes:
   - `calcular_dias_uteis`, `calcular_curva_aprendizado`, `normalizar_id_historia`, `carregar_dados`, `colorir_status`
2. Add one import line to `dashboard.py` pulling from `calculations.py`
3. Create `tests/` directory at project root with `conftest.py`, fixture CSVs, `pytest.ini`
4. Write unit tests: `test_calculations.py`, `test_etl_atualizacao.py`, `test_etl_pendencias.py`
5. Write smoke test: `test_app_smoke.py` with `AppTest` — verifies app loads, no exceptions
6. `pytest.ini` must include `filterwarnings = error::FutureWarning` to gate deprecated API re-introduction

**Dependency:** Phase 1 (FutureWarning must not block the test run)

### Phase 4: Migration Heatmap
**Additive feature.** No existing code touched except the radio list and a new `elif` branch.

1. Add `"Heatmap"` to sidebar radio list (append to end)
2. Write `_render_heatmap(df_base)` function in the render helpers block
3. Data transform: pivot FASE_3.csv by (Data-Lake, status bucket), normalize to percentage
4. Chart: `px.imshow()` with `text_auto=".0f"`, discrete colorscale, `template=plotly_template`
5. Add `st.metric` row above the heatmap (Done%, In Progress count, Backlog count)

**Data dependency:** Only FASE_3.csv — already loaded as `df`. No new files needed.
**Phase dependency:** Phase 2 (caching in place before adding another view that reads the same CSV)

### Phase 5: Timeline and Forecast View
**Most complex feature.** Requires Monte Carlo calculation, milestone data, and graceful degradation when throughput data is sparse (most lakes have 0 Done items as of 2026-03-25).

1. Add `"Previsao"` to sidebar radio list (append to end)
2. Write `monte_carlo_forecast(daily_throughput, remaining, n_simulations=5000)` — returns P50, P70, P85, P95 day offsets
3. Implement graceful degradation: if `len(burn_real) < 3`, skip Monte Carlo, show existing ±30% linear projection
4. Build forecast band: P85 invisible upper trace + P50 lower trace with `fill='tonexty'`
5. Add milestone markers: read `datas_esperadas_por_lake.csv`, derive max `data_fim` per lake, call `add_vline` for each
6. Add rolling velocity: 7-day and 14-day means on `burn_real`, secondary y-axis
7. Add `st.metric` cards: Central Forecast (P50), Conservative Forecast (P85), velocity delta

**Data dependency:** `datas_esperadas_por_lake.csv` (already loaded as `lakes_fase`) and `burn_real_acum` (already computed in burndown section).
**Phase dependency:** Phase 3 (tests must cover `monte_carlo_forecast` before it ships)

---

## Confirmed Approaches

### Pandas Deprecation Fixes (exact replacements, verified in project environment)

```python
# dashboard.py:48 — inside calcular_curva_aprendizado()
# BEFORE
valores_plan_interp = df_interpolado['valor'].fillna(method='ffill').fillna(0).tolist()
# AFTER
valores_plan_interp = df_interpolado['valor'].ffill().fillna(0).tolist()

# dashboard.py:1214 — inside table rendering
# BEFORE
df_render.style.applymap(colorir_status, subset=['Status'])
# AFTER
df_render.style.map(colorir_status, subset=['Status'])
```

### Cache Decorator Pattern

```python
@st.cache_data(ttl=900)   # 15 min matches CI update interval (4×/weekday)
def carregar_dados(arquivo):
    ...

@st.cache_data(ttl=900)
def calcular_ciclo_desenvolvimento(data_lake_filtro='Todos'):
    ...
```

Each unique `data_lake_filtro` value is a separate cache entry — correct behavior.

### pytest.ini (complete)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short -m "not integration"
filterwarnings =
    error::FutureWarning
    ignore::urllib3.exceptions.InsecureRequestWarning
```

### Heatmap Data Transform

```python
STATUS_BUCKET = {
    "Open": "Backlog", "To Do": "Backlog",
    "In progress": "Em andamento", "In Test": "Em andamento", "Waiting Test": "Em andamento",
    "Done": "Concluido", "Canceled": "Cancelado",
}
df["bucket"] = df["Status"].map(STATUS_BUCKET).fillna("Outro")
pivot = df.groupby(["Data-Lake", "bucket"]).size().unstack(fill_value=0)
pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
# pct is a (9 lakes x 5 buckets) DataFrame, 0–100 float — feeds px.imshow() directly
```

### AppTest Pattern (smoke test only)

```python
from streamlit.testing.v1 import AppTest

def test_app_loads_without_exception():
    at = AppTest.from_file("app/dashboard/dashboard.py", default_timeout=30)
    at.run()
    assert not at.exception

import streamlit as st
import pytest

@pytest.fixture(autouse=True)
def clear_st_cache():
    yield
    st.cache_data.clear()   # prevents cache contamination between AppTest instances
```

### ETL Script Mocking (no extra dependencies)

```python
# Patch requests.get at the point of use
with patch("script_atualizacao.requests.get") as mock_get:
    mock_get.return_value = _make_response(fake_issues, is_last=True)
    result = buscar_com_paginacao("project=X", "key,summary", auth=None)
```

### Monte Carlo Forecast

```python
def monte_carlo_forecast(daily_throughput, remaining, n_simulations=5000, seed=42):
    rng = np.random.default_rng(seed)
    if len(daily_throughput) < 3:
        return None   # fall back to linear ±30% projection
    results = []
    for _ in range(n_simulations):
        days, completed = 0, 0
        while completed < remaining:
            completed += max(0, rng.choice(daily_throughput))
            days += 1
            if days > 730: break
        results.append(days)
    arr = np.array(results)
    return {"p50": int(np.percentile(arr, 50)), "p85": int(np.percentile(arr, 85))}
```

---

## Risks and Mitigations

### Risk 1: Pandas 3.x Runtime Failures (CRITICAL)
**What:** `fillna(method='ffill')` raises `TypeError` on pandas 3.0; `style.applymap()` raises `AttributeError`. Both confirmed present in dashboard.py.
**When it hits:** Any pandas upgrade, or if the deployed environment moves to pandas 3.x.
**Mitigation:** Phase 1 fixes both — 30 minutes total effort. Add `filterwarnings = error::FutureWarning` in pytest.ini to prevent regression.

### Risk 2: 9 CSV Disk Reads on Every User Interaction (HIGH)
**What:** `calcular_ciclo_desenvolvimento()` reads 9 history CSVs and `carregar_dados()` reads FASE_3.csv with no caching. Every sidebar filter change or tab switch triggers full re-execution.
**Impact:** 1–3 second latency on each interaction; gets worse as new views are added.
**Mitigation:** `@st.cache_data(ttl=900)` on both functions — Phase 2, ~1 hour effort. Expected result: interaction latency drops from seconds to milliseconds.

### Risk 3: Monolith Import Blocks Test Suite (HIGH)
**What:** `dashboard.py` executes `st.set_page_config`, CSV loads, and chart logic at module top level. Importing it in tests triggers failures or Streamlit session errors.
**Mitigation:** Extract pure functions to `calculations.py` first (Phase 3 step 1). Alternatively, use `sys.modules` mock to stub Streamlit before import — valid interim approach.

### Risk 4: Sparse Throughput Data Breaks Forecast (MEDIUM)
**What:** As of 2026-03-25, only COMPRAS has meaningful Done counts. BMC has 0 Done items. Monte Carlo sampling from an empty or near-empty throughput list produces nonsense.
**Mitigation:** Explicit guard: `if len(daily_throughput) < 3: return None`. Fall back to the existing ±30% linear projection. Display `st.info()` explaining the limitation.

### Risk 5: Cache Contamination in AppTest (MEDIUM)
**What:** `@st.cache_data` persists across `AppTest` instances in the same process (known Streamlit bug #9139). Second test in a sequence sees stale data from the first.
**Mitigation:** `autouse` fixture that calls `st.cache_data.clear()` in teardown — confirmed working pattern.

### Risk 6: `add_vline` Datetime Type Issue (LOW)
**What:** `add_vline` with a Timestamp object on datetime x-axes has a known Plotly bug in some versions — must pass date as a string `"YYYY-MM-DD"`.
**Mitigation:** Always pass milestone dates as strings, not `pd.Timestamp` objects, in the forecast view.

### Risk 7: XSS via `unsafe_allow_html=True` (LOW — current deployment, MEDIUM if ever public)
**What:** Jira issue titles and descriptions rendered through `st.markdown(..., unsafe_allow_html=True)` could execute injected JavaScript if the Codespaces port is made public.
**Mitigation:** Wrap all Jira-sourced variables in `html.escape()` before embedding in HTML template strings. ~2 hours effort, one-time fix.

---

## What NOT to Do

### Architecture
- Do not move existing view code to "clean it up" while adding a new view — each code movement is a potential regression
- Do not introduce `st.tabs()` as a navigation replacement — users are accustomed to the sidebar radio pattern; `st.tabs()` is acceptable only within a single view's scope
- Do not import `dashboard.py` directly in tests — it runs Streamlit at import time
- Do not add `__init__.py` to `tests/` — this causes import confusion with pytest's import mode

### Caching
- Do not use `@st.cache_resource` for DataFrames — it returns the same mutable object to all callers, enabling cache corruption
- Do not combine `ttl` with `persist="disk"` — TTL is silently ignored when disk persistence is active
- Do not cache functions that contain `st.*` calls — those calls are suppressed on cache hits

### Charts
- Do not use `ff.create_annotated_heatmap` — deprecated; `px.imshow()` is the current recommendation
- Do not use pastel table colors (`#90EE90`, `#87CEEB`) in the heatmap — they are too light for fill cells; use the saturated palette instead
- Do not render all 127 SHARED SERVICES stories as heatmap columns — the story-level view is unreadable at that scale; use the lake-level bucket summary (9 × 5 matrix)

### Features
- Do not build an interactive backlog editor — the dashboard is read-only; data comes from Jira via CI
- Do not make real-time Jira API calls from the dashboard — CSV-only architecture is a project constraint
- Do not add animation or auto-play timeline — poor UX in a monitoring dashboard, adds complexity without value
- Do not add custom JS components (`st.components.v1`) — requires `unsafe_allow_html` and adds XSS surface

### Testing
- Do not use `pytest-mock` — `unittest.mock` + `monkeypatch` (both stdlib/built-in) cover all needs; no new dependency required
- Do not write integration tests that hit the real Jira API in CI — credentials are unavailable in PR builds, tests become flaky
- Do not use `scope="session"` for DataFrame fixtures — DataFrames are mutable; a mutating test silently corrupts subsequent tests
- Do not use AppTest to verify chart correctness — Plotly charts are opaque to AppTest (`UnknownElement`)

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Stack versions and compatibility | HIGH | Verified by running code in the actual project environment |
| Deprecated API locations and fixes | HIGH | Confirmed present in dashboard.py; replacements verified working |
| Caching strategy and TTL values | HIGH | Official Streamlit docs + codebase analysis of CI schedule |
| Test strategy (two-layer approach) | HIGH | Official pytest + AppTest docs + direct codebase analysis |
| Heatmap implementation | HIGH | Official Plotly docs; `px.imshow` API verified |
| Forecast band construction | HIGH | Official Plotly filled area docs |
| Monte Carlo algorithm | MEDIUM | Multiple practitioner sources agree; no official Plotly/Streamlit doc |
| Streamlit 1.55 metric card params | MEDIUM | Basic params (label/value/delta/help) HIGH; newer params (border, chart_data) LOW — verify before use |

### Gaps to Address During Implementation

1. **Column schema mismatch:** ARCHITECTURE.md fixture uses `"Chave"` as the subtask key column while STACK.md fixture uses `"Key"`. Verify actual FASE_3.csv header before writing fixtures.
2. **requirements.txt version drift:** Installed pandas 2.1.4 vs pinned 2.2.3; installed numpy 1.26.4 vs pinned 2.2.1. Clarify whether the pinned or installed version is the deployment target before any upgrade path is planned.
3. **`calcular_ciclo_ideal` dependency:** This function reads module-level `df_lake` — not extractable to `calculations.py` without also passing `df_lake` as a parameter. Flag during Phase 3 extraction work.
4. **Throughput data availability:** Monte Carlo confidence intervals will be very wide or non-functional for most lakes until more Done items accumulate. The Phase 5 implementation must present this limitation clearly to users.

---

## Sources (Aggregated)

### Primary (HIGH confidence)
- Official Streamlit docs: AppTest API, `st.cache_data`, `st.metric`
- Official pandas docs: 3.0 What's New, String Migration Guide, `fillna`, `applymap`
- Official Plotly docs: Heatmaps, Annotated Heatmaps, Filled Area Plots, Shapes
- Official pytest docs: Good practices, fixtures, `tmp_path`
- Direct codebase analysis: `dashboard.py` (2,351 lines), `script_atualizacao.py`, `FASE_3.csv` schema, `historico_completo-BMC.csv` schema
- In-project runtime verification: deprecated calls and replacements confirmed under Python 3.12.5 / pandas 2.1.4

### Secondary (MEDIUM confidence)
- Monte Carlo forecasting: Expedia Group Tech blog, Agile Seekers
- WCAG accessible color palettes: Carbon Design System
- Discrete heatmap colorscales: Plotly community thread
- AppTest cache bug: GitHub issue #9139 (confirmed, workaround documented)
- Plotly `orjson` speedup: Streamlit PR #7860

### Tertiary (LOW — validate before relying on)
- Streamlit 1.55 `st.metric` `border` parameter availability
- pandas 3.0 CoW migration behavior for specific chained assignment patterns in dashboard.py
