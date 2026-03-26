# Requirements: Dashboard Fase 3 — GCP to AWS Migration Tracker

**Defined:** 2026-03-25
**Core Value:** The migration team must always know how many items are done, how many remain, and when it will finish — with a forecast honest enough to plan around.

## v1 Requirements

### Correctness Fixes

- [ ] **FIX-01**: `fillna(method='ffill')` in `calcular_curva_aprendizado()` (line 48) replaced with `.ffill()` — no `FutureWarning` or `TypeError` on pandas 3.x
- [ ] **FIX-02**: `style.applymap()` in dashboard rendering (line 1214) replaced with `style.map()` — no `FutureWarning` or `AttributeError` on pandas 3.x
- [ ] **FIX-03**: `dias_uteis_restantes()` while-loop replaced with `np.busday_count()` — consistent with `calcular_dias_uteis()` already in codebase
- [ ] **FIX-04**: `pytest.ini` configured with `filterwarnings = error::FutureWarning` so any re-introduced deprecated pandas call fails CI automatically

### Performance

- [ ] **PERF-01**: `carregar_dados()` decorated with `@st.cache_data(ttl=900)` — CSV files not re-read on every user interaction
- [ ] **PERF-02**: `calcular_ciclo_desenvolvimento()` decorated with `@st.cache_data(ttl=900)` — 9 history CSV reads per render eliminated
- [ ] **PERF-03**: Manual "Atualizar dados" button calls `carregar_dados.clear()` allowing forced refresh between CI runs
- [ ] **PERF-04**: `orjson` added to `requirements.txt` — faster Plotly chart serialization with no code changes

### Test Suite — Calculations

- [ ] **TEST-01**: Pure calculation functions extracted verbatim to `app/dashboard/calculations.py` (at minimum: `calcular_curva_aprendizado`, `calcular_dias_uteis`, `colorir_status`, `classificar_subtarefa`, `normalizar_id_historia`, `parse_data_criacao`)
- [ ] **TEST-02**: Unit tests written for `calcular_curva_aprendizado()` — sigmoid output range, learning curve shape, edge cases (0 items, all done)
- [ ] **TEST-03**: Unit tests written for `calcular_dias_uteis()` — weekday counting, weekend exclusion, holiday boundary
- [ ] **TEST-04**: Unit tests written for `colorir_status()` — all known status strings return correct colors, unknown status has safe fallback
- [ ] **TEST-05**: Unit tests written for `classificar_subtarefa()` — all category strings return correct classification
- [ ] **TEST-06**: Unit tests written for burndown/burnup projection logic — optimistic (×1.3), pessimistic (×0.7), zero-velocity edge case
- [ ] **TEST-07**: AppTest smoke test confirms dashboard loads without exception when fed sample CSV fixtures

### Test Suite — Data Pipeline

- [ ] **TEST-08**: `classificar_subtarefa()` and `extrair_data_lake()` from `script_atualizacao.py` unit-tested by direct import via `sys.path.insert`
- [ ] **TEST-09**: `buscar_com_paginacao()` tested with mocked HTTP responses — single page, multi-page pagination, 401 auth failure
- [ ] **TEST-10**: `carregar_dados()` tested with a sample CSV fixture matching the real 13-column `FASE_3.csv` schema
- [ ] **TEST-11**: `adf_para_texto()` from `script_pendencias.py` unit-tested for ADF JSON → plain text conversion
- [ ] **TEST-12**: `pytest --cov=app` reports ≥ 70% line coverage on `calculations.py`

### Migration Heatmap View

- [ ] **HEAT-01**: New tab "🗺️ Mapa de Migração" added to sidebar navigation (appended to existing radio list)
- [ ] **HEAT-02**: Heatmap displays a 9-lake × 5-status-bucket percentage matrix using `px.imshow()` — lakes as rows, status buckets as columns
- [ ] **HEAT-03**: Status buckets: `Não Iniciado` (Open/To Do), `Em Andamento` (In Progress/In Test/Waiting Test), `Concluído` (Done), `Cancelado` (Canceled), `Bloqueado` (if applicable)
- [ ] **HEAT-04**: Each cell shows both the color encoding and the item count (annotation text)
- [ ] **HEAT-05**: Discrete colorscale: green for Concluído, blue for Em Andamento, gray for Não Iniciado, red for Bloqueado/Cancelado
- [ ] **HEAT-06**: Clicking a cell (or selecting lake from dropdown) filters the existing Detalhes tab to show matching items
- [ ] **HEAT-07**: Heatmap respects current theme (dark/light) — background and text colors adapt

### Timeline & Forecast View

- [ ] **FORE-01**: New tab "📅 Previsão" added to sidebar navigation
- [ ] **FORE-02**: Projected end date displayed per epic and as an overall project completion date, based on current velocity
- [ ] **FORE-03**: Optimistic (×1.3 velocity) and pessimistic (×0.7 velocity) completion date range shown — consistent with existing burndown/burnup factors
- [ ] **FORE-04**: Velocity trend chart shows rolling 7-day vs 14-day throughput — visual indication of acceleration or deceleration
- [ ] **FORE-05**: Milestone markers (cutover dates per lake from `datas_esperadas_por_lake.csv`) displayed as vertical lines via `add_vline()` on the forecast chart
- [ ] **FORE-06**: Graceful degradation when a lake has zero completed items — shows "Dados insuficientes" instead of broken chart
- [ ] **FORE-07**: All forecast calculations apply `@st.cache_data(ttl=900)` — not recomputed on every widget interaction

### Visual Clarity

- [ ] **VIS-01**: All Plotly charts use `<extra></extra>` in `hovertemplate` to suppress default trace-name box in tooltips
- [ ] **VIS-02**: Hover tooltips on key charts include: item title, status, assignee, remaining days
- [ ] **VIS-03**: Status colors are consistent across all charts and the heatmap (single color mapping defined once, referenced everywhere)
- [ ] **VIS-04**: Chart axis labels and titles are present and descriptive (no unlabeled axes)

### Alerts & Bottleneck Detection

- [ ] **ALERT-01**: Sidebar ou aba Executivo exibe badge de alerta quando qualquer impedimento está vencido (deadline < hoje e status != Done/Closed)
- [ ] **ALERT-02**: Cada lake com velocidade real abaixo de 50% da velocidade necessária para cumprir o deadline exibe indicador visual de risco (vermelho)
- [ ] **ALERT-03**: Cada lake com velocidade entre 50–80% da necessária exibe indicador de atenção (amarelo)
- [ ] **ALERT-04**: Cálculo de velocidade necessária: `itens_restantes / dias_uteis_ate_deadline` por lake, usando `np.busday_count`
- [ ] **ALERT-05**: Resumo de alertas visível na aba Executivo (n° de lakes em risco, n° de impedimentos vencidos)

### Weekly Tracker View

- [ ] **WEEK-01**: Nova aba "📋 Semanas" adicionada à navegação sidebar
- [ ] **WEEK-02**: Tabela semanal exibe, por lake: itens restantes, done esta semana, velocidade atual, velocidade necessária, semáforo de risco (🔴/🟡/🟢)
- [ ] **WEEK-03**: Seção de impedimentos exibe todos os itens abertos com indicação de "vencido" quando deadline < hoje
- [ ] **WEEK-04**: Gráfico de barras empilhadas mostra progresso por lake vs. meta semanal
- [ ] **WEEK-05**: Indicador de semanas restantes até deadline por lake, calculado com `np.busday_count`
- [ ] **WEEK-06**: Aba respeita tema dark/light

## v2 Requirements

### Deferred to Future Milestone

- **SEC-01**: HTML-escape all Jira-sourced strings before `unsafe_allow_html=True` rendering (XSS mitigation) — low urgency while dashboard is on internal network
- **CFG-01**: Centralize hardcoded project key (`BF3E4`), epic IDs, and Jira URL into a single config file — needed when project expands to second migration
- **REF-01**: Full modular refactor — `calculations.py`, `components.py`, `data_loader.py` — defer until test coverage provides safety net
- **SEC-02**: SSL verification re-enabled for Jira API calls — requires corporate network SSL cert bundle to be resolved

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live Jira connection from dashboard | Architecture decision: CSV pipeline is the data layer; no live API in dashboard |
| Multi-project support | Only `BF3E4` in scope for this milestone |
| User authentication / access control | Internal tool, Codespaces access control is sufficient |
| Mobile/responsive layout | Streamlit desktop-first, migration team uses desktops |
| Monolith refactor | Deferred to v2 — tests must come first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01, FIX-02, FIX-03, FIX-04 | Phase 1 | Pending |
| PERF-01, PERF-02, PERF-03, PERF-04 | Phase 2 | Pending |
| TEST-01 – TEST-07 | Phase 3 | Pending |
| TEST-08 – TEST-12 | Phase 4 | Pending |
| HEAT-01 – HEAT-07 | Phase 5 | Pending |
| FORE-01 – FORE-07 | Phase 6 | Pending |
| VIS-01 – VIS-04 | Phase 5 + 6 | Pending |
| ALERT-01 – ALERT-05 | Phase 7 | Pending |
| WEEK-01 – WEEK-06 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after initialization*
