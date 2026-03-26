# Project Structure

**Analysis Date:** 2026-03-25

## Root Layout

```
dashboard_fase_3/
├── app/                        # All application code and data
│   ├── dados/                  # CSV data files (ETL output, read by dashboard)
│   │   └── historico/          # Per-lake status-change history CSVs
│   ├── dashboard/              # Streamlit web application
│   │   └── .streamlit/         # Streamlit configuration
│   └── scripts/                # Jira data extraction scripts
├── .devcontainer/              # GitHub Codespaces dev container config
├── .github/
│   └── workflows/              # GitHub Actions CI/CD workflows
├── .planning/
│   └── codebase/               # GSD architecture and planning documents
├── requirements.txt            # Python dependencies (pinned versions)
└── .gitignore                  # Excludes .env, __pycache__, etc.
```

## Source Organization

The codebase has no `src/` directory. Application code lives directly under `app/` split into two roles:

- `app/scripts/` — data producers (run by CI, write CSV files)
- `app/dashboard/` — data consumer (Streamlit app, reads CSV files)

Data flows one-way: scripts write to `app/dados/`, dashboard reads from `app/dados/`.

## Key Directories

**`app/dados/`:**
- Purpose: Persistent CSV data store. Acts as the interface layer between ETL and dashboard.
- Key files:
  - `FASE_3.csv` — main dataset (~1.4 MB); one row per Jira subtask with Epic/Story/Status/Dates
  - `datas_esperadas_por_lake.csv` — planned delivery dates per story (legacy fallback, ~75 KB)
  - `processos_seguintes.csv` — Epic list with keys, titles, statuses, dates
  - `pendencias_BF3E4-293.csv` — open issues for the Pendencias tab
  - `historico_BF3E4-293.csv` — status-change history for BF3E4-293 epic
- All files are committed to git and updated by GitHub Actions on each scheduled run.

**`app/dados/historico/`:**
- Purpose: Per-lake status-change history extracted from Jira changelogs.
- Naming pattern: `historico_completo-{LAKE}.csv` where LAKE is one of: `BMC`, `CLIENTE`, `COMERCIAL`, `COMPRAS`, `FINANCE`, `MOPAR`, `RH`, `SHAREDSERVICES`, `SUPPLYCHAIN`
- Consumed by `calcular_ciclo_desenvolvimento()` inside `dashboard.py` to compute real development cycle time metrics.

**`app/scripts/`:**
- Purpose: Jira data extraction scripts. Run by GitHub Actions workflow. Not imported by the dashboard.
- Files:
  - `script_atualizacao.py` — full project extraction (Epics → Stories → Subtasks); produces `FASE_3.csv`
  - `extrair_historico.py` — changelog extraction per epic/lake; produces `historico/historico_completo-{LAKE}.csv`
  - `script_pendencias.py` — targeted extraction for epic `BF3E4-293`; produces `pendencias_BF3E4-293.csv` and `historico_BF3E4-293.csv`

**`app/dashboard/`:**
- Purpose: The Streamlit web application.
- Files:
  - `dashboard.py` — entire application (2,351 lines); no submodules
  - `.streamlit/config.toml` — Streamlit theme configuration (dark theme defaults: `backgroundColor = "#0d1b2a"`, `primaryColor = "#1f77b4"`)

**`.github/workflows/`:**
- Purpose: CI/CD automation.
- `atualizar_dados.yml` — scheduled workflow (4× weekdays) that runs all three ETL scripts and auto-commits updated CSVs with message `chore: atualização automática dos dados Jira - {TIMESTAMP} [skip ci]`

**`.devcontainer/`:**
- Purpose: GitHub Codespaces configuration.
- `devcontainer.json` — uses `mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`, auto-installs requirements and starts Streamlit on port 8501.

## Module Boundaries

There are two logical modules with no shared code between them:

1. **ETL Module** (`app/scripts/`):
   - Each script is self-contained and standalone
   - Scripts share a common pattern: load `.env` → authenticate with Jira → paginate JQL → write CSV
   - No shared utility module between scripts (pagination logic is duplicated across files)
   - No imports from `app/dashboard/`

2. **Dashboard Module** (`app/dashboard/`):
   - Single-file Streamlit app with no internal imports from `app/scripts/`
   - Reads only from `app/dados/` via `os.path` relative to `SCRIPT_DIR`
   - Path resolution: `DADOS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'dados')`

## File Naming Conventions

**Python scripts:**
- ETL scripts: `snake_case` descriptive names — `script_atualizacao.py`, `script_pendencias.py`, `extrair_historico.py`
- Dashboard: single file, lowercase — `dashboard.py`

**CSV data files:**
- Main dataset: `UPPER_CASE` with underscores — `FASE_3.csv`
- History files: `snake_case-UPPERCASE` with a dash separator — `historico_completo-FINANCE.csv`
- Specific-epic files: `snake_case_{EPIC_KEY}` — `pendencias_BF3E4-293.csv`, `historico_BF3E4-293.csv`
- Planning reference: `snake_case` — `datas_esperadas_por_lake.csv`, `processos_seguintes.csv`

**Configuration files:**
- Streamlit config: `config.toml` (inside `.streamlit/` directory)
- Workflow: `atualizar_dados.yml` (snake_case)
- Dev container: `devcontainer.json`

## Where to Add New Code

**New ETL extraction script:**
- Place in `app/scripts/` following the existing pattern: load `.env`, authenticate, paginate JQL, write to `app/dados/`
- Register in `.github/workflows/atualizar_dados.yml` as a new step if it should run on schedule

**New CSV data source:**
- Write output to `app/dados/` from an ETL script
- Read from the dashboard using `os.path.join(DADOS_DIR, 'filename.csv')` pattern

**New per-lake history data:**
- Write to `app/dados/historico/historico_completo-{LAKE}.csv`
- The dashboard's `calcular_ciclo_desenvolvimento()` function uses `glob` to discover all files matching that pattern automatically

**New dashboard section/view:**
- Add a new option to the `aba_selecionada` radio widget in the sidebar
- Add a corresponding `if aba_selecionada == "..."` block in `dashboard.py` after line ~1429
- Pre-compute any needed DataFrames/figures before the tab rendering blocks (current pattern: all computations happen before the `if aba_selecionada` blocks)

**New Plotly chart:**
- Define the `go.Figure` or `px.*` call before the tab rendering blocks
- Respect `plotly_template`, `plotly_paper_bgcolor`, `plotly_plot_bgcolor`, `plotly_font_color`, `plotly_axis_style`, `plotly_legend_style` variables for theme consistency

---

*Structure analysis: 2026-03-25*
