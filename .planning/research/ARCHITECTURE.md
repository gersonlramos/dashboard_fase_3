# Architecture Research

**Researched:** 2026-03-25
**Domain:** Streamlit + pandas monolith testing and extension patterns
**Confidence:** HIGH (standard stack verified against official docs and current sources)

---

## Summary

The existing codebase is a 2,351-line `app/dashboard/dashboard.py` that mixes pure calculation functions, data-loading side effects, and Streamlit UI calls in a single top-to-bottom script. The navigation is driven by a sidebar radio widget (`aba_selecionada`) with four branches: Executivo, Graficos, Detalhes, Pendencias. Three ETL scripts in `app/scripts/` call the Jira REST API and write CSVs to `app/dados/`.

The goal is NOT a full refactor. It is (a) adding a test suite that exercises the existing calculation functions without touching their signatures, and (b) adding new views cleanly. Both are achievable with minimal structural changes.

**Primary recommendation:** Write a `tests/` directory at the project root, use `pytest` with a `conftest.py` that provides in-memory DataFrame fixtures built from small literal dicts (not from the real CSVs), and add new views by appending a new `elif` branch to the `aba_selecionada` radio block — the lowest-risk extension pattern for this codebase.

---

## Testing Without Full Refactor

### The Key Insight

The dashboard contains a set of functions that are already pure (or close to pure): they take DataFrames and primitives as arguments and return computed values. These can be tested directly with `pytest` by importing the module — **no AppTest, no Streamlit runtime needed**.

| Function | Purity | Can be unit-tested as-is? |
|---|---|---|
| `calcular_dias_uteis(data_inicio, data_fim)` | Pure | Yes |
| `calcular_curva_aprendizado(...)` | Pure | Yes |
| `normalizar_id_historia(valor)` | Pure | Yes |
| `carregar_dados(arquivo)` | IO side-effect (reads CSV) | Yes, with `tmp_path` fixture |
| `calcular_ciclo_desenvolvimento(...)` | Reads `glob` + file system | Yes, with `tmp_path` fixture |
| `calcular_ciclo_ideal(...)` | Reads module-level `df_lake` | Requires fixture patching |
| `colorir_status(val)` | Pure | Yes |
| `_render_indicadores(df_base)` | Calls `st.*` | Skip — UI concern |

### The Import Problem

`dashboard.py` executes Streamlit calls at module level (`st.set_page_config`, `st.sidebar.radio`, CSV loading, etc.). Importing it normally will fail or produce unexpected output. The workaround is **not** to import the module directly for unit tests, but instead to:

1. **Copy the pure functions** into a new `app/dashboard/calculations.py` module (or equivalent) so they can be imported cleanly. This is a low-risk extraction — not a refactor of the UI — and is the standard pre-refactor step recommended in the testing literature.

2. **Alternatively**, use `importlib` + environment variable patching, but this is fragile. The extraction approach is simpler and safer.

**Minimal extraction strategy (lowest risk):**

Move these six functions verbatim from `dashboard.py` into `app/dashboard/calculations.py` without changing their signatures or logic:
- `calcular_dias_uteis`
- `calcular_curva_aprendizado`
- `normalizar_id_historia`
- `carregar_dados`
- `colorir_status`
- `classificar_subtarefa` (currently in `script_atualizacao.py` — duplicate extraction)

Then add one import line to `dashboard.py`:
```python
from calculations import (
    calcular_dias_uteis, calcular_curva_aprendizado,
    normalizar_id_historia, carregar_dados, colorir_status
)
```

This is the only structural change needed to enable unit tests. The monolith's behavior is unchanged.

### Streamlit AppTest (for smoke testing only)

`streamlit.testing.v1.AppTest` is the official framework for testing whole Streamlit apps without a browser. It runs the script in a headless mode and lets you assert on widget states.

**Limitations relevant to this project:**
- Cache from `@st.cache_data` persists between `AppTest` instances in the same process — known bug (GitHub issue #9139). Workaround: call `st.cache_data.clear()` in test teardown.
- Requires the full script to run without errors — any import-time failure or missing CSV will abort the test.
- Sidebar `st.radio` IS supported via `at.sidebar.radio`.
- Does NOT test the visual output (HTML/CSS injected via `unsafe_allow_html`).

**Verdict for this project:** Use `AppTest` only for a single top-level smoke test that verifies the app runs and the four sidebar views load without exception. Unit test all calculations separately. Do not use `AppTest` as the primary test strategy.

---

## Test Directory Structure

### Recommended Layout

```
dashboard_fase_3/           <- project root / pytest rootdir
├── app/
│   ├── dados/              <- CSV data files (not in tests)
│   ├── dashboard/
│   │   ├── dashboard.py    <- monolith (unchanged)
│   │   └── calculations.py <- extracted pure functions (new)
│   └── scripts/
│       ├── script_atualizacao.py
│       ├── script_pendencias.py
│       └── extrair_historico.py
├── tests/
│   ├── conftest.py         <- shared fixtures (DataFrames, tmp CSV files)
│   ├── test_calculations.py
│   ├── test_etl_atualizacao.py
│   ├── test_etl_pendencias.py
│   └── test_etl_historico.py
├── pytest.ini              <- rootdir anchor + testpaths
└── requirements.txt
```

### Why `tests/` at project root (not inside `app/`)

- pytest's `rootdir` resolution looks for configuration files (e.g., `pytest.ini`) walking up from the test path. Placing `pytest.ini` at the project root and `tests/` alongside it is the official pytest recommendation for non-`src`-layout projects.
- Keeps test code clearly separated from application code.
- Avoids confusion with `app/` being both the source and test tree.

### `pytest.ini` (minimal)

```ini
[pytest]
testpaths = tests
addopts = -ra -q
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

This anchors the rootdir to the project root so that relative imports and `DADOS_DIR` resolution inside `dashboard.py` remain correct.

### `__init__.py` files

Do NOT add `__init__.py` to `tests/`. pytest discovers test files by path, not by Python package structure. Adding `__init__.py` to `tests/` causes import confusion with the `importlib` import mode. Leave `tests/` as a plain directory.

---

## pytest Fixtures for CSV Data

### Core Pattern: Build fixtures from literal dicts, not from real CSVs

The real CSVs are large and change with every CI run. Tests must be hermetic. Build minimal DataFrames in-memory that contain only the columns and rows each test needs.

### `tests/conftest.py`

```python
import io
import textwrap
import pytest
import pandas as pd


# ------------------------------------------------------------------
# FASE_3.csv schema:
# Epico, Historia, Titulo Historia, Data-Lake, Chave, Titulo,
# Status, Data Criacao, Data Atualizacao, Quantidade Subtarefas,
# Categoria_Analise, Start Date Historia, Deadline Historia
# ------------------------------------------------------------------

@pytest.fixture
def df_subtarefas_minimal():
    """Minimal FASE_3.csv equivalent — 4 rows, 2 lakes, mixed statuses."""
    return pd.DataFrame({
        "Epico": ["BF3E4-1", "BF3E4-1", "BF3E4-2", "BF3E4-2"],
        "Historia": ["BF3E4-10", "BF3E4-10", "BF3E4-20", "BF3E4-20"],
        "Titulo Historia": [
            "[BMC - 1] Entidade: BMC",
            "[BMC - 1] Entidade: BMC",
            "[COMERCIAL - 2] Entidade: X",
            "[COMERCIAL - 2] Entidade: X",
        ],
        "Data-Lake": ["BMC", "BMC", "COMERCIAL", "COMERCIAL"],
        "Chave": ["BF3E4-101", "BF3E4-102", "BF3E4-201", "BF3E4-202"],
        "Titulo": ["Task A", "Task B", "Task C", "Task D"],
        "Status": ["Done", "Open", "Done", "Done"],
        "Data Criacao": [
            "2026-01-10T10:00:00.000-0300",
            "2026-01-10T10:00:00.000-0300",
            "2026-01-15T10:00:00.000-0300",
            "2026-01-15T10:00:00.000-0300",
        ],
        "Data Atualizacao": [
            "2026-02-01T10:00:00.000-0300",
            "2026-02-05T10:00:00.000-0300",
            "2026-02-10T10:00:00.000-0300",
            "2026-02-10T10:00:00.000-0300",
        ],
        "Quantidade Subtarefas": [0, 0, 0, 0],
        "Categoria_Analise": [
            "Desenvolvimento/Outros",
            "RN",
            "Desenvolvimento/Outros",
            "RN-FMK",
        ],
        "Start Date Historia": [
            "2026-01-10", "2026-01-10", "2026-01-15", "2026-01-15"
        ],
        "Deadline Historia": [
            "2026-03-01", "2026-03-01", "2026-04-01", "2026-04-01"
        ],
    })


@pytest.fixture
def df_historico_minimal():
    """Minimal historico_completo-*.csv equivalent."""
    return pd.DataFrame({
        "Chave": ["BF3E4-10", "BF3E4-10", "BF3E4-20"],
        "Titulo": ["[BMC - 1] Entidade: BMC", "[BMC - 1] Entidade: BMC", "[COMERCIAL - 2] X"],
        "Data Criacao": [
            "2026-02-24T12:53:16.393-0300",
            "2026-02-24T12:53:16.393-0300",
            "2026-02-24T12:53:16.393-0300",
        ],
        "Data Mudanca": [
            "2026-03-17T10:59:06.678-0300",
            "2026-03-09T11:09:17.678-0300",
            "2026-03-10T10:00:00.000-0300",
        ],
        "Status Antigo": ["To Do", "Refined", "To Do"],
        "Status Novo": ["IN DEVELOPMENT", "To Do", "IN DEVELOPMENT"],
        "Autor": ["user1", "user2", "user1"],
    })


@pytest.fixture
def fase3_csv_file(tmp_path, df_subtarefas_minimal):
    """Write df_subtarefas_minimal to a temp CSV file, return the Path."""
    p = tmp_path / "FASE_3.csv"
    df_subtarefas_minimal.to_csv(p, index=False, encoding="utf-8-sig")
    return p


@pytest.fixture
def historico_dir(tmp_path, df_historico_minimal):
    """Create a temp historico/ subdirectory with one per-lake CSV."""
    h = tmp_path / "historico"
    h.mkdir()
    path = h / "historico_completo-BMC.csv"
    df_historico_minimal.to_csv(path, index=False, encoding="utf-8-sig")
    return h
```

### Fixture scoping strategy

| Fixture | Scope | Reason |
|---|---|---|
| `df_subtarefas_minimal` | `function` (default) | Cheap to create; each test gets a fresh copy so mutations don't leak |
| `df_historico_minimal` | `function` (default) | Same reason |
| `fase3_csv_file` | `function` | `tmp_path` is function-scoped by pytest |
| `historico_dir` | `function` | `tmp_path` is function-scoped by pytest |

Do NOT use `scope="session"` for DataFrame fixtures. DataFrames are mutable and a test that modifies one will silently corrupt subsequent tests.

### Asserting DataFrame equality

```python
import pandas as pd

# Exact equality
pd.testing.assert_frame_equal(result, expected)

# Ignore column order (useful when function reorders columns)
pd.testing.assert_frame_equal(result, expected, check_like=True)

# Ignore dtypes (useful when CSV round-trip changes int -> float)
pd.testing.assert_frame_equal(result, expected, check_dtype=False)
```

### Pattern: Test calculation functions with in-memory data

```python
# tests/test_calculations.py
import pandas as pd
import numpy as np
import pytest
from app.dashboard.calculations import calcular_dias_uteis, normalizar_id_historia


def test_calcular_dias_uteis_normal():
    d1 = pd.Timestamp("2026-01-05")  # Monday
    d2 = pd.Timestamp("2026-01-09")  # Friday
    assert calcular_dias_uteis(d1, d2) == 4


def test_calcular_dias_uteis_same_day():
    d = pd.Timestamp("2026-01-05")
    assert calcular_dias_uteis(d, d) == 0


def test_calcular_dias_uteis_reversed():
    d1 = pd.Timestamp("2026-01-09")
    d2 = pd.Timestamp("2026-01-05")
    assert calcular_dias_uteis(d1, d2) == 0


def test_calcular_dias_uteis_na():
    assert calcular_dias_uteis(pd.NaT, pd.Timestamp("2026-01-09")) == 0


def test_normalizar_id_historia_strips_brackets():
    assert normalizar_id_historia("[BMC - 1]") == "BMC-1"


def test_normalizar_id_historia_na():
    assert normalizar_id_historia(np.nan) is None
```

---

## Adding New Views to Existing Streamlit App

### How the current navigation works

The app uses a sidebar radio button (not `st.tabs`) to select the active view:

```python
# dashboard.py line ~488
aba_selecionada = st.sidebar.radio(
    "Visualize:",
    ["Executivo", "Graficos", "Detalhes", "Pendencias"],
    label_visibility="collapsed"
)
```

All view rendering is in `if/elif` branches further down the file:

```python
if aba_selecionada == "Executivo":
    ...
elif aba_selecionada == "Graficos":
    ...
elif aba_selecionada == "Detalhes":
    ...
elif aba_selecionada == "Pendencias":
    ...
```

### Pattern: Add a new view without breaking existing ones

**Step 1.** Add the new label to the radio list:

```python
aba_selecionada = st.sidebar.radio(
    "Visualize:",
    ["Executivo", "Graficos", "Detalhes", "Pendencias", "Nova View"],
    label_visibility="collapsed"
)
```

**Step 2.** Add a new `elif` at the END of the if/elif chain:

```python
elif aba_selecionada == "Nova View":
    _render_nova_view(df_filtrado)
```

**Step 3.** Define `_render_nova_view` as a function BEFORE the if/elif block (follow the existing pattern of `_render_indicadores`):

```python
def _render_nova_view(df_base):
    st.subheader("Nova View")
    # ... rendering logic ...
```

### Why this works safely

- Existing `elif` branches are not touched — zero risk of regression.
- All shared calculations (burndown, burnup, `df_filtrado`, etc.) run once before the if/elif block. The new view can use any of these without re-computing them.
- Streamlit reruns the full script on interaction; the new branch only renders its content when selected. When not selected, it is skipped entirely.

### Anti-patterns to avoid

- **Do NOT** move existing view code around to "clean it up" as part of adding a new view. Each code movement is a potential regression.
- **Do NOT** introduce a new shared variable in the module-level calculation section unless it is genuinely needed by the new view and its computation cost is acceptable (or it is cached with `@st.cache_data`).
- **Do NOT** use `st.tabs()` as a replacement for the sidebar radio — the existing navigation is intentional and users are accustomed to it. Adding `st.tabs()` inside a view IS acceptable if it is scoped to that view only.

### Where to place new view functions

Place all new rendering functions in the block that starts at `# Funções de renderização de tabelas` (~line 1168). This section is the established location for render helpers. Place new functions there rather than scattering them near the if/elif block.

---

## ETL Script Testing Strategy

### Structure of the existing ETL scripts

All three scripts (`script_atualizacao.py`, `script_pendencias.py`, `extrair_historico.py`) share this pattern:

1. Module-level setup: `load_dotenv()`, `requests` auth, hardcoded URLs.
2. Pure helper functions: `extrair_data_lake`, `classificar_subtarefa`, `buscar_com_paginacao`.
3. Top-level script execution: direct `requests.get` calls outside any function.

This means the helper functions CAN be unit-tested by import. The top-level script execution CANNOT be imported without triggering real API calls.

### Recommended split

| Test Type | What It Tests | How | CI? |
|---|---|---|---|
| Unit | Pure transform functions | Import function, call with literal data | Always |
| Unit | `carregar_dados` / CSV parsing | Use `tmp_path` fixture | Always |
| Integration | Full pipeline run | Marked `@pytest.mark.integration`, skipped by default | Manual / scheduled |

### Unit test pattern: mock `requests.get`

Use `unittest.mock.patch` (built-in, no extra dependency):

```python
# tests/test_etl_atualizacao.py
import json
from unittest.mock import patch, MagicMock
import pytest
import sys
import os

# Add app/scripts to path so we can import helper functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "scripts"))

from script_atualizacao import (
    extrair_data_lake,
    classificar_subtarefa,
    buscar_com_paginacao,
)


# ── Pure function tests (no mocking needed) ──────────────────────

def test_extrair_data_lake_brackets():
    assert extrair_data_lake("[BMC - 1] Entidade") == "BMC"


def test_extrair_data_lake_no_brackets():
    assert extrair_data_lake("Sem colchetes") == "N/A"


def test_extrair_data_lake_none():
    assert extrair_data_lake(None) == "N/A"


def test_classificar_subtarefa_rn_fmk():
    assert classificar_subtarefa("RN-FMK ajuste") == "RN-FMK"


def test_classificar_subtarefa_rn():
    assert classificar_subtarefa("[RN] Regra") == "RN"


def test_classificar_subtarefa_story_bug():
    assert classificar_subtarefa("Story Bug correction") == "Story Bug"


def test_classificar_subtarefa_default():
    assert classificar_subtarefa("Implementacao normal") == "Desenvolvimento/Outros"


# ── Mock-based test for paginated API function ────────────────────

def _make_response(issues, is_last=True, next_page_token=None):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "issues": issues,
        "isLast": is_last,
        "nextPageToken": next_page_token,
    }
    return mock


def test_buscar_com_paginacao_single_page():
    fake_issues = [{"key": "BF3E4-1"}, {"key": "BF3E4-2"}]
    with patch("script_atualizacao.requests.get") as mock_get:
        mock_get.return_value = _make_response(fake_issues, is_last=True)
        result = buscar_com_paginacao("project=X", "key,summary", auth=None)
    assert result == fake_issues
    assert mock_get.call_count == 1


def test_buscar_com_paginacao_two_pages():
    page1 = [{"key": "BF3E4-1"}]
    page2 = [{"key": "BF3E4-2"}]
    responses = [
        _make_response(page1, is_last=False, next_page_token="tok2"),
        _make_response(page2, is_last=True),
    ]
    with patch("script_atualizacao.requests.get") as mock_get:
        mock_get.side_effect = responses
        result = buscar_com_paginacao("project=X", "key,summary", auth=None)
    assert result == page1 + page2
    assert mock_get.call_count == 2


def test_buscar_com_paginacao_api_error():
    mock = MagicMock()
    mock.status_code = 401
    mock.text = "Unauthorized"
    with patch("script_atualizacao.requests.get", return_value=mock):
        result = buscar_com_paginacao("project=X", "key,summary", auth=None)
    assert result == []
```

### Integration test pattern (optional, gated)

```python
# tests/test_etl_integration.py
import pytest

@pytest.mark.integration
def test_full_pipeline_against_jira():
    """Requires JIRA_EMAIL and JIRA_API_TOKEN env vars. Skip in CI by default."""
    import os
    if not os.getenv("JIRA_API_TOKEN"):
        pytest.skip("No JIRA credentials — integration test skipped")
    # ... call the full script via subprocess or direct function calls
```

Run integration tests explicitly: `pytest -m integration`

Exclude them in normal CI: `pytest -m "not integration"` (add to `pytest.ini` as default: `addopts = -ra -q -m "not integration"`).

### What NOT to do

- **Do not** use `responses` or `requests-mock` libraries. The standard library `unittest.mock.patch` is sufficient and adds zero dependencies.
- **Do not** try to import the full ETL scripts (they execute at module level). Import only the helper functions by targeting the module with `sys.path.insert`.
- **Do not** write integration tests that hit the real Jira API in CI — credentials are not available in pull request builds and the tests become flaky.

---

## Common Pitfalls

### Pitfall 1: Importing dashboard.py triggers Streamlit execution
**What goes wrong:** `import dashboard` at test time calls `st.set_page_config`, tries to load CSVs from `DADOS_DIR`, and either crashes or opens a Streamlit server.
**Why it happens:** The entire script body runs on import.
**How to avoid:** Extract the functions you want to test into `calculations.py` first. Only import that module in tests.
**Warning signs:** `streamlit.errors.StreamlitAPIException` or `FileNotFoundError` for `FASE_3.csv` during pytest collection.

### Pitfall 2: DADOS_DIR is relative to the script's location
**What goes wrong:** `carregar_dados` resolves `DADOS_DIR` using `os.path.dirname(os.path.abspath(__file__))`. When called from tests, `__file__` is still `calculations.py` — which is fine — but if the test moves the script, the path breaks.
**How to avoid:** Accept the CSV path as a parameter in `carregar_dados` (it already does this: `def carregar_dados(arquivo)`). Pass `tmp_path / "FASE_3.csv"` from the fixture. Do not change `DADOS_DIR` resolution.
**Warning signs:** `FileNotFoundError` in tests even though the fixture created the file.

### Pitfall 3: `fillna(method='ffill')` FutureWarning breaks on pandas 3.x
**What goes wrong:** `dashboard.py` line 48 uses `fillna(method='ffill')`. On pandas 2.2.x this emits a `FutureWarning`. On pandas 3.0 it raises `TypeError`.
**Why it happens:** Deprecated API call.
**How to avoid:** Replace with `.ffill()` (a separate task). Tests will surface this warning immediately — add `filterwarnings = error::FutureWarning` to `pytest.ini` to make it a test failure.
**Warning signs:** `FutureWarning: DataFrame.fillna with 'method' is deprecated` in pytest output.

### Pitfall 4: `applymap` is renamed `map` in pandas 2.1+
**What goes wrong:** If `applymap` is used in `calculations.py` (it exists in the styling path), tests will emit `FutureWarning` or raise on pandas 2.1+.
**How to avoid:** Replace with `.map()`. Same `filterwarnings` setting above will surface this.

### Pitfall 5: Cache contamination between AppTest instances
**What goes wrong:** When multiple `AppTest.from_file(...).run()` calls share the same Python process, `@st.cache_data` caches persist across tests, so the second test sees stale data.
**How to avoid:** Add a teardown in any `AppTest`-based test:
```python
import streamlit as st
@pytest.fixture(autouse=True)
def clear_st_cache():
    yield
    st.cache_data.clear()
```
**Warning signs:** Second test in a sequence returns unexpected data from the first test's fixture.

### Pitfall 6: Adding a new sidebar option changes the radio widget index
**What goes wrong:** `st.sidebar.radio(..., index=0)` hardcodes the default selection by position. If a new option is inserted at any position other than the end, the default selection changes.
**How to avoid:** Always append new options at the END of the radio list. Never insert in the middle.
**Warning signs:** The Executivo view no longer loads as the default after adding a new view.

---

## Environment Availability

This section covers what is needed to run the test suite.

| Dependency | Required By | Available on target machine | Notes |
|---|---|---|---|
| Python 3.11 | All tests | Assumed yes (existing project) | `python3 --version` |
| pytest | Test runner | Not yet installed | Add to `requirements-dev.txt` |
| pandas 2.2.3 | All fixtures, calculations | Yes (in requirements.txt) | Already in use |
| numpy 2.2.1 | `calcular_curva_aprendizado`, `calcular_dias_uteis` | Yes (in requirements.txt) | Already in use |
| streamlit 1.55.0 | AppTest smoke test only | Yes (in requirements.txt) | Already in use |
| requests (stdlib mock) | ETL test mocking | Built into Python 3.x | No extra install |
| pytest-cov (optional) | Coverage reporting | Not yet installed | Optional, not required |

### Recommended `requirements-dev.txt` (new file)

```
pytest>=8.3
pytest-cov>=6.0
```

No other test dependencies are needed. Do not install `pytest-mock`, `responses`, or `requests-mock` — `unittest.mock` from stdlib is sufficient for this project's mocking needs.

---

## Sources

### Primary (HIGH confidence)
- [Streamlit AppTest get-started](https://docs.streamlit.io/develop/concepts/app-testing/get-started) — AppTest framework, minimal test example, limitations
- [Streamlit AppTest API reference](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) — widget interaction API
- [pytest good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) — directory structure, importlib mode, rootdir resolution
- [pytest fixtures reference](https://docs.pytest.org/en/stable/reference/fixtures.html) — scope, conftest.py, tmp_path

### Secondary (MEDIUM confidence)
- [pytest-with-eric: external API testing](https://pytest-with-eric.com/api-testing/pytest-external-api-testing/) — unit vs integration split, dependency injection vs raw mocking
- [Medium: Automated Testing for Streamlit with Pytest](https://medium.com/@shingurding/automated-testing-for-streamlit-apps-with-pytest-a0dd6e56c86d) — AppTest patterns
- [GitHub issue #9139: cache between AppTest instances](https://github.com/streamlit/streamlit/issues/9139) — confirmed bug, `st.cache_data.clear()` workaround

### Codebase analysis (verified by direct file read)
- `app/dashboard/dashboard.py` lines 14, 278, 383, 488, 591, 740, 772, 1169, 1185 — function signatures and navigation structure
- `app/scripts/script_atualizacao.py` lines 35–98 — ETL helper functions and `buscar_com_paginacao` signature
- `app/dados/FASE_3.csv` header row — 13-column schema verified
- `app/dados/historico/historico_completo-BMC.csv` header row — 7-column schema verified

---

**Confidence breakdown:**
- Testing without refactor: HIGH — based on direct codebase analysis + official AppTest docs
- Test directory structure: HIGH — official pytest documentation
- conftest.py patterns: HIGH — based on actual CSV schema from codebase + official pytest fixture docs
- Adding new views: HIGH — based on direct reading of the navigation pattern in dashboard.py
- ETL testing strategy: HIGH — `unittest.mock` is stdlib, patterns verified against official Python docs

**Research date:** 2026-03-25
**Valid until:** 2026-09-25 (stable ecosystem — pandas, pytest, streamlit testing APIs change slowly)
