# Testing

**Analysis Date:** 2026-03-26

## Testing Strategy

The project has a full pytest test suite built incrementally across phases 3–6. Tests are separated into unit tests (pure functions, no I/O side effects), integration tests (real CSV parsing with `tmp_path`), mock-based tests (HTTP pagination), and one smoke test (full Streamlit AppTest run).

**Core constraint:** `dashboard.py` cannot be directly imported in tests because `st.set_page_config()` runs at module scope and crashes outside a Streamlit context. This is solved by extracting testable logic to `app/dashboard/calculations.py` and `app/dashboard/data_loader.py`.

---

## Test Framework

**Runner:** pytest (no pinned version in `requirements.txt` — installed as `pytest`)
**Config:** `pytest.ini` at project root

```ini
[pytest]
filterwarnings =
    error::FutureWarning
    ignore::urllib3.exceptions.InsecureRequestWarning
```

`FutureWarning` is promoted to error — any deprecated pandas API usage (e.g., `fillna(method=)`, `applymap`) will fail the test run.

**Assertion library:** pytest built-in (`assert`), `pytest.approx` for float comparisons

**Mocking:** `unittest.mock` — `MagicMock`, `patch`

**Streamlit testing:** `streamlit.testing.v1.AppTest` for the smoke test

**Run commands:**
```bash
pytest                          # run all tests
pytest tests/test_calculations.py   # run one file
pytest -k "TestCarregarDados"       # run by name pattern
pytest -v                       # verbose output
```

No coverage tool is configured. To add coverage:
```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

## Test File Organization

All tests live in `tests/` at the project root. Tests are **not** co-located with source files.

```
tests/
├── __init__.py
├── conftest.py                          # shared fixture: sample_df
├── test_calculations.py                 # TEST-02 through TEST-06
├── test_data_loader_and_pendencias.py   # TEST-10, TEST-11
├── test_etl_atualizacao.py              # TEST-08, TEST-09
├── test_forecast_calculations.py        # monte_carlo_forecast, forecast_linear_range
├── test_phase1.py                       # FIX-01 through FIX-04 regression tests
└── test_smoke.py                        # TEST-07 AppTest smoke test
```

**Naming:** test files follow `test_{module_or_domain}.py`. Test classes follow `Test{FunctionName}` (PascalCase). Test methods follow `test_{scenario_description}` (snake_case).

---

## Test Structure

**Class-based grouping for related tests:**
```python
class TestCalcularCurvaAprendizado:
    def test_returns_two_lists_same_length(self): ...
    def test_sigmoid_first_value_near_zero(self): ...
    def test_nat_start_returns_empty(self): ...
```

**Function-level tests for standalone scenarios** (no class wrapper) in `test_forecast_calculations.py` and `test_phase1.py`.

**Section dividers** separate test classes within a file:
```python
# ── TEST-02: calcular_curva_aprendizado ──────────────────────────────────────
```

**Shared fixture** in `tests/conftest.py`:
```python
@pytest.fixture
def sample_df():
    """Minimal DataFrame matching FASE_3.csv schema for unit tests."""
    rows = [...]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df['Data Criacao'] = pd.to_datetime(df['Data Criacao'])
    return df
```

**Class-level shared args** using a class dict:
```python
class TestProjetarBurndown:
    BASE_ARGS = dict(
        historias_faltantes=4.0,
        total_planejado=10.0,
        realizado_atual=6.0,
        ultima_data_real_bh=pd.Timestamp('2026-03-01'),
    )
    def test_returns_nonempty_on_valid_input(self):
        datas, valores = projetar_burndown(ritmo=2.0, prazo_limite=pd.NaT, **self.BASE_ARGS)
```

---

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `patch`)

**HTTP mocking pattern** (used in `tests/test_etl_atualizacao.py`):
```python
def _make_response(status_code, json_data):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.text = str(json_data)
    return r

def test_single_page_returns_all_issues(self):
    resp = _make_response(200, {'issues': [issue], 'isLast': True})
    with patch('script_atualizacao.requests.get', return_value=resp) as mock_get:
        result = script_atualizacao.buscar_com_paginacao(...)
    assert mock_get.call_count == 1
```

**What is mocked:** External HTTP calls (`requests.get`) in ETL tests, Streamlit cache (`st.cache_data.clear()`) in smoke test.

**What is NOT mocked:** File I/O — `tmp_path` fixture is used to write real temp CSV files and load them through `carregar_dados_csv`.

---

## Fixtures and Factories

**`tests/conftest.py` — `sample_df`:** A 3-row DataFrame matching the `FASE_3.csv` schema. Available to all tests in the suite.

**`tests/test_data_loader_and_pendencias.py` — `_write_csv`:** A helper method (not a pytest fixture) that writes CSV content to a `tmp_path` temp file:
```python
def _write_csv(self, tmp_path, rows):
    p = tmp_path / 'test_fase3.csv'
    content = '\n'.join([CSV_HEADER] + rows)
    p.write_text(content, encoding='utf-8-sig')
    return str(p)
```

**`tests/test_smoke.py` — `clear_cache` (autouse):** Clears Streamlit's `@st.cache_data` before and after each test to prevent stale state across runs.

---

## Parametrize Usage

`@pytest.mark.parametrize` is used for value-variant tests:
```python
@pytest.mark.parametrize("status", ['Done', 'Closed', 'Resolved', 'Concluído', 'Concluida'])
def test_done_statuses_return_green(self, status):
    assert '#90EE90' in colorir_status(status)
```

---

## Coverage

**Configured target:** None — no coverage tool installed or configured.

**What is tested:**

| Module | Functions Tested |
|--------|-----------------|
| `app/dashboard/calculations.py` | `calcular_curva_aprendizado`, `calcular_dias_uteis`, `colorir_status`, `normalizar_id_historia`, `parse_data_criacao`, `classificar_subtarefa`, `projetar_burndown`, `monte_carlo_forecast`, `forecast_linear_range` |
| `app/dashboard/data_loader.py` | `carregar_dados_csv` (including BOM handling, empty file, missing file, fallback parser) |
| `app/scripts/script_atualizacao.py` | `extrair_data_lake`, `classificar_subtarefa`, `buscar_com_paginacao` (single-page, multi-page, 401, missing token) |
| `app/scripts/script_pendencias.py` | `adf_para_texto` (all node types: text, hardBreak, paragraph, heading, bulletList, orderedList, doc, unknown) |
| `app/dashboard/dashboard.py` | Smoke test only (AppTest loads page without exception); individual functions not directly importable |

**Test count by file:**
- `test_calculations.py`: ~37 tests across 6 classes
- `test_data_loader_and_pendencias.py`: ~19 tests across 2 classes
- `test_etl_atualizacao.py`: ~20 tests across 3 classes
- `test_forecast_calculations.py`: 4 standalone tests
- `test_phase1.py`: ~15 regression tests (FIX-01 through FIX-04)
- `test_smoke.py`: 1 smoke test

**What is NOT tested:**
- `app/scripts/extrair_historico.py` — no tests at all
- `dashboard.py` rendering logic (tabs, charts, filters, heatmap, timeline/forecast view) — only the top-level load is smoke-tested
- `_compute_heatmap_pivot` and other dashboard-internal private functions

---

## Smoke Test

`tests/test_smoke.py` uses Streamlit's `AppTest` framework to verify the dashboard renders without raising an exception:

```python
def test_dashboard_loads_without_exception():
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=60)
    at.run()
    assert not at.exception, f"Dashboard raised: {at.exception}"
```

This test requires real CSV data files in `app/dados/` to be present. It may be slow (~5–10 seconds).

---

## sys.path Management

Because there are no `__init__.py` files and the project is not installed as a package, each test file that imports from `app/` inserts the path explicitly:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'dashboard'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'scripts'))
```

The root `conftest.py` also inserts `app/dashboard` so that `AppTest.from_file(dashboard.py)` can resolve `from calculations import (...)` correctly.

---

## CI Integration

The CI workflow (`.github/workflows/atualizar_dados.yml`) runs **no tests** — it only executes the data-extraction scripts and commits updated CSVs. Tests must be run manually:

```bash
cd dashboard_fase_3
pytest
```
