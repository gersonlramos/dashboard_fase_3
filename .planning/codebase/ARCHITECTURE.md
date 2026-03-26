# Architecture

**Analysis Date:** 2026-03-25

## Pattern

Single-page data pipeline dashboard. The system is split into two distinct concerns:

1. **ETL Pipeline** — Python scripts that pull data from the Jira REST API and write CSV files to `app/dados/`
2. **Streamlit Dashboard** — a single-file SPA (`dashboard.py`) that reads those CSV files and renders an interactive web UI

There is no shared module layer or service layer between these two parts. They communicate exclusively through CSV files on the filesystem. The GitHub Actions workflow (`atualizar_dados.yml`) runs the ETL scripts on a schedule and commits updated CSVs back to the repo, keeping data fresh without any live Jira connection from the dashboard.

## Entry Points

- `app/dashboard/dashboard.py`: The Streamlit application. Executed via `streamlit run app/dashboard/dashboard.py`. All dashboard logic, data loading, computation, and rendering lives in this single file (2,351 lines).
- `app/scripts/script_atualizacao.py`: Main ETL script. Fetches all Epics → Stories → Subtasks from the Jira project `BF3E4` and writes `app/dados/FASE_3.csv` and `app/dados/processos_seguintes.csv`.
- `app/scripts/extrair_historico.py`: Fetches status-change changelogs for all Stories under each Epic and writes per-lake CSV files to `app/dados/historico/historico_completo-{LAKE}.csv`.
- `app/scripts/script_pendencias.py`: Fetches issues under epic `BF3E4-293` with full changelog and writes `app/dados/pendencias_BF3E4-293.csv` and `app/dados/historico_BF3E4-293.csv`.
- `.github/workflows/atualizar_dados.yml`: Triggers all three ETL scripts on a schedule (4× per weekday) and commits data changes back to `main`.

## Core Components

**Jira Data Extractor (`app/scripts/script_atualizacao.py`):**
- Authenticates with Jira Cloud REST API v3 at `https://fcagil.atlassian.net/rest/api/3/search/jql`
- Credentials loaded from `.env` via `python-dotenv` (env vars: `EMAIL`, `API_TOKEN`)
- Handles paginated JQL queries via `buscar_com_paginacao()` using `nextPageToken`
- Traverses 3 hierarchy levels: Epic → Story → Subtask
- Classifies subtasks into categories (`RN`, `RN-FMK`, `Story Bug`, `Desenvolvimento/Outros`) via `classificar_subtarefa()`
- Extracts Data-Lake identifier from story title bracket notation (e.g. `[FINANCE-1]`) via `extrair_data_lake()`
- Output: `app/dados/FASE_3.csv` with columns: `Epico, Historia, Titulo Historia, Data-Lake, Chave, Titulo, Status, Data Criacao, Data Atualizacao, Quantidade Subtarefas, Categoria_Analise, Start Date Historia, Deadline Historia`

**History Extractor (`app/scripts/extrair_historico.py`):**
- Fixed Epic-to-Lake mapping: 9 epics mapped to lake names (BMC, COMPRAS, MOPAR, CLIENTE, SHAREDSERVICES, RH, FINANCE, SUPPLYCHAIN, COMERCIAL)
- Fetches Stories under each Epic with `expand=changelog`
- Writes one CSV per lake: `app/dados/historico/historico_completo-{LAKE}.csv` with columns: `Chave, Titulo, Data Criacao, Data Mudanca, Status Antigo, Status Novo, Autor`

**Pendencies Extractor (`app/scripts/script_pendencias.py`):**
- Targets a single hardcoded Epic (`BF3E4-293`)
- Fetches 2-level hierarchy (direct children + subtasks) with changelog
- Writes both a pendencies CSV and a status-history CSV for that specific epic
- Includes `adf_para_texto()` to convert Atlassian Document Format JSON to plain text

**Streamlit Dashboard (`app/dashboard/dashboard.py`):**
- Monolithic single-file application
- Sections in execution order:
  1. Helper functions (`calcular_curva_aprendizado`, `calcular_dias_uteis`, `calcular_ciclo_desenvolvimento`, `calcular_ciclo_ideal`)
  2. Page config + theme setup (light/dark via sidebar radio; CSS injected via `st.markdown(unsafe_allow_html=True)`)
  3. Data loading: `carregar_dados()` reads `app/dados/FASE_3.csv` with CSV parse-error fallback
  4. Filter computations (sidebar filters: Data-Lake, Historia, Categoria)
  5. All metric and chart computations (burn-up/burn-down, projections, SLA indicators)
  6. Tab-based rendering: `📊 Executivo`, `📈 Gráficos`, `📋 Detalhes`, `⚠️ Pendências`

## Data Flow

```
Jira Cloud REST API
        │
        ▼
app/scripts/script_atualizacao.py  ──► app/dados/FASE_3.csv
app/scripts/extrair_historico.py   ──► app/dados/historico/historico_completo-{LAKE}.csv
app/scripts/script_pendencias.py   ──► app/dados/pendencias_BF3E4-293.csv
                                   ──► app/dados/historico_BF3E4-293.csv
        │
        │  (GitHub Actions commits CSVs to repo)
        │
        ▼
app/dados/ (CSV files on filesystem)
        │
        ▼
app/dashboard/dashboard.py
  carregar_dados() → pd.DataFrame
        │
        ├─ Sidebar filters (Data-Lake, Historia, Categoria)
        │         │
        │         ▼
        │   df_filtrado (filtered DataFrame)
        │
        ├─ Metric calculations (burn-up, burn-down, projections, SLA, cycle time)
        │
        └─ Tab rendering:
               📊 Executivo  →  KPI metrics, progress cards
               📈 Gráficos   →  Plotly charts (burn-up, burn-down, pie, bar, gauge)
               📋 Detalhes   →  Filterable HTML tables
               ⚠️ Pendências →  BF3E4-293 issues table
```

**Secondary data sources read by the dashboard:**
- `app/dados/datas_esperadas_por_lake.csv` — fallback for planned dates per story when `Start Date Historia`/`Deadline Historia` columns are absent from `FASE_3.csv`
- `app/dados/historico/historico_completo-{LAKE}.csv` — consumed by `calcular_ciclo_desenvolvimento()` to compute real development cycle time
- `app/dados/pendencias_BF3E4-293.csv` — rendered in the Pendencias tab
- `app/dados/historico_BF3E4-293.csv` — rendered in the Pendencias tab

## State Management

All state is Streamlit session state (implicit). There is no explicit `st.session_state` usage — all state derives from:
- Sidebar widget values (Data-Lake selectbox, Historia selectbox, Categoria selectbox, tab radio, theme radio)
- The filtered DataFrame `df_filtrado` recomputed on each render cycle
- All charts and metrics are recomputed from scratch on each Streamlit rerun triggered by widget interaction

No caching (`@st.cache_data`) is used. Every user interaction triggers a full script rerun from line 1.

## Key Design Decisions

- **CSV-as-database**: All data exchange between ETL scripts and dashboard uses CSV files committed to git. This avoids any database infrastructure but means the dashboard is always read-only and data is as fresh as the last GitHub Actions run.
- **Monolithic dashboard**: All 2,351 lines of the dashboard are in one file with no module imports from the project. This makes the file large but deployment trivial — a single `streamlit run` command.
- **Hardcoded project key**: The Jira project `BF3E4` and epic-to-lake mapping are hardcoded in the scripts. Changing project requires editing source code.
- **Scheduled CI refresh**: GitHub Actions runs extraction 4× per weekday (05:00, 10:00, 14:00, 16:00 BRT) and auto-commits data, so the deployed dashboard served from the repo always has up-to-date data without requiring the user to run scripts manually.
- **SSL verification disabled**: All Jira API calls use `verify=False` with `urllib3` warnings suppressed — a workaround for corporate proxy/certificate environments.
- **Dual theme**: The dashboard supports light and dark themes via sidebar toggle. Theme state is managed through CSS injection and Plotly template switching, not through Streamlit's built-in theme config.
- **Sigmoid learning curve**: A custom sigmoid function (`calcular_curva_aprendizado`) models expected team delivery acceleration, shown as "Entrega Esperada" line on burn-up charts.

---

*Architecture analysis: 2026-03-25*
