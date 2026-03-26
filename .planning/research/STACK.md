# Stack Research

**Researched:** 2026-03-25
**Domain:** Streamlit 1.55 / Pandas 2.1.4 / Python 3.12.5 — testing, deprecations, caching
**Confidence:** HIGH (all claims verified against official docs or confirmed by running code in the actual project environment)

---

## Streamlit Testing (2025)

### Two distinct strategies — choose based on what you are testing

**Strategy A: Pure unit tests (pytest, no Streamlit runtime)**
Test calculation functions (`calcular_curva_aprendizado`, `dias_uteis_restantes`, `calcular_ciclo_desenvolvimento`,
`carregar_dados`) in isolation by importing them directly. No browser, no Streamlit session.
This is the primary strategy for this project: the monolith `dashboard.py` contains pure-Python
functions whose logic can be extracted and tested without touching the Streamlit rendering layer.

**Strategy B: AppTest integration tests (streamlit.testing.v1)**
Uses `streamlit.testing.v1.AppTest` — confirmed importable in the installed Streamlit 1.55.0:

```python
from streamlit.testing.v1 import AppTest
```

AppTest simulates a running Streamlit app without a browser. It is appropriate for testing widget
interaction, sidebar state, and that the app does not raise exceptions on load. It is NOT a visual
renderer — it cannot test chart content or HTML styling.

**When to use each:**

| Use Case | Strategy |
|----------|----------|
| Test burndown/burnup math | A — pure pytest |
| Test SLA business-days calculation | A — pure pytest |
| Test sigmoid learning curve | A — pure pytest |
| Test `carregar_dados()` CSV parsing | A — pure pytest with tmp_path fixture |
| Test `calcular_ciclo_desenvolvimento()` | A — pure pytest with temp CSV files |
| Verify app loads without exceptions | B — AppTest |
| Verify sidebar filters change state | B — AppTest |
| Verify tab navigation works | B — AppTest |

### AppTest API (verified against official docs)

```python
from streamlit.testing.v1 import AppTest

# Initialize — path is relative to where pytest is invoked
at = AppTest.from_file("app/dashboard/dashboard.py", default_timeout=10)

# Run the app (must call explicitly)
at.run()

# Assert no exceptions were raised
assert not at.exception

# Access widgets by index or key
at.sidebar.radio[0].set_value("☀️ Claro")
at.run()

# Access session state
at.session_state["my_key"] = "value"
at.run()

# Inject secrets (avoids committing credentials)
at.secrets["EMAIL"] = "test@example.com"
at.secrets["API_TOKEN"] = "fake-token"
```

### Critical path constraint

> "Imports and paths within a test script should be relative to the directory where pytest is called."

Run `pytest` from the project root (`G:/Meu Drive/Projetos/dashboard_fase_3`), not from within `app/`.
Use `AppTest.from_file("app/dashboard/dashboard.py")` — not a relative `../` path.

### AppTest limitation: top-level side effects

`dashboard.py` executes `carregar_dados()` and all chart logic at module top-level (not inside a
`main()` function). AppTest runs the full script, which means CSV files must exist or the app hits
`st.stop()`. Solution: use `monkeypatch` to patch `os.path.exists` and `pd.read_csv`, or provide
real minimal fixture CSV files in `tests/fixtures/`.

**Confidence:** HIGH — verified against official Streamlit docs + confirmed AppTest importable in project.

---

## Pandas Testing Patterns

### Core tool: `pandas.testing`

```python
import pandas as pd
import pandas.testing as tm

# Compare DataFrames — raises AssertionError with diff on mismatch
tm.assert_frame_equal(result, expected)

# Compare Series
tm.assert_series_equal(result, expected)

# Useful parameters
tm.assert_frame_equal(result, expected, check_dtype=False)   # ignore dtype differences
tm.assert_frame_equal(result, expected, check_exact=False, rtol=1e-5)  # float tolerance
```

### Fixture pattern for this project

```python
import pytest
import pandas as pd

@pytest.fixture
def df_subtarefas_minimal():
    """Minimal FASE_3.csv-shaped DataFrame for unit tests."""
    return pd.DataFrame({
        'Key': ['BF3E4-1', 'BF3E4-2'],
        'Data-Lake': ['BMC', 'BMC'],
        'Status': ['DONE', 'IN DEVELOPMENT'],
        'Titulo': ['task 1', 'task 2'],
        'Titulo Historia': ['[BMC-1] hist', '[BMC-1] hist'],
        'Deadline Historia': ['2026-06-01', '2026-06-01'],
        'Start Date': ['2026-01-15', '2026-01-20'],
        'Deadline': ['2026-03-01', '2026-03-01'],
        'Categoria': ['RN', 'Desenvolvimento/Outros'],
        'Tamanho': ['M', 'G'],
        'Epic Key': ['BF3E4-10', 'BF3E4-10'],
    })
```

### Testing functions with file I/O (`carregar_dados`, `calcular_ciclo_desenvolvimento`)

Use `tmp_path` (built-in pytest fixture) to avoid touching real CSV files:

```python
def test_carregar_dados_valid_csv(tmp_path):
    csv_file = tmp_path / "FASE_3.csv"
    csv_file.write_text("Key,Status\nBF3E4-1,DONE\n", encoding="utf-8-sig")

    # Import the function in isolation
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app/dashboard"))
    from dashboard import carregar_dados

    result = carregar_dados(str(csv_file))
    assert result is not None
    assert len(result) == 1
```

### Testing `calcular_ciclo_desenvolvimento` — glob dependency

The function uses `glob.glob()` to find CSV files. Patch it:

```python
from unittest.mock import patch

def test_calcular_ciclo_sem_arquivos(monkeypatch):
    monkeypatch.setattr("glob.glob", lambda *args, **kwargs: [])
    # Now the function returns (None, None) without hitting the filesystem
```

### Testing time-dependent functions (`dias_uteis_restantes`)

```python
from unittest.mock import patch
import pandas as pd

def test_dias_uteis_restantes_prazo_futuro(monkeypatch):
    frozen_today = pd.Timestamp("2026-03-25")
    monkeypatch.setattr("pandas.Timestamp.now", lambda: frozen_today)
    deadline = pd.Timestamp("2026-04-01")
    # 7 calendar days, 5 business days (Mon 30 Mar - Tue 1 Apr = 2 days, Mon-Fri)
```

### Testing the sigmoid (`calcular_curva_aprendizado`)

No external dependencies — pure numpy math. Test directly:

```python
def test_sigmoid_returns_monotonic_output():
    from app.dashboard.dashboard import calcular_curva_aprendizado
    datas, valores = calcular_curva_aprendizado(
        data_inicio=pd.Timestamp("2026-01-01"),
        data_fim=pd.Timestamp("2026-06-30"),
        total=100
    )
    assert len(datas) == len(valores)
    assert valores[0] < valores[-1]      # monotonically increasing
    assert valores[-1] == pytest.approx(100, rel=0.05)
```

**Confidence:** HIGH — verified against pandas.testing docs + confirmed `tm.assert_frame_equal` available.

---

## Deprecated API Fixes

All three deprecations confirmed as FutureWarning in pandas 2.1.4 (verified by running in project):

### Fix 1: `fillna(method='ffill')` → `.ffill()`

**Location:** `dashboard.py:48`

```python
# BEFORE (raises FutureWarning now, will raise in pandas 3.x)
valores_plan_interp = df_interpolado['valor'].fillna(method='ffill').fillna(0).tolist()

# AFTER — exact chain replacement
valores_plan_interp = df_interpolado['valor'].ffill().fillna(0).tolist()
```

The two-step chain is intentional: `.ffill()` fills forward from existing values, then `.fillna(0)`
fills any remaining NaN at the START of the series (where no previous value exists to propagate).

### Fix 2: `DataFrame.applymap()` → `DataFrame.map()`

**Location:** `dashboard.py:1214` — uses `df_render.style.applymap()`
Note: this is `Styler.applymap`, not `DataFrame.applymap`. Both are deprecated.

```python
# BEFORE (FutureWarning: Styler.applymap has been deprecated)
df_render.style.applymap(colorir_status, subset=['Status'])

# AFTER — exact replacement (same signature, same subset= parameter)
df_render.style.map(colorir_status, subset=['Status'])
```

For any `DataFrame.applymap()` occurrences (element-wise function over all cells):

```python
# BEFORE
df.applymap(some_func)

# AFTER
df.map(some_func)
```

### Deprecation timeline

| API | Deprecated | Warning in 2.1.4 | Removed in |
|-----|-----------|-------------------|-----------|
| `fillna(method='ffill')` | pandas 2.1.0 (Aug 2023) | FutureWarning | pandas 3.x |
| `DataFrame.applymap()` | pandas 2.1.0 (Aug 2023) | FutureWarning | pandas 3.x |
| `Styler.applymap()` | pandas 2.1.0 (Aug 2023) | FutureWarning | pandas 3.x |
| `GroupBy.fillna()` | pandas 2.2.0 (Jan 2024) | FutureWarning | pandas 3.x |

### No occurrences to fix in scripts

The extraction scripts (`script_atualizacao.py`, `extrair_historico.py`, `script_pendencias.py`)
use only `.fillna(value)` with a literal value — not the `method=` variant. No changes needed there.

**Confidence:** HIGH — ran both deprecated calls and their replacements in the actual project Python 3.12.5 / pandas 2.1.4 environment. All replacements confirmed working.

---

## @st.cache_data Best Practices

### When to use `@st.cache_data` vs `@st.cache_resource`

| Decorator | Use For | Returns | Example |
|-----------|---------|---------|---------|
| `@st.cache_data` | Data loading, transformations, CSV reads | **Copy** (safe for DataFrames) | `carregar_dados()`, `calcular_ciclo_desenvolvimento()` |
| `@st.cache_resource` | Shared connections, models, singletons | **Same object** (mutable) | DB connections, ML models |

For this project: use `@st.cache_data` on all data-loading and calculation functions.

### TTL guidance for this project

Data is refreshed by GitHub Actions 4 times per weekday. The CSV files on disk change; the
Streamlit session does not know about the file change unless the cache expires or is cleared.

```python
@st.cache_data(ttl=1800)  # 30 minutes — safe for 4x/day updates
def carregar_dados(arquivo):
    ...

@st.cache_data(ttl=1800)
def calcular_ciclo_desenvolvimento(data_lake_filtro='Todos'):
    ...
```

**TTL formats accepted (verified):**
- Integer seconds: `ttl=1800`
- Timedelta string: `ttl="30m"`, `ttl="1h"`, `ttl="1d"`
- `datetime.timedelta` object: `ttl=timedelta(minutes=30)`

**Do not use `persist="disk"`** — the CSV layer is already the persistence layer. Disk persistence
would create a stale second cache that ignores file changes.

### Cache invalidation

Manual clear (e.g., a "Refresh" button in the sidebar):

```python
if st.sidebar.button("Atualizar dados"):
    carregar_dados.clear()          # clear only this function's cache
    calcular_ciclo_desenvolvimento.clear()
    st.rerun()
```

Or clear all cached data:
```python
st.cache_data.clear()
```

### Important: function arguments become cache keys

`calcular_ciclo_desenvolvimento(data_lake_filtro)` takes an argument — this works correctly with
`@st.cache_data` because each unique argument value is cached separately:

```python
# These are THREE separate cache entries — correct behavior
calcular_ciclo_desenvolvimento('Todos')
calcular_ciclo_desenvolvimento('BMC')
calcular_ciclo_desenvolvimento('FINANCE')
```

### Scope parameter (Streamlit 1.55 feature)

```python
@st.cache_data(ttl=1800, scope="global")   # shared across all user sessions (default)
@st.cache_data(ttl=1800, scope="session")  # isolated per user session
```

For a single-user GitHub Codespaces deployment: `scope="global"` (default) is correct.

### Anti-pattern: don't cache functions with `st.*` calls inside

`carregar_dados()` and `calcular_ciclo_desenvolvimento()` contain no `st.*` calls — safe to cache.
If a function calls `st.warning()` or `st.write()` internally, caching it will suppress those
calls on cache hits. The functions in this codebase are clean on this point.

**Confidence:** HIGH — verified against official Streamlit docs for st.cache_data API and TTL formats.

---

## HTTP/API Mocking for Tests

### Available in project environment

| Library | Installed | Version | Role |
|---------|-----------|---------|------|
| `unittest.mock` | Yes (stdlib) | Python 3.12 | Patch any Python object |
| `responses` | Yes | 0.25.7 | Intercept `requests` HTTP calls at socket level |
| `pytest-mock` | **No** | — | Adds `mocker` fixture (thin pytest wrapper over unittest.mock) |
| `requests-mock` | No | — | Alternative to `responses` |

**Recommendation:** Use `responses` (already installed) + `unittest.mock` (stdlib). Do not require `pytest-mock` — it is a convenience wrapper and its absence is not a problem.

### Strategy 1: `responses` library — for testing script functions that call `requests.get`

`responses` intercepts at the socket level — no actual HTTP ever leaves the machine:

```python
import responses
import requests

@responses.activate
def test_buscar_com_paginacao_single_page():
    responses.add(
        responses.GET,
        "https://fcagil.atlassian.net/rest/api/3/search/jql",
        json={
            "issues": [{"key": "BF3E4-1", "fields": {"summary": "test"}}],
            "isLast": True
        },
        status=200
    )
    from requests.auth import HTTPBasicAuth
    auth = HTTPBasicAuth("user@test.com", "fake-token")
    # Import the function under test
    from app.scripts.script_atualizacao import buscar_com_paginacao

    result = buscar_com_paginacao(
        jql='project="BF3E4"',
        fields="key,summary",
        auth=auth
    )
    assert len(result) == 1
    assert result[0]["key"] == "BF3E4-1"
```

### Strategy 2: `unittest.mock.patch` — for patching `requests.get` inline

Use when you need fine-grained control over return values or side effects:

```python
from unittest.mock import patch, MagicMock

def test_request_returns_error_status():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("requests.get", return_value=mock_response):
        # Test that the script handles auth failures gracefully
        ...
```

### Critical rule: patch at the point of use

The scripts import `requests` at module level. Patch `requests.get` in the module where it is called:

```python
# script_atualizacao.py uses requests.get directly — patch it there:
with patch("app.scripts.script_atualizacao.requests.get", return_value=mock_response):
    ...

# Or patch the global requests.get (also works since the module uses requests.get, not a local alias):
with patch("requests.get", return_value=mock_response):
    ...
```

### Strategy 3: environment variable isolation

The scripts read `EMAIL` and `API_TOKEN` from `os.getenv()`. In tests:

```python
import os
from unittest.mock import patch

def test_script_with_fake_credentials(monkeypatch):
    monkeypatch.setenv("EMAIL", "test@example.com")
    monkeypatch.setenv("API_TOKEN", "fake-token-for-testing")
    # Now os.getenv() returns test values for this test only
```

### Testing `extrair_data_lake` and `classificar_subtarefa` — no mocking needed

These are pure string functions with no I/O. Test directly:

```python
from app.scripts.script_atualizacao import extrair_data_lake, classificar_subtarefa

def test_extrair_data_lake_with_hyphen():
    assert extrair_data_lake("[BMC-1] Some story") == "BMC"

def test_classificar_subtarefa_rn_fmk():
    assert classificar_subtarefa("Validar RN-FMK regra especial") == "RN-FMK"

def test_classificar_subtarefa_story_bug_priority():
    assert classificar_subtarefa("STORY BUG - RN-FMK overlap") == "Story Bug"
```

**Confidence:** HIGH — `responses` 0.25.7 verified installed; `unittest.mock` is Python stdlib. Patterns verified against official Python docs and responses library docs.

---

## Recommended Test Setup

### Directory structure

```
dashboard_fase_3/
├── app/
│   ├── dashboard/dashboard.py
│   ├── scripts/
│   └── dados/
├── tests/
│   ├── __init__.py               (empty — marks tests/ as a package)
│   ├── conftest.py               (shared fixtures)
│   ├── fixtures/
│   │   ├── FASE_3_minimal.csv    (10-row CSV for fast tests)
│   │   └── historico_minimal.csv
│   ├── test_dashboard_calculations.py
│   ├── test_carregar_dados.py
│   ├── test_scripts_extraction.py
│   └── test_app_smoke.py         (AppTest: verifies app loads without crash)
├── pytest.ini
└── requirements.txt
```

### `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    error::FutureWarning
    ignore::urllib3.exceptions.InsecureRequestWarning
```

`filterwarnings = error::FutureWarning` turns any remaining pandas deprecation warnings into
test failures — this is the automated gate that prevents deprecated API re-introduction.

### `tests/conftest.py`

```python
import pytest
import pandas as pd
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def df_subtarefas():
    """Minimal 11-column DataFrame matching FASE_3.csv schema."""
    return pd.DataFrame({
        'Key':              ['BF3E4-1', 'BF3E4-2', 'BF3E4-3'],
        'Data-Lake':        ['BMC', 'BMC', 'FINANCE'],
        'Status':           ['DONE', 'IN DEVELOPMENT', 'DONE'],
        'Titulo':           ['task 1', 'task 2', 'task 3'],
        'Titulo Historia':  ['[BMC-1] hist A', '[BMC-1] hist A', '[FINANCE-2] hist B'],
        'Deadline Historia':['2026-06-01', '2026-06-01', '2026-05-01'],
        'Start Date':       ['2026-01-15', '2026-01-20', '2026-02-01'],
        'Deadline':         ['2026-03-01', '2026-03-01', '2026-04-01'],
        'Categoria':        ['RN', 'Desenvolvimento/Outros', 'RN-FMK'],
        'Tamanho':          ['M', 'G', 'P'],
        'Epic Key':         ['BF3E4-10', 'BF3E4-10', 'BF3E4-11'],
    })


@pytest.fixture
def csv_fase3(tmp_path, df_subtarefas):
    """Write df_subtarefas to a temp CSV file, return its path."""
    p = tmp_path / "FASE_3.csv"
    df_subtarefas.to_csv(p, index=False, encoding="utf-8-sig")
    return str(p)
```

### Running tests

```bash
# From project root — always
pytest

# Single file
pytest tests/test_dashboard_calculations.py -v

# Single test
pytest tests/test_dashboard_calculations.py::test_sigmoid_monotonic -v

# Run and show all warnings (useful during debugging)
pytest -W default
```

### Packages to add to `requirements.txt` (or a new `requirements-test.txt`)

```
pytest==8.4.1        # already installed
responses==0.25.7    # already installed
# No additional packages required for the test strategy above
```

`pytest-mock` is NOT required — `unittest.mock` with `monkeypatch` covers all needs.

---

## Environment Availability

| Tool | Available | Version | Notes |
|------|-----------|---------|-------|
| Python | Yes | 3.12.5 | Installed |
| pytest | Yes | 8.4.1 | Installed |
| streamlit | Yes | 1.55.0 | `streamlit.testing.v1.AppTest` confirmed importable |
| pandas | Yes | 2.1.4 | Deprecated APIs confirmed as FutureWarning (not yet Error) |
| numpy | Yes | 1.26.4 | Available |
| responses | Yes | 0.25.7 | Available for HTTP mocking |
| pytest-mock | No | — | Not needed — `unittest.mock` + `monkeypatch` sufficient |
| requests-mock | No | — | Not needed — `responses` covers use cases |

**Note:** `requirements.txt` pins `pandas==2.2.3` and `numpy==2.2.1`, but the installed versions
are `pandas==2.1.4` and `numpy==1.26.4`. The deprecated APIs (`fillna(method=)`, `applymap`)
are FutureWarning in both 2.1.x and 2.2.x — the fix is valid for both.

---

## Sources

### Primary (HIGH confidence — official docs + verified in project environment)
- [Streamlit AppTest API](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) — AppTest initialization, run(), widget access
- [Streamlit App Testing: Get Started](https://docs.streamlit.io/develop/concepts/app-testing/get-started) — path resolution, test organization
- [Streamlit App Testing: Beyond Basics](https://docs.streamlit.io/develop/concepts/app-testing/beyond-the-basics) — session state, secrets injection
- [st.cache_data API](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data) — TTL formats, manual clear, scope parameter
- [pandas 2.1.0 What's New](https://pandas.pydata.org/docs/whatsnew/v2.1.0.html) — fillna method= deprecation, applymap→map, Styler.applymap→map
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html) — MagicMock, patch
- In-project verification: ran deprecated calls and replacements under Python 3.12.5 / pandas 2.1.4

### Secondary (MEDIUM confidence — official docs verified)
- [pandas DataFrame.fillna](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.fillna.html)
- [pandas DataFrame.applymap](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.applymap.html)
- [responses library (PyPI)](https://pypi.org/project/responses/) — version 0.25.7 confirmed installed
