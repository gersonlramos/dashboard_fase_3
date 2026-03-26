# Project Structure

**Analysis Date:** 2026-03-26

## Directory Layout

```
dashboard_fase_3/
├── app/
│   ├── dados/                          # CSV data files (git-tracked, updated by ETL scripts)
│   │   ├── FASE_3.csv                  # Primary dataset: one row per Jira subtask
│   │   ├── datas_esperadas_por_lake.csv # Legacy planned dates per lake (fallback)
│   │   ├── processos_seguintes.csv     # Next-process reference data
│   │   ├── pendencias_BF3E4-293.csv    # Blocker/impedimento issues
│   │   ├── historico_BF3E4-293.csv     # Change history for blocker epic
│   │   └── historico/                  # Per-lake status-change history
│   │       ├── historico_completo-BMC.csv
│   │       ├── historico_completo-CLIENTE.csv
│   │       ├── historico_completo-COMERCIAL.csv
│   │       ├── historico_completo-COMPRAS.csv
│   │       ├── historico_completo-FINANCE.csv
│   │       ├── historico_completo-MOPAR.csv
│   │       ├── historico_completo-RH.csv
│   │       ├── historico_completo-SHAREDSERVICES.csv
│   │       └── historico_completo-SUPPLYCHAIN.csv
│   ├── dashboard/
│   │   ├── dashboard.py                # Streamlit entry point (~2600 lines)
│   │   ├── calculations.py             # Pure calculation functions (~218 lines)
│   │   ├── data_loader.py              # CSV loader with fallback parser (~47 lines)
│   │   └── .streamlit/
│   │       └── config.toml             # Streamlit theme (dark, blue primary)
│   └── scripts/
│       ├── script_atualizacao.py       # Jira ETL: extracts subtasks -> FASE_3.csv
│       ├── script_pendencias.py        # Jira ETL: extracts blockers -> pendencias_*.csv
│       └── extrair_historico.py        # Jira ETL: extracts status history -> historico/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Adds app/dashboard to sys.path
│   ├── test_calculations.py            # Unit tests for calculations.py functions
│   ├── test_forecast_calculations.py   # Tests for monte_carlo_forecast, forecast_linear_range
│   ├── test_data_loader_and_pendencias.py
│   ├── test_etl_atualizacao.py
│   ├── test_phase1.py
│   └── test_smoke.py                   # AppTest smoke test: dashboard loads without exception
├── conftest.py                         # Root conftest: adds app/dashboard to sys.path
├── pytest.ini                          # Pytest configuration
├── requirements.txt                    # Python dependencies
└── .planning/                          # GSD planning documents (not application code)
    ├── codebase/                       # Codebase analysis documents
    ├── phases/                         # Phase planning documents
    └── ...
```

## Key Files

**Application Entry Point:**
- `app/dashboard/dashboard.py` — the only file executed by `streamlit run`. Contains all UI rendering, data wrangling, figure construction, and tab branching logic.

**Calculation Library:**
- `app/dashboard/calculations.py` — pure functions imported by `dashboard.py` and tested independently. No Streamlit imports. Add new stateless computation here.

**Data Loading:**
- `app/dashboard/data_loader.py` — `carregar_dados_csv(arquivo)`. The only place that reads the primary CSV. Import in tests or scripts that need raw data loading.

**ETL Scripts:**
- `app/scripts/script_atualizacao.py` — run to refresh `FASE_3.csv` from Jira.
- `app/scripts/script_pendencias.py` — run to refresh `pendencias_BF3E4-293.csv`.
- `app/scripts/extrair_historico.py` — run to rebuild all per-lake history CSVs.

**Configuration:**
- `app/dashboard/.streamlit/config.toml` — Streamlit server/theme configuration.
- `requirements.txt` — pinned Python dependencies.

**Test Infrastructure:**
- `conftest.py` (root) — adds `app/dashboard` to `sys.path` so tests can `import calculations` directly.
- `tests/conftest.py` — secondary path setup for test-local imports.
- `pytest.ini` — pytest settings.

**Primary Data File:**
- `app/dados/FASE_3.csv` — main dataset, overwritten each time `script_atualizacao.py` runs. 11 columns including Titulo Historia, Data-Lake, Status, Categoria_Analise, Data Criacao, Data Atualizacao, Start Date Historia, Deadline Historia.

## Module Organization

The project has three logical layers:

**1. ETL layer** (`app/scripts/`)
- Standalone Python scripts. No shared module between them.
- Communicate with dashboard exclusively via CSV files in `app/dados/`.
- Require `EMAIL` and `API_TOKEN` env vars (from `.env` loaded via `python-dotenv`).

**2. Dashboard layer** (`app/dashboard/`)
- `data_loader.py` — I/O abstraction. Pure Python, no Streamlit.
- `calculations.py` — computation layer. Pure Python, no Streamlit.
- `dashboard.py` — orchestrates everything: loads data, applies filters, builds figures, renders tabs.

**3. Test layer** (`tests/`)
- Tests exercise `calculations.py` functions directly (unit) and `dashboard.py` via Streamlit `AppTest` (smoke/integration).

## Entry Points

**Run the dashboard:**
```bash
cd app/dashboard
streamlit run dashboard.py
```

**Run ETL to refresh data:**
```bash
python app/scripts/script_atualizacao.py
python app/scripts/script_pendencias.py
python app/scripts/extrair_historico.py
```

**Run tests:**
```bash
pytest
```

## Where to Add New Code

**New calculation or forecast algorithm:**
- Add to `app/dashboard/calculations.py` as a pure function.
- Add corresponding tests in `tests/test_calculations.py` or a new `tests/test_<name>.py`.
- Import the function at the top of `dashboard.py` in the existing import block (line 9-13).

**New dashboard tab/view:**
- Add the tab label to the `st.sidebar.radio` list at line ~604 in `dashboard.py`.
- Add an `elif aba_selecionada == "..."` branch at the bottom of `dashboard.py` following the existing pattern.
- Pre-compute any required figures/DataFrames at module level (before the tab branch) following the existing pattern.

**New ETL script:**
- Create a new file in `app/scripts/`.
- Output CSV to `app/dados/` following the existing naming pattern.
- Read `EMAIL`/`API_TOKEN` via `os.getenv()` after `load_dotenv()`.

**New data file:**
- Place in `app/dados/` (static reference data) or `app/dados/historico/` (per-lake history).
- Load in `dashboard.py` with `pd.read_csv(..., encoding='utf-8-sig')`.

## Special Directories

**`app/dados/`:**
- Purpose: all CSV data files consumed by the dashboard.
- Generated: yes (by ETL scripts and Jira automation).
- Committed: yes (CSV files are version-controlled so the dashboard works without running ETL).

**`app/dados/historico/`:**
- Purpose: per-lake Jira status-change history, one file per data-lake.
- Read by: `calcular_ciclo_desenvolvimento()` in `dashboard.py` via `glob`.

**`.venv/`:**
- Purpose: Python virtual environment.
- Committed: no (excluded by `.gitignore`).

**`.planning/`:**
- Purpose: GSD planning documents (architecture, conventions, phases, requirements).
- Committed: yes.

---

*Structure analysis: 2026-03-26*
