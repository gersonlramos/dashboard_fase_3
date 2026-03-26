"""
Phase 1 correctness fixes — unit tests.
CONSTRAINT: dashboard.py is NOT imported here.
It calls st.set_page_config() at module scope which crashes outside Streamlit.
Each test reproduces the logic pattern inline.
"""
import pandas as pd
import numpy as np
import pytest
import configparser
import os


# ---------------------------------------------------------------------------
# FIX-01: fillna(method='ffill') -> .ffill()
# ---------------------------------------------------------------------------

def test_fix01_ffill_basic():
    """ffill() fills NaN from the preceding non-NaN value, same as fillna(method='ffill')."""
    s = pd.Series([1.0, float('nan'), float('nan'), 4.0])
    result = s.ffill().fillna(0).tolist()
    assert result == [1.0, 1.0, 1.0, 4.0], f"Expected [1.0, 1.0, 1.0, 4.0], got {result}"


def test_fix01_ffill_leading_nan_filled_by_fillna_zero():
    """Leading NaN (no prior value to forward-fill) must be filled by the trailing .fillna(0)."""
    s = pd.Series([float('nan'), float('nan'), 3.0])
    result = s.ffill().fillna(0).tolist()
    assert result == [0.0, 0.0, 3.0], f"Expected [0.0, 0.0, 3.0], got {result}"


def test_fix01_no_future_warning():
    """Calling .ffill() must not emit FutureWarning."""
    s = pd.Series([1.0, float('nan'), 3.0])
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        result = s.ffill().fillna(0).tolist()  # must not raise
    assert result == [1.0, 1.0, 3.0]


# ---------------------------------------------------------------------------
# FIX-02: style.applymap() -> style.map()
# ---------------------------------------------------------------------------

def _colorir_status_inline(val):
    """Inline copy of colorir_status from dashboard.py:1169-1183.
    Cannot import from dashboard.py (Streamlit module-scope crash).
    """
    cores = {
        'Done': 'color: #1a7a1a; font-weight: bold',
        'In Progress': 'color: #0055a5; font-weight: bold',
        'In Test': 'color: #0055a5; font-weight: bold',
        'Waiting Test': 'color: #6b3fa0; font-weight: bold',
        'Canceled': 'color: #888888',
        'Open': 'color: #b34a00',
        'To Do': 'color: #b34a00',
    }
    return cores.get(val, '')


def test_fix02_style_map_returns_css():
    """style.map() calls func with one scalar per cell and returns a Styler."""
    df = pd.DataFrame({'Status': ['Done', 'In Progress', 'Open', 'Unknown']})
    result = df.style.map(_colorir_status_inline, subset=['Status'])
    import pandas.io.formats.style as pd_style
    assert isinstance(result, pd_style.Styler)


def test_fix02_style_map_no_future_warning():
    """style.map() must not emit FutureWarning (as applymap did in pandas 2.x)."""
    df = pd.DataFrame({'Status': ['Done', 'Canceled']})
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        _ = df.style.map(_colorir_status_inline, subset=['Status'])  # must not raise


def test_fix02_applymap_absent():
    """Confirm that no 'applymap' string exists anywhere in dashboard.py."""
    dashboard_path = os.path.join(
        os.path.dirname(__file__), '..', 'app', 'dashboard', 'dashboard.py'
    )
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'applymap' not in content, "applymap still present in dashboard.py"


# ---------------------------------------------------------------------------
# FIX-03a: dias_uteis_restantes while-loop -> np.busday_count
# ---------------------------------------------------------------------------

def _dias_uteis_busday(deadline, hoje_d=None):
    """Inline implementation of the FIXED dias_uteis_restantes using np.busday_count.
    Shift both bounds by +1 day so busday_count covers (hoje_d, deadline]
    which matches the while-loop's exclusive-start semantics exactly.
    """
    if pd.isna(deadline):
        return None
    if hoje_d is None:
        hoje_d = pd.Timestamp.now().normalize()
    if deadline < hoje_d:
        return -int((hoje_d - deadline).days)
    d1 = (hoje_d + pd.Timedelta(days=1)).date()
    d2 = (pd.Timestamp(deadline) + pd.Timedelta(days=1)).date()
    return int(np.busday_count(d1, d2))


def _dias_uteis_while(deadline, hoje_d=None):
    """Inline copy of the ORIGINAL while-loop for semantic comparison."""
    if pd.isna(deadline):
        return None
    if hoje_d is None:
        hoje_d = pd.Timestamp.now().normalize()
    if deadline < hoje_d:
        return -int((hoje_d - deadline).days)
    count = 0
    cur = hoje_d
    while cur < deadline:
        cur += pd.Timedelta(days=1)
        if cur.weekday() < 5:
            count += 1
    return count


def test_fix03_busday_matches_while_loop():
    """np.busday_count replacement returns same count as while-loop for sample inputs."""
    base = pd.Timestamp('2026-03-23')  # Monday — fixed reference date
    test_deadlines = [
        base + pd.Timedelta(days=1),   # Tuesday -> 1
        base + pd.Timedelta(days=5),   # Saturday -> 4 (Mon-Fri only)
        base + pd.Timedelta(days=7),   # next Monday -> 5
        base + pd.Timedelta(days=14),  # two weeks out -> 10
        base,                          # same day -> 0
    ]
    for dl in test_deadlines:
        expected = _dias_uteis_while(dl, hoje_d=base)
        actual = _dias_uteis_busday(dl, hoje_d=base)
        assert actual == expected, (
            f"Mismatch for deadline={dl.date()}: while={expected}, busday={actual}"
        )


def test_fix03_busday_past_deadline_returns_negative():
    """Past deadline returns negative calendar days (unchanged behavior)."""
    base = pd.Timestamp('2026-03-23')
    past = base - pd.Timedelta(days=3)
    result = _dias_uteis_busday(past, hoje_d=base)
    assert result == -3


def test_fix03_busday_na_returns_none():
    """pd.NaT / None input returns None."""
    assert _dias_uteis_busday(pd.NaT) is None


# ---------------------------------------------------------------------------
# FIX-03b: bare except -> except (ValueError, TypeError)
# ---------------------------------------------------------------------------

def test_fix03b_tightened_except_in_dashboard():
    """Confirm 'except:' no longer exists in dashboard.py (bare except is gone)."""
    dashboard_path = os.path.join(
        os.path.dirname(__file__), '..', 'app', 'dashboard', 'dashboard.py'
    )
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    bare_except_lines = [
        (i + 1, line.strip()) for i, line in enumerate(lines)
        if line.strip() == 'except:'
    ]
    assert bare_except_lines == [], (
        f"Bare 'except:' still present at lines: {bare_except_lines}"
    )


# ---------------------------------------------------------------------------
# FIX-03c: Historia column guard
# ---------------------------------------------------------------------------

def test_fix03c_historia_guard_missing_column():
    """Column list builder skips 'Historia' when it is absent from df."""
    df = pd.DataFrame({
        'Data-Lake': ['COMPRAS'],
        'Titulo Historia': ['Some title'],
        'Chave': ['BF3E4-1'],
        'Titulo': ['Task'],
        'Status': ['Done'],
        'Categoria_Analise': ['Cat A'],
    })
    colunas_resumo_base = ['Data-Lake', 'Historia', 'Titulo Historia', 'Chave', 'Titulo', 'Status', 'Categoria_Analise']
    colunas_resumo = [c for c in colunas_resumo_base if c in df.columns]
    result = df[colunas_resumo]
    assert 'Historia' not in result.columns
    assert 'Data-Lake' in result.columns
    assert len(result) == 1


def test_fix03c_historia_guard_present_column():
    """When Historia IS present, it is included normally."""
    df = pd.DataFrame({
        'Data-Lake': ['COMPRAS'],
        'Historia': ['H-001'],
        'Titulo Historia': ['Some title'],
        'Chave': ['BF3E4-1'],
        'Titulo': ['Task'],
        'Status': ['Done'],
        'Categoria_Analise': ['Cat A'],
    })
    colunas_resumo_base = ['Data-Lake', 'Historia', 'Titulo Historia', 'Chave', 'Titulo', 'Status', 'Categoria_Analise']
    colunas_resumo = [c for c in colunas_resumo_base if c in df.columns]
    result = df[colunas_resumo]
    assert 'Historia' in result.columns


# ---------------------------------------------------------------------------
# FIX-04: pytest.ini with filterwarnings = error::FutureWarning
# ---------------------------------------------------------------------------

def test_fix04_pytest_ini_exists():
    """pytest.ini exists at the project root with required filterwarnings entries."""
    root = os.path.join(os.path.dirname(__file__), '..')
    ini_path = os.path.join(root, 'pytest.ini')
    assert os.path.isfile(ini_path), f"pytest.ini not found at {os.path.abspath(ini_path)}"

    config = configparser.ConfigParser()
    config.read(ini_path, encoding='utf-8')

    assert config.has_section('pytest'), "pytest.ini must have [pytest] section"
    assert config.has_option('pytest', 'filterwarnings'), \
        "pytest.ini [pytest] section must have filterwarnings key"

    fw_value = config.get('pytest', 'filterwarnings')
    assert 'error::FutureWarning' in fw_value, \
        f"filterwarnings must include 'error::FutureWarning'; got: {fw_value!r}"
    assert 'ignore::urllib3.exceptions.InsecureRequestWarning' in fw_value, \
        f"filterwarnings must include 'ignore::urllib3...' suppressor; got: {fw_value!r}"


def test_fix04_futurewarning_gate_is_active():
    """Verify FutureWarning is elevated to error in the pytest session (from pytest.ini)."""
    import warnings
    filters = warnings.filters
    future_warning_elevated = any(
        action == 'error' and (issubclass(FutureWarning, category) or category is FutureWarning)
        for action, message, category, module, lineno in filters
    )
    assert future_warning_elevated, (
        "FutureWarning is not elevated to error in the current pytest session. "
        "Check that pytest.ini has filterwarnings = error::FutureWarning and "
        "that pytest was invoked from the project root."
    )
