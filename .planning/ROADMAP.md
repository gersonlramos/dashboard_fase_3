# Roadmap: Dashboard Fase 3

**Milestone:** v1 â€” Foundation & New Views
**Goal:** Harden the existing dashboard against pandas 3.x failures and slow renders, establish a test safety net, and deliver two new views (migration heatmap and timeline/forecast) that answer the team's core question â€” how many items remain and when will it finish.
**Requirements:** REQUIREMENTS.md

---

## Phase 1: Correctness Fixes

**Goal:** All deprecated pandas API calls eliminated and a pytest gate installed so no future pandas-3.x-breaking pattern can be reintroduced silently.
**Requirements:** FIX-01, FIX-02, FIX-03, FIX-04
**Depends on:** Nothing
**Plans:** 4 plans

Plans:
- [x] 01-01-PLAN.md â€” Fix fillna deprecation: replace `fillna(method='ffill')` at dashboard.py:48 with `.ffill()`
- [x] 01-02-PLAN.md â€” Fix applymap deprecation: replace `style.applymap()` at dashboard.py:1214 with `style.map()`
- [x] 01-03-PLAN.md â€” Replace dias_uteis_restantes while-loop with np.busday_count; tighten bare except; add Historia guard
- [x] 01-04-PLAN.md â€” Create pytest.ini with filterwarnings = error::FutureWarning gate

**Success criteria:**
- [ ] Running `python -W error::FutureWarning -c "import app.dashboard.dashboard"` produces no warnings and no exceptions.
- [ ] `pytest` exits 0 with the FutureWarning filter active (no existing call trips the gate).
- [ ] The Detalhes table renders status colors correctly after the `applymap` â†’ `map` change.
- [ ] SLA business-day values match the previous loop-based output for a sample of pending items.

---

## Phase 2: Performance

**Goal:** Data loading and chart rendering complete in milliseconds on repeated interactions, with users able to force a manual refresh between scheduled CI runs.
**Requirements:** PERF-01, PERF-02, PERF-03, PERF-04
**Depends on:** Phase 1

**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md â€” Add @st.cache_data(ttl=900) to carregar_dados and calcular_ciclo_desenvolvimento (PERF-01, PERF-02)
- [x] 02-02-PLAN.md â€” Add Atualizar dados button + orjson dependency (PERF-03, PERF-04)

### Plans (original outline)

1. **Cache carregar_dados** â€” Decorate `carregar_dados()` with `@st.cache_data(ttl=900)` so the FASE_3.csv disk read happens at most once per 15 minutes across all user interactions.
2. **Cache calcular_ciclo_desenvolvimento** â€” Decorate `calcular_ciclo_desenvolvimento()` with `@st.cache_data(ttl=900)` so the 9 history-CSV glob-and-read cycle is eliminated on every sidebar filter change.
3. **Add Atualizar dados button** â€” Place a "Atualizar dados" button in the sidebar that calls `carregar_dados.clear()` and `calcular_ciclo_desenvolvimento.clear()` so users can force a refresh between the 4Ã— daily CI runs without restarting the app.
4. **Add orjson to requirements.txt** â€” Add `orjson` as a dependency; Plotly uses it automatically for JSON serialization when present, delivering ~8Ã— chart serialization speedup with no code changes.

**Success criteria:**
- [ ] Switching sidebar filters after initial load does not re-read any CSV files (verified by adding a `print` statement inside `carregar_dados` and confirming it fires only once per cache period).
- [ ] The "Atualizar dados" button appears in the sidebar and clicking it triggers a full data reload on the next render.
- [ ] `orjson` appears in `requirements.txt` and installs cleanly in the Codespaces environment.
- [ ] No `@st.cache_resource` decorators introduced (DataFrames must use `cache_data` only).

---

## Phase 3: Test Suite â€” Calculations

**Goal:** Pure calculation functions are extracted to `calculations.py` and covered by unit tests, with a smoke test confirming the full app loads without exceptions.
**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07
**Depends on:** Phase 1

**Plans:** 3 plans

Plans:
- [x] 03-01-PLAN.md â€” Extract calculation functions to calculations.py + conftest fixture (TEST-01)
- [x] 03-02-PLAN.md â€” TDD unit tests for all 6 functions, â‰¥90% coverage (TEST-02 to TEST-06)
- [x] 03-03-PLAN.md â€” AppTest smoke test: dashboard loads without exception (TEST-07)

### Plans

1. **Extract calculations.py** â€” Copy (verbatim, no signature changes) `calcular_curva_aprendizado`, `calcular_dias_uteis`, `colorir_status`, `classificar_subtarefa`, `normalizar_id_historia`, and `parse_data_criacao` into `app/dashboard/calculations.py`; add a single `from calculations import ...` line to `dashboard.py` so both files stay in sync without duplication.
2. **Set up tests/ directory** â€” Create `tests/` at the project root with `conftest.py` (sample CSV fixtures matching the real 13-column `FASE_3.csv` schema), `pytest.ini` already written in Phase 1, and an empty `__init__.py`-free layout.
3. **Write test_calculations.py** â€” Unit tests covering `calcular_curva_aprendizado` (sigmoid range, edge cases), `calcular_dias_uteis` (weekday counting, weekend exclusion, boundary), `colorir_status` (all known strings, unknown fallback), `classificar_subtarefa` (all category strings), and burndown/burnup projection logic (Ã—1.3 optimistic, Ã—0.7 pessimistic, zero-velocity edge case).
4. **Write AppTest smoke test** â€” `tests/test_app_smoke.py` with `AppTest.from_file("app/dashboard/dashboard.py")` that asserts `not at.exception`; include an `autouse` fixture calling `st.cache_data.clear()` in teardown to prevent cache contamination between test runs.

**Success criteria:**
- [ ] `pytest tests/test_calculations.py -v` passes with all functions covered: `calcular_curva_aprendizado`, `calcular_dias_uteis`, `colorir_status`, `classificar_subtarefa`, burndown/burnup projections.
- [ ] `pytest tests/test_app_smoke.py` passes â€” app loads without exception on sample fixtures.
- [ ] `pytest --cov=app/dashboard/calculations.py` reports â‰¥ 90% line coverage on the extracted module.
- [ ] No existing `dashboard.py` behavior changes â€” all extracted functions remain importable from `dashboard.py` via the added import line.
- [ ] `filterwarnings = error::FutureWarning` in `pytest.ini` does not cause any test to fail on the extracted functions.

---

## Phase 4: Test Suite â€” Data Pipeline

**Goal:** ETL script helper functions are unit-tested with mocked HTTP, CSV parsing is tested against a real-schema fixture, and overall line coverage on `calculations.py` reaches 70%.
**Requirements:** TEST-08, TEST-09, TEST-10, TEST-11, TEST-12
**Depends on:** Phase 3
**Plans:** 4 plans

Plans:
- [x] 04-01-PLAN.md â€” Guard script_atualizacao.py + extract carregar_dados_csv to data_loader.py
- [x] 04-02-PLAN.md â€” Unit tests for extrair_data_lake, classificar_subtarefa, buscar_com_paginacao (TEST-08, TEST-09)
- [x] 04-03-PLAN.md â€” Unit tests for carregar_dados_csv and adf_para_texto (TEST-10, TEST-11)
- [x] 04-04-PLAN.md â€” Coverage gate: assert calculations.py â‰¥70% line coverage (TEST-12)

### Plans

1. **Test ETL classification helpers** â€” Import `classificar_subtarefa` and `extrair_data_lake` from `script_atualizacao.py` via `sys.path.insert` and write unit tests for all category strings and lake-name extraction patterns.
2. **Test paginated HTTP fetching** â€” Write `tests/test_etl_atualizacao.py` mocking `requests.get` via `unittest.mock.patch` to cover: single-page response, multi-page pagination (two pages), and 401 auth failure; assert correct issue count and error handling.
3. **Test carregar_dados with CSV fixture** â€” Write `tests/test_data_loader.py` that creates a temporary CSV matching the real 13-column `FASE_3.csv` schema (`Epico, Historia, Titulo Historia, Data-Lake, Chave, Titulo, Status, Data Criacao, Data Atualizacao, Quantidade Subtarefas, Categoria_Analise, Start Date Historia, Deadline Historia`) and asserts `carregar_dados()` returns a DataFrame with correct dtypes and row count.
4. **Test adf_para_texto** â€” Import `adf_para_texto` from `script_pendencias.py` and write unit tests for ADF JSON â†’ plain text conversion, including empty document, nested nodes, and unknown node types.
5. **Verify 70% coverage target** â€” Run `pytest --cov=app --cov-report=term-missing` and confirm `calculations.py` is at or above 70% line coverage; document any intentionally untested code paths.

**Success criteria:**
- [ ] `pytest tests/test_etl_atualizacao.py -v` passes with single-page, multi-page, and 401 scenarios all covered.
- [ ] `pytest tests/test_data_loader.py -v` passes â€” `carregar_dados()` correctly parses a minimal fixture CSV.
- [ ] `pytest tests/test_etl_pendencias.py -v` passes â€” `adf_para_texto` handles all documented node types.
- [ ] `pytest --cov=app` reports â‰¥ 70% line coverage on `calculations.py`.
- [ ] No test makes a real network call â€” all HTTP is mocked.

---

## Phase 5: Migration Heatmap

**Goal:** A new "Mapa de MigraÃ§Ã£o" tab is live showing the 9-lake Ã— 5-status percentage grid with theme support, cell annotations, and cross-filtering to the Detalhes tab.
**Requirements:** HEAT-01, HEAT-02, HEAT-03, HEAT-04, HEAT-05, HEAT-06, HEAT-07, VIS-01, VIS-02, VIS-03, VIS-04
**Depends on:** Phase 2
**UI hint**: yes

**Plans:** 3 plans

Plans:
- [ ] 05-01-PLAN.md â€” Nav entry + STATUS_COLOR_MAP/STATUS_BUCKET/BUCKET_ORDER/BUCKET_COLORS constants + _compute_heatmap_pivot() + elif stub (HEAT-01, HEAT-02, HEAT-03)
- [ ] 05-02-PLAN.md â€” Full go.Heatmap render + metric cards + cross-filter selectbox + Detalhes table (HEAT-04, HEAT-05, HEAT-06, HEAT-07)
- [ ] 05-03-PLAN.md â€” VIS pass: centralize STATUS_COLOR_MAP, suppress trace-name boxes, enrich tooltips, add axis labels (VIS-01, VIS-02, VIS-03, VIS-04)

**Success criteria:**
- [ ] "Mapa de MigraÃ§Ã£o" tab appears in the sidebar and renders without exceptions on the live CSV data.
- [ ] All 9 data lakes appear as rows and all 5 status buckets appear as columns in the heatmap.
- [ ] Each cell displays its percentage value as annotation text and is colored according to the discrete colorscale.
- [ ] Switching between dark and light theme updates heatmap background and text colors correctly.
- [ ] Selecting a lake from the cross-filter dropdown updates the Detalhes table to show only items from that lake.
- [ ] No existing tab (Executivo, Graficos, Detalhes, Pendencias) breaks after the change.
- [ ] All key Plotly charts suppress the default trace-name box in tooltips (`<extra></extra>`).

---

## Phase 6: Timeline & Forecast View

**Goal:** A new "PrevisÃ£o" tab shows projected completion dates per epic and overall, with a probabilistic confidence band, rolling velocity trend, milestone markers, and graceful fallback when throughput data is too sparse.
**Requirements:** FORE-01, FORE-02, FORE-03, FORE-04, FORE-05, FORE-06, FORE-07
**Depends on:** Phase 3, Phase 2

**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md — Add Previsao nav + forecast contracts (monte_carlo/fallback) + insufficient-data guard + cache wiring
- [x] 06-02-PLAN.md — Build P50/P85 confidence band chart + +/-30% fallback + milestone add_vline markers
- [x] 06-03-PLAN.md — Add rolling velocity 7d/14d trend + forecast metric cards + filtered consolidation

### Plans

1. **Add forecast tab and monte_carlo_forecast function** â€” Append "PrevisÃ£o" to the sidebar radio list; implement `monte_carlo_forecast(daily_throughput, remaining, n_simulations=5000, seed=42)` returning `{"p50": int, "p85": int}` day offsets; include explicit guard `if len(daily_throughput) < 3: return None` to fall back to the existing Â±30% linear projection.
2. **Build forecast confidence band** â€” Render the P50 lower trace and the P85 invisible upper trace with `fill='tonexty'` using `go.Scatter`; display P50 as the central forecast line and the shaded band as the uncertainty range; show the existing Â±30% linear projection as a dashed fallback for lakes with fewer than 3 Done data points.
3. **Add rolling velocity chart** â€” Compute 7-day and 14-day rolling means on `burn_real` daily throughput; render both on a secondary y-axis via `yaxis2` with labels "Velocidade 7d" and "Velocidade 14d"; provide visual indication of acceleration vs deceleration.
4. **Add milestone markers** â€” Read `datas_esperadas_por_lake.csv` (already loaded as `lakes_fase`); derive the maximum `data_fim` per lake; call `add_vline` with date strings (not `pd.Timestamp` objects) for each lake's cutover date; label each line with the lake name.
5. **Add forecast metric cards and graceful degradation** â€” Place `st.metric` cards for Central Forecast (P50 date), Conservative Forecast (P85 date), and velocity delta (7d vs 14d); when a lake has zero completed items, render `st.info("Dados insuficientes â€” projeÃ§Ã£o indisponÃ­vel para este lago")` instead of a broken chart; decorate all forecast calculation functions with `@st.cache_data(ttl=900)`.

**Success criteria:**
- [ ] "PrevisÃ£o" tab appears in the sidebar and renders without exceptions for all 9 lakes.
- [ ] A lake with zero Done items shows the "Dados insuficientes" message instead of an error or empty chart.
- [ ] A lake with sufficient data (e.g., COMPRAS) shows both the P50 line and the P50â€“P85 shaded band.
- [ ] Milestone vertical lines appear on the forecast chart for all lakes that have a date in `datas_esperadas_por_lake.csv`.
- [ ] The rolling velocity chart shows 7-day and 14-day trend lines on a secondary axis.
- [ ] Forecast metric cards (P50 date, P85 date, velocity delta) are visible above the chart.
- [ ] No forecast calculation is recomputed on every widget interaction â€” verified by confirming `@st.cache_data` is applied to all forecast functions.

---

## Phase 7: Alerts & Bottleneck Detection

**Goal:** O dashboard detecta automaticamente lakes em risco de atraso e impedimentos vencidos, exibindo alertas visuais na aba Executivo sem necessidade de navegar para outras abas.
**Requirements:** ALERT-01, ALERT-02, ALERT-03, ALERT-04, ALERT-05
**Depends on:** Phase 2 (caching), Phase 6 (forecast data already loaded)

**Plans:** 2 plans

Plans:
- [ ] 07-01-PLAN.md — Cálculo de velocidade necessária por lake + semáforo de risco (ALERT-04, ALERT-02, ALERT-03)
- [ ] 07-02-PLAN.md — Badge de impedimentos vencidos + resumo de alertas na aba Executivo (ALERT-01, ALERT-05)

**Success criteria:**
- [ ] Aba Executivo exibe contagem de lakes em risco (vermelho) e em atenção (amarelo) sem precisar navegar.
- [ ] Impedimentos com deadline vencida exibem badge/indicador visível.
- [ ] Velocidade necessária é calculada corretamente com `np.busday_count` para cada lake.
- [ ] Semáforo verde aparece quando lake está no ritmo ou acima.
- [ ] Nenhuma aba existente quebra após a mudança.

---

## Phase 8: Weekly Tracker View

**Goal:** Uma nova aba "Semanas" dá visão consolidada semana a semana: progresso real vs. meta por lake, velocidade de entrega, semáforos de risco e impedimentos com SLA, em uma única tela.
**Requirements:** WEEK-01, WEEK-02, WEEK-03, WEEK-04, WEEK-05, WEEK-06
**Depends on:** Phase 7 (reaproveita cálculo de velocidade necessária e semáforo)

**Plans:** 2 plans

Plans:
- [ ] 08-01-PLAN.md — Nav entry + tabela semanal por lake (velocidade real vs. necessária, semáforo, semanas restantes) (WEEK-01, WEEK-02, WEEK-05)
- [ ] 08-02-PLAN.md — Seção impedimentos com SLA vencido + gráfico barras progresso vs. meta + tema (WEEK-03, WEEK-04, WEEK-06)

**Success criteria:**
- [ ] Aba "📋 Semanas" aparece na navegação e renderiza sem exceções.
- [ ] Tabela exibe todos os 9 lakes com semáforo correto (🔴/🟡/🟢) baseado na velocidade.
- [ ] Impedimentos vencidos aparecem destacados na seção de impedimentos.
- [ ] Gráfico de barras mostra progresso real vs. meta semanal por lake.
- [ ] Aba respeita tema dark/light.
- [ ] Nenhuma aba existente quebra após a mudança.

---

## Coverage

| Phase | Requirements | Key Deliverable |
|-------|-------------|-----------------|
| 1 â€” Correctness Fixes | FIX-01, FIX-02, FIX-03, FIX-04 | No FutureWarnings, CI gate |
| 2 â€” Performance | PERF-01, PERF-02, PERF-03, PERF-04 | Instant dashboard loads, manual refresh button |
| 3 â€” Test Suite: Calculations | TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07 | Unit tests for all calculation functions |
| 4 â€” Test Suite: Data Pipeline | TEST-08, TEST-09, TEST-10, TEST-11, TEST-12 | ETL + CSV pipeline tests, 70% coverage |
| 5 â€” Migration Heatmap | HEAT-01, HEAT-02, HEAT-03, HEAT-04, HEAT-05, HEAT-06, HEAT-07, VIS-01, VIS-02, VIS-03, VIS-04 | Migration heatmap tab + visual clarity pass |
| 6 â€” Timeline & Forecast View | FORE-01, FORE-02, FORE-03, FORE-04, FORE-05, FORE-06, FORE-07 | Forecast & timeline tab with Monte Carlo bands |

**Total v1 requirements:** 35
**Mapped:** 35
**Unmapped:** 0

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Correctness Fixes | 4/4 | Done | 2026-03-25 |
| 2. Performance | 2/2 | Done | 2026-03-25 |
| 3. Test Suite: Calculations | 3/3 | Done | 2026-03-25 |
| 4. Test Suite: Data Pipeline | 4/4 | Done | 2026-03-25 |
| 5. Migration Heatmap | 3/3 | Done | 2026-03-25 |
| 6. Timeline & Forecast View | 3/3 | Done | 2026-03-26 |
| 7. Alerts & Bottleneck Detection | 0/2 | Planned | - |
| 8. Weekly Tracker View | 0/2 | Planned | - |

---

*Roadmap created: 2026-03-25*
*Phase 1 plans created: 2026-03-25*

