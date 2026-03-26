# Architecture

**Analysis Date:** 2026-03-26

## System Overview

Single-page Streamlit dashboard for tracking the Stellantis Phase 3 migration project. Data originates in Jira (fcagil.atlassian.net), is extracted by standalone ETL scripts into CSV files, and then consumed and visualised by the dashboard at runtime. There is no backend server, no database, and no API layer — the entire application is a Python process rendered by Streamlit.

## Design Patterns

**Script-level module decomposition (not MVC):**
- Business logic (pure calculations) is isolated in `app/dashboard/calculations.py`, importable without Streamlit.
- All UI rendering and data wrangling lives in `app/dashboard/dashboard.py` (a single ~2600-line Streamlit script).
- ETL is separated into `app/scripts/` — these scripts run out-of-band (e.g., via GitHub Actions cron) and produce CSV files that the dashboard reads.

**Streamlit page model:**
- The file `dashboard.py` is the entry point for `streamlit run`. Streamlit re-executes the entire script on every user interaction.
- State is passed through variables that are re-computed each run, not through a state store.
- `@st.cache_data(ttl=900)` is used to memoize heavy CSV loads and the development cycle calculation for 15 minutes.

**Tab-based navigation:**
- `st.sidebar.radio` selects from six named views: Executivo, Graficos, Detalhes, Impedimentos, Mapa de Migração, Previsão.
- All figure objects and DataFrames are computed unconditionally at module level; rendering is conditional on `aba_selecionada`.

**Dual-theme support:**
- A sidebar radio selects "Escuro" (default) or "Claro".
- All Plotly layout dicts and Streamlit CSS injections are parameterised by `plotly_template`, `plotly_paper_bgcolor`, `plotly_plot_bgcolor`, `plotly_font_color`, and `plotly_axis_style`.

## Data Flow

### ETL Path (offline, periodic)

1. `app/scripts/script_atualizacao.py` — queries Jira REST API (`/rest/api/3/search/jql`) with `HTTPBasicAuth`, paginates results, writes `app/dados/FASE_3.csv` (one row per subtask).
2. `app/scripts/script_pendencias.py` — queries a specific epic (`BF3E4-293`), writes `app/dados/pendencias_BF3E4-293.csv` and `app/dados/historico_BF3E4-293.csv`.
3. `app/scripts/extrair_historico.py` — iterates over a hardcoded epic map (9 data-lake epics), fetches full status-change history, writes `app/dados/historico/historico_completo-{LAKE}.csv` per lake.

### Dashboard Runtime Path

```
app/dados/FASE_3.csv
    |
    v
carregar_dados_csv()          # data_loader.py: raw CSV parse, comma-in-title fallback
    | @st.cache_data(ttl=900)
    v
carregar_dados()              # dashboard.py: Streamlit cache wrapper
    |
    v
df (raw DataFrame)
    |
    v
Sidebar filters               # Data-Lake -> Historia -> Categoria chain
    |
    v
df_filtrado
    |
    v
Metric calculations           # inline in dashboard.py
    |
    v
Plotly figures                # built unconditionally at module scope
    |
    v
aba_selecionada branch        # renders the appropriate tab
```

### Burndown/Burnup calculation sub-flow

```
df_lake (from FASE_3.csv Jira dates OR datas_esperadas_por_lake.csv fallback)
    |
    v
burn_planejado (cumulative plan by data_fim)
    | merged with
burn_real (histories fully completed by max(Data Atualizacao))
    |
    v
projetar_burndown()           # calculations.py: linear projection +-30%
calcular_curva_aprendizado()  # calculations.py: sigmoid "expected delivery" curve
```

### Forecast tab sub-flow

```
burn_real_acum daily throughput array
    |
    v
monte_carlo_forecast()        # calculations.py: 5000-sim Monte Carlo -> P50/P85 dates
forecast_linear_range()       # calculations.py: linear best/current/worst scenarios
```

## Key Components

**`app/dashboard/dashboard.py`** (~2600 lines)
- Streamlit entry point; executed in full on every user interaction.
- Defines rendering functions: `_render_indicadores`, `_compute_heatmap_pivot`, `renderizar_tabela`.
- Builds all Plotly figure objects (`fig_burn`, `fig_burnup`, `fig_progress`, `fig_categoria`, `fig_data_lake`, `fig_critico`) at module scope before the tab branch.
- Contains duplicate implementations of some functions already in `calculations.py` (historical remnants): `calcular_dias_uteis`, `normalizar_id_historia`, `parse_data_criacao`.
- Imports from `calculations.py`: `calcular_curva_aprendizado`, `calcular_dias_uteis`, `colorir_status`, `normalizar_id_historia`, `parse_data_criacao`, `classificar_subtarefa`, `projetar_burndown`, `monte_carlo_forecast`, `forecast_linear_range`.

**`app/dashboard/calculations.py`** (~218 lines)
- Pure Python/NumPy/Pandas functions with zero Streamlit dependency.
- Designed for testability; all logic is covered by tests in `tests/`.
- Key functions: `calcular_curva_aprendizado` (sigmoid curve), `monte_carlo_forecast` (5000 simulations, seed=42), `forecast_linear_range` (best/current/worst), `projetar_burndown` (daily rate projection), `calcular_dias_uteis` (business days via numpy.busday_count), `classificar_subtarefa` (RN/RN-FMK/Story Bug classifier via regex).

**`app/dashboard/data_loader.py`** (~47 lines)
- `carregar_dados_csv(arquivo)` reads CSV with `utf-8-sig` encoding.
- Custom fallback parser handles rows where the `Titulo` field contains unquoted commas (assumes exactly 11 columns: 5 prefix + Titulo + 5 suffix).

**`app/scripts/script_atualizacao.py`**
- Main Jira extractor: project BF3E4, subtask level. Reads `EMAIL`/`API_TOKEN` from `.env`. Disables SSL verification (`verify=False`) for corporate network. Writes `app/dados/FASE_3.csv`.

**`app/scripts/script_pendencias.py`**
- Impedimento extractor for epic BF3E4-293. Converts Atlassian Document Format (ADF) JSON to plain text via `adf_para_texto()`. Writes `pendencias_BF3E4-293.csv` and `historico_BF3E4-293.csv`.

**`app/scripts/extrair_historico.py`**
- Status-change history extractor. Iterates over 9 hardcoded epics (one per data-lake). Writes `historico_completo-{LAKE}.csv` to `app/dados/historico/`.

## State Management

Streamlit has no persistent client-side state across reruns. Mechanisms used:

- **`@st.cache_data(ttl=900)`** — memoises `carregar_dados()` and `calcular_ciclo_desenvolvimento()` for 15 minutes. Invalidated by the "Atualizar dados" sidebar button via `st.cache_data.clear()` then `st.rerun()`.
- **Sidebar widgets** — `data_lake_selecionado`, `historia_selecionada`, `categoria_selecionada`, `aba_selecionada`, `tema_selecionado` drive all conditional rendering. Values persist across reruns via Streamlit's internal session state.
- **Module-level variables** — `df`, `df_filtrado`, `burn`, `fig_*` objects are recomputed on every script execution. No explicit `st.session_state` is used anywhere.

## Entry Points

**Dashboard:**
- `streamlit run app/dashboard/dashboard.py` — must be run from within `app/dashboard/` for relative imports to resolve.
- Streamlit config: `app/dashboard/.streamlit/config.toml` (dark theme, primaryColor #1f77b4).

**ETL scripts (run independently or via CI):**
- `python app/scripts/script_atualizacao.py` — primary data refresh.
- `python app/scripts/script_pendencias.py` — impedimento/blocker refresh.
- `python app/scripts/extrair_historico.py` — full history rebuild per lake.

## Error Handling

- `data_loader.py` catches `ParserError` and falls back to a manual line parser.
- `dashboard.py` calls `st.stop()` if `FASE_3.csv` is missing.
- `calcular_ciclo_desenvolvimento` wraps each file load in `except Exception: continue`.
- Date parsing is wrapped in `try/except Exception` that silently sets `issues_abertos_1_semana = 0` on failure.
- No structured logging; errors surface via `st.error()` inline or are silently swallowed.

## Cross-Cutting Concerns

**Data normalisation:**
- `Data-Lake` values normalised to uppercase via `.str.strip().str.upper()` in multiple callsites.
- History IDs normalised via `normalizar_id_historia()`: strips brackets, collapses whitespace, normalises hyphens.

**Theme:**
- Plotly template and CSS `st.markdown` injection both react to `tema_selecionado` resolved at dashboard startup.

**Timezone handling:**
- Jira timestamps arrive in UTC with timezone info. Converted to UTC then tz-stripped for Plotly display.

---

*Architecture analysis: 2026-03-26*
