# Codebase Concerns

**Analysis Date:** 2026-03-26

## Critical Issues

**Imported functions silently shadowed by local redefinitions:**
- `calcular_curva_aprendizado` is imported from `calculations.py` at line 9 of `dashboard.py`, then immediately redefined as a local function at line 20. The imported version is completely unreachable at runtime.
- `normalizar_id_historia` is imported at line 11, then locally redefined at line 889.
- Files: `app/dashboard/dashboard.py` (lines 9–13 imports; lines 20, 889 redefinitions), `app/dashboard/calculations.py`
- Impact: Any bug fix or improvement applied to `calculations.py` has no effect on the running dashboard. Tests passing against `calculations.py` versions do not validate what the dashboard actually executes.
- Fix approach: Remove the two local redefinitions from `dashboard.py` and rely solely on the imported versions.

**SSL verification disabled across all HTTP requests:**
- All three scripts disable SSL certificate verification (`verify=False`) and suppress the resulting warnings with `urllib3.disable_warnings`.
- Files: `app/scripts/script_atualizacao.py` (lines 80, 114, 140, 244), `app/scripts/extrair_historico.py` (line 94), `app/scripts/script_pendencias.py` (line 102)
- Impact: Accepted as corporate network constraint. Would be a risk from untrusted networks.

**Deprecated pandas API in active code paths:**
- `fillna(method='ffill')` is deprecated since pandas 2.1; raises `FutureWarning` (fails tests under `filterwarnings = error::FutureWarning` in `pytest.ini`).
- `df_render.style.applymap(colorir_status)` uses `applymap` renamed to `map` in pandas 2.x.
- Files: `app/dashboard/dashboard.py` (various lines); `pytest.ini` converts these to errors.
- Fix: Replace `fillna(method='ffill')` with `.ffill()` and `applymap` with `.map`.

**Dashboard monolith cannot be unit-tested by import:**
- `app/dashboard/dashboard.py` runs `st.set_page_config()` at module scope (line 65). Any `import dashboard` in a test triggers Streamlit initialization and crashes the runner.
- Files: `app/dashboard/dashboard.py` (line 65)
- Impact: Rendering logic (all 6 tabs, ~1,300 lines) has zero unit test coverage.
- Fix approach: Continue extracting pure functions to `calculations.py`; wrap rendering in functions rather than top-level code.

## Technical Debt

**`calcular_ciclo_ideal` missing `@st.cache_data` decorator:**
- `calcular_ciclo_desenvolvimento` at line 725 is cached with `@st.cache_data(ttl=900)`, but the equivalent `calcular_ciclo_ideal` at line 857 has no cache decorator. It iterates all rows of `datas_esperadas_por_lake.csv` on every Streamlit interaction.
- Files: `app/dashboard/dashboard.py` (line 857)
- Fix: Add `@st.cache_data(ttl=900)` before `calcular_ciclo_ideal`.

**`_build_forecast_inputs` defined inside a conditional tab block:**
- Defined with `@st.cache_data(ttl=900)` at line 2507, nested inside the `elif aba_selecionada == "📅 Previsão":` block. Streamlit re-registers the cache key on every rerun when the tab is active, which is an anti-pattern.
- Files: `app/dashboard/dashboard.py` (lines 2507–2515)
- Fix: Hoist to module level.

**Hardcoded project and epic keys across scripts:**
- `projeto = "BF3E4"` in `script_atualizacao.py` line 21.
- `EPIC = "BF3E4-293"` in `script_pendencias.py` line 21.
- Epic-to-name mapping dict in `extrair_historico.py` lines 23–31.
- File references `pendencias_BF3E4-293.csv` and `historico_BF3E4-293.csv` in `dashboard.py` lines 2023–2024.
- Files: `app/scripts/script_atualizacao.py`, `app/scripts/extrair_historico.py`, `app/scripts/script_pendencias.py`, `app/dashboard/dashboard.py`
- Impact: Extending to another project or epic requires editing four separate files. Explicitly deferred in PROJECT.md.

**Hardcoded burn-up start date:**
- `data_inicio_burnup = pd.Timestamp('2026-03-13')` hardcoded in `dashboard.py`. Must be manually updated when the project phase changes.
- Files: `app/dashboard/dashboard.py` (search for `data_inicio_burnup`)

**Duplicate `status_concluidos` list defined in 5+ locations:**
- The list `['Done', 'Closed', 'Resolved', 'Concluído', 'Concluida', 'Canceled', 'Cancelled', 'Cancelado']` is redefined at multiple locations in `dashboard.py`. Any status name change must be applied in all places.
- Files: `app/dashboard/dashboard.py` (lines 611, and others throughout)
- Fix: Define once as a module-level constant.

**Custom CSV parser with fragile column-count assumption:**
- The fallback CSV parser in `data_loader.py` (lines 18–46) assumes exactly 11 columns and raises a bare `raise` if the header count differs. Column-position slicing (`partes[:5]`, `partes[-5:]`) silently produces corrupt data if the schema changes.
- Files: `app/dashboard/data_loader.py` (lines 18–46)
- Fix: Use `csv.reader` with proper quoting, or `pandas.read_csv` with `on_bad_lines='skip'`.

**`script_atualizacao.py` executes top-level API calls at module scope:**
- Lines 100+ call the Jira API and call `exit()` at top level. The script cannot be imported, tested, or reused as a library.
- Files: `app/scripts/script_atualizacao.py`

**`quantidade_subtarefas` field always zero:**
- Initialized to `0` and written to CSV without ever being populated.
- Files: `app/scripts/script_atualizacao.py` (line ~284)

**Dead code: `jql_customizado` branch in `extrair_historico.py`:**
- `tipo_busca` is hardcoded to `"epic"` and never changed, so the `jql` branch is unreachable.
- Files: `app/scripts/extrair_historico.py` (lines 36–63)

**`pytest` version unpinned in requirements.txt:**
- All other packages are pinned; `pytest` is listed without a version.
- Files: `requirements.txt` (line 14)
- Fix: Pin to `pytest==9.0.2` (version in use per `__pycache__` filenames).

**Python runtime version drift:**
- `__pycache__` filenames show `cpython-314` (Python 3.14) while stack docs target Python 3.11. Installed pandas is 2.1.4 while `requirements.txt` pins 2.2.3. Noted in STATE.md — verify deployment target before next milestone.

## Performance Concerns

**`calcular_ciclo_desenvolvimento` reads 9 CSV files on every cache miss:**
- Iterates over all 9 `historico_completo-*.csv` files, parses dates, and computes per-row deltas. With TTL=900 s, a cold start (new Codespace, cache clear) or first filter change triggers a full reload.
- Files: `app/dashboard/dashboard.py` (lines 726–855)
- Fix: Pre-aggregate history data in the ETL pipeline and persist as a summary CSV.

**SLA business-days calculation uses a Python day-by-day loop:**
- `dias_uteis_restantes()` iterates day-by-day in a `while` loop instead of using `numpy.busday_count`. Called once per pending item on every rerender.
- Files: `app/dashboard/dashboard.py` (lines ~2158–2171)
- Fix: Replace with `np.busday_count(hoje_d, deadline)` — consistent with `calcular_dias_uteis()` already in the codebase.

**Module-level code re-executes on every Streamlit rerun:**
- Filter derivation, DataFrame copies, and metric calculations at lines 570–619 and ~900–930 run at module scope and re-execute on every widget interaction.
- Files: `app/dashboard/dashboard.py`
- Fix: Wrap stateless computations inside cached functions or gate them inside tab blocks.

**Linear projection uses unvectorized row iteration:**
- `calcular_ciclo_desenvolvimento` iterates every row of the combined history dataframe inside nested loops without vectorization.
- Files: `app/dashboard/dashboard.py` (lines 726–855)

## Security

**`unsafe_allow_html=True` used 20+ times with Jira-sourced data:**
- HTML is built by string-interpolating data from CSVs (Titulo, Descricao fields sourced from Jira) into `st.markdown(..., unsafe_allow_html=True)`.
- Files: `app/dashboard/dashboard.py` (lines 273, 384, 392, 459, 502, 1304, 1533, 1575, 1616, 1632, 1746, 1997, 2007, 2045, 2114, 2190, 2249, 2353, 2355, 2403, 2451, 2457, 2470, 2497, 2505)
- Risk: Low while the dashboard is internal-only. XSS vector if any Jira field contains injected HTML.
- Recommendation: Apply `html.escape()` to `Titulo` and `Descricao` before interpolation.

**API credentials loaded without validation:**
- `EMAIL` and `API_TOKEN` are read via `os.getenv` without guards. Missing vars silently construct `HTTPBasicAuth(None, None)` causing confusing auth errors.
- Files: `app/scripts/script_atualizacao.py` (lines 18–19), `app/scripts/extrair_historico.py`, `app/scripts/script_pendencias.py`
- Fix: Add `if not email or not api_token: raise EnvironmentError(...)` at startup.

**Data committed to git repository:**
- All extracted CSVs under `app/dados/` are committed by CI workflow. Jira issue titles, statuses, and related data are permanently in git history.
- Files: `.github/workflows/atualizar_dados.yml`

## Maintainability

**Global state consumed across 2,599-line file:**
- Variables `df`, `df_filtrado`, `burn_real`, `burn_real_acum`, `total_planejado`, `realizado_atual`, `lakes_fase` etc. are computed at module scope and consumed inside tab render blocks. No explicit data pipeline; downstream code depends on execution order.
- Files: `app/dashboard/dashboard.py` (data prep lines 539–930; tabs consume from ~1300 onward)
- Fix: After test coverage is established, extract each tab into `app/dashboard/tabs/` modules.

**Magic numbers for ±30% projection:**
- `ritmo * 1.3` (optimistic) and `ritmo * 0.7` (pessimistic) appear in burndown and burnup calculations without named constants or documentation of the ±30% basis.
- Files: `app/dashboard/dashboard.py` (lines ~927–928, ~1059–1060)

**Duplicate theme color inline computations:**
- `"#1b2a3b" if tema_selecionado != "☀️ Claro" else "#ffffff"` (and similar pairs) repeated dozens of times instead of a theme dict computed once.
- Files: `app/dashboard/dashboard.py` (throughout)

**`import glob` inside a function body:**
- `import glob` inside `calcular_ciclo_desenvolvimento()` rather than at module top.
- Files: `app/dashboard/dashboard.py` (line ~615)

**Bare `except Exception` swallows CSV read errors silently:**
- Inside `calcular_ciclo_desenvolvimento()`, corrupt history files are silently skipped with `continue`.
- Files: `app/dashboard/dashboard.py` (lines ~658–663)

## Forecast-Specific Concerns (Phase 6)

**Monte Carlo fallback is silent for 8 of 9 lakes:**
- `monte_carlo_forecast` requires at least 3 non-zero throughput data points. Only COMPRAS has meaningful Done counts as of 2026-03-26. All other lakes fall back to ±30% linear projection, but the UI only shows a brief `st.info` message — no persistent per-lake indicator.
- Files: `app/dashboard/dashboard.py` (lines 2526–2528), `app/dashboard/calculations.py` (lines 154–184)
- Impact: Users may misread linear fallback forecasts as Monte Carlo P50/P85 precision.
- Fix: Display an explicit label ("Projeção Linear — dados insuficientes para Monte Carlo") per lake whenever fallback is active.

**Forecast view is per-filtered-selection, not per-lake summary:**
- The Previsão tab shows one forecast line for whatever filter is currently applied. There is no side-by-side per-lake forecast table showing completion dates for all 9 lakes at once.
- Files: `app/dashboard/dashboard.py` (lines 2503–2599)
- Impact: Users must change the Data-Lake filter 9 times to compare forecast dates.

## Test Coverage Gaps

**Dashboard rendering logic (all 6 tabs) has zero test coverage:**
- What's not tested: Chart-building, HTML injection, filter application, heatmap rendering, forecast tab display.
- Files: `app/dashboard/dashboard.py` (lines 1300–2599)
- Risk: Visual regressions and data-display bugs go undetected.
- Priority: Medium — visible on manual inspection.

**`calcular_ciclo_ideal` and `calcular_ciclo_desenvolvimento` not directly testable:**
- Both functions reside in `dashboard.py` and cannot be imported without triggering Streamlit.
- Files: `app/dashboard/dashboard.py` (lines 726–887)
- Risk: Cycle-time calculation bugs go undetected.
- Priority: High — fix by extracting to `calculations.py`.

**ETL scripts: error paths not tested:**
- HTTP error responses (4xx/5xx), malformed JSON, and empty JQL result sets are not covered by tests.
- Files: `app/scripts/script_atualizacao.py`, `app/scripts/extrair_historico.py`, `app/scripts/script_pendencias.py`
- Priority: Medium.

## Scalability

**CSV files committed to git grow indefinitely:**
- GitHub Actions commits updated CSVs 4x per weekday. `historico_completo-*.csv` files under `app/dados/historico/` accumulate git history for the life of the project.
- Impact: Repository size growth; data history pollutes code history.
- Scaling path: Move CSVs to Git LFS or an external store (S3, GitHub Releases artifacts).

## Recommendations

Prioritized order:

1. **Remove duplicate function redefinitions** (`calcular_curva_aprendizado` line 20, `normalizar_id_historia` line 889 in `dashboard.py`) — zero-risk, prevents shadow bugs.
2. **Add `@st.cache_data` to `calcular_ciclo_ideal`** — one-line fix at line 857.
3. **Hoist `_build_forecast_inputs` to module level** — remove nested cached-function anti-pattern at line 2507.
4. **Fix deprecated pandas API calls** — `fillna(method='ffill')` and `applymap` will fail on pandas 3.x and already fail in pytest under `filterwarnings = error::FutureWarning`.
5. **Extract `calcular_ciclo_ideal` and `calcular_ciclo_desenvolvimento` to `calculations.py`** — enables unit testing of cycle-time logic.
6. **Add Monte Carlo fallback visual indicator per lake** — make forecast confidence explicit when linear projection is used.
7. **Escape Jira-sourced fields before HTML interpolation** — `html.escape()` on `Titulo` and `Descricao` before `unsafe_allow_html` rendering.
8. **Add startup env var validation to ETL scripts** — fail fast with a clear error when `EMAIL` or `API_TOKEN` is missing.
9. **Pin `pytest` version in requirements.txt** — prevent surprise breakage from unpinned test runner upgrade.
10. **Define `STATUS_DONE` / `STATUS_CANCELED` as module-level constants** — eliminate 5+ duplicate status list definitions.

---

*Concerns audit: 2026-03-26*
