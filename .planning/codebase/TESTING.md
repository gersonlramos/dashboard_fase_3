# Testing

**Analysis Date:** 2026-03-25

## Framework

- **None** — no test framework is installed or configured
- `requirements.txt` lists only runtime dependencies: `streamlit`, `plotly`, `pandas`, `numpy`, `requests`, `urllib3`, `python-dotenv`
- No `pytest`, `unittest`, `pytest-cov`, `hypothesis`, or similar packages present

## Test Organization

- **No test files exist** anywhere in the repository
- No `tests/` directory, no `test_*.py` files, no `*_test.py` files
- No `conftest.py`, `pytest.ini`, `setup.cfg [tool:pytest]`, or `pyproject.toml [tool.pytest]`

## Coverage

- **Current:** 0% — no tests exist
- **Configuration:** None — no coverage tool (`coverage.py`, `pytest-cov`) is configured

## Testing Patterns

No testing patterns are in use. The project has no unit tests, integration tests, or end-to-end tests.

## What's Well Tested

- **Nothing** — there is no automated test coverage for any component

## Testing Gaps

**`app/dashboard/dashboard.py` (2351 lines):**
- `calcular_curva_aprendizado()` — sigmoid math and edge-case inputs (zero totals, `NaT` dates) are not tested
- `carregar_dados()` — CSV parsing fallback logic (manual parser for comma-in-title edge case) is not tested
- `calcular_dias_uteis()` — business-day calculation is not tested
- `calcular_ciclo_desenvolvimento()` and `calcular_ciclo_ideal()` — aggregation over historic CSV files is not tested
- `_render_indicadores()` — progress percentage calculation and delta coloring are not tested
- `normalizar_id_historia()` — normalization logic is not tested

**`app/scripts/script_atualizacao.py`:**
- `extrair_data_lake()` — regex extraction from bracket notation is not tested
- `classificar_subtarefa()` — classification rules (`Story Bug`, `RN-FMK`, `RN`, fallback) are not tested
- `buscar_com_paginacao()` — pagination loop and `isLast`/`nextPageToken` logic are not tested

**`app/scripts/script_pendencias.py`:**
- `adf_para_texto()` — recursive ADF-to-plain-text conversion across all node types is not tested
- `_paginar_jql()` — pagination via `startAt` is not tested
- `buscar_issues_do_epico()` — two-level hierarchy traversal with deduplication is not tested
- `extrair_campos()` — field extraction and null-safe access patterns are not tested

**`app/scripts/extrair_historico.py`:**
- Entire script is untested; changelog parsing and CSV output format are not verified

## CI Integration

- The CI pipeline (`.github/workflows/atualizar_dados.yml`) runs **no tests**
- Workflow steps: checkout → setup Python 3.11 → `pip install -r requirements.txt` → run three extraction scripts → commit and push updated CSVs
- There is no test step, no lint step, and no quality gate of any kind in CI
- Pipeline runs on a schedule (weekdays at 05:00, 10:00, 14:00, 16:00 BRT) and on `workflow_dispatch`

## Recommendations for Adding Tests

**Highest-value targets (pure functions, no I/O side effects):**
- `extrair_data_lake()` in `app/scripts/script_atualizacao.py`
- `classificar_subtarefa()` in `app/scripts/script_atualizacao.py`
- `adf_para_texto()` in `app/scripts/script_pendencias.py`
- `calcular_dias_uteis()` in `app/dashboard/dashboard.py`
- `carregar_dados()` in `app/dashboard/dashboard.py` (with fixture CSV files)
- `calcular_curva_aprendizado()` in `app/dashboard/dashboard.py`

**Suggested setup:**
```
pip install pytest pytest-cov
```
```
tests/
├── test_script_atualizacao.py
├── test_script_pendencias.py
└── test_dashboard_utils.py
```

**Suggested `pytest` invocation in CI:**
```bash
pytest tests/ --cov=app --cov-report=term-missing
```
