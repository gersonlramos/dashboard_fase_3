# Phase 1: Correctness Fixes - Research

**Researched:** 2026-03-25
**Domain:** pandas deprecated APIs, numpy busday, pytest configuration
**Confidence:** HIGH

---

## Summary

Phase 1 makes four surgical edits to `app/dashboard/dashboard.py` and creates one new file (`pytest.ini`). All four deprecated patterns have been confirmed in the live file by direct inspection. The replacements are one-to-one API swaps — there are no signature changes that would alter runtime behavior. The most structurally significant change is replacing the `while`-loop in `dias_uteis_restantes()` with `np.busday_count()`, which already exists and is used in `calcular_dias_uteis()` at line 607 of the same file. No new dependencies are required.

The `Historia` column reference at line 1912 is a straightforward `KeyError` risk: the column is directly subscripted as `df_filtrado['Historia']`, but the CSV produced by `script_atualizacao.py` does not include a `Historia` column. The fix is a conditional column-list construction that checks membership before inclusion.

`pytest.ini` does not exist in the project. The project root (`g:/Meu Drive/Projetos/dashboard_fase_3/`) currently contains only `requirements.txt` and the `app/` directory. `pytest.ini` must be created there.

**Primary recommendation:** Apply each fix as an isolated, self-contained edit with a matching test assertion in `tests/test_phase1.py`. The pytest `filterwarnings = error::FutureWarning` gate in `pytest.ini` will enforce correctness automatically going forward.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIX-01 | `fillna(method='ffill')` at line 48 replaced with `.ffill()` — no FutureWarning on pandas 3.x | Direct file inspection confirms single occurrence; replacement is a chained method call |
| FIX-02 | `style.applymap()` at line 1214 replaced with `style.map()` — no FutureWarning or AttributeError on pandas 3.x | Direct file inspection confirms single occurrence; signatures are identical |
| FIX-03 | `dias_uteis_restantes()` while-loop at lines 2158–2171 replaced with `np.busday_count()` | `calcular_dias_uteis()` at line 591 is the proven template; also covers bare `except:` at line 536 and `Historia` guard at line 1912 |
| FIX-04 | `pytest.ini` created with `filterwarnings = error::FutureWarning` | No pytest.ini exists; project root confirmed; format documented below |
</phase_requirements>

---

## Exact Code at Each Affected Location

### FIX-01 — line 48: `fillna(method='ffill')`

**Current code (line 48):**
```python
valores_plan_interp = df_interpolado['valor'].fillna(method='ffill').fillna(0).tolist()
```

**Context:** Inside `calcular_curva_aprendizado()` (function starts at line 14). The Series `df_interpolado['valor']` may have NaN gaps from `pd.merge_asof(..., direction='forward')` when no matching forward-date exists. The intent is to forward-fill those NaN values, then fill any remaining NaN with 0.

**After fix:**
```python
valores_plan_interp = df_interpolado['valor'].ffill().fillna(0).tolist()
```

**Chaining note:** `.ffill()` returns the same Series type as `fillna(method='ffill')` did; `.fillna(0)` in the second position is unaffected by this change. No edge-case regression risk. Confidence: HIGH (verified against pandas 2.2 changelog and pandas 1.5 deprecation notice).

**Scope check:** Grep confirms this is the only `fillna(method=` occurrence in the entire file.

---

### FIX-02 — line 1214: `style.applymap()`

**Current code (lines 1212–1217):**
```python
    else:
        st.dataframe(
            df_render.style.applymap(colorir_status, subset=['Status']),
            use_container_width=True,
            height=300
        )
```

**Context:** `renderizar_tabela()` function (starts line 1185). `colorir_status` (lines 1169–1183) takes a scalar value and returns a CSS string or `''`. The `subset=['Status']` argument restricts styling to the Status column only.

**After fix:**
```python
    else:
        st.dataframe(
            df_render.style.map(colorir_status, subset=['Status']),
            use_container_width=True,
            height=300
        )
```

**Signature compatibility:** `Styler.map()` (introduced pandas 2.1.0 as the replacement for `applymap`) accepts exactly the same arguments: `func`, `subset`, `**kwargs`. The function signature of `colorir_status(val)` is unchanged — it still receives one scalar per cell. No behavior change. Confidence: HIGH.

**Scope check:** Grep confirms this is the only `applymap` occurrence in the file.

---

### FIX-03a — lines 2158–2171: `dias_uteis_restantes()` while-loop

**Current code:**
```python
def dias_uteis_restantes(deadline):
    """Conta dias úteis entre hoje e o deadline."""
    if pd.isna(deadline):
        return None
    hoje_d = pd.Timestamp.now().normalize()
    if deadline < hoje_d:
        return -int((hoje_d - deadline).days)  # negativo = já passou
    count = 0
    cur = hoje_d
    while cur < deadline:
        cur += pd.Timedelta(days=1)
        if cur.weekday() < 5:
            count += 1
    return count
```

**Problem:** The while-loop iterates day-by-day, which is O(n_days). Called via `.apply()` on every row of `df_sla` on every Streamlit render. Also classified as a performance concern in CONCERNS.md.

**Template already in codebase** — `calcular_dias_uteis()` at lines 591–607:
```python
def calcular_dias_uteis(data_inicio, data_fim):
    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0
    d1 = pd.Timestamp(data_inicio).date()
    d2 = pd.Timestamp(data_fim).date()
    if d2 < d1:
        return 0
    return np.busday_count(d1, d2)
```

**After fix:**
```python
def dias_uteis_restantes(deadline):
    """Conta dias úteis entre hoje e o deadline."""
    if pd.isna(deadline):
        return None
    hoje_d = pd.Timestamp.now().normalize()
    if deadline < hoje_d:
        return -int((hoje_d - deadline).days)  # negativo = já passou
    d1 = hoje_d.date()
    d2 = pd.Timestamp(deadline).date()
    return int(np.busday_count(d1, d2))
```

**Behavior notes:**
- `np.busday_count(d1, d2)` counts Mon–Fri business days from `d1` (inclusive) to `d2` (exclusive). The old while-loop also excluded weekends with `cur.weekday() < 5`. The off-by-one behavior: `busday_count` does NOT count `d1` itself (exclusive start) and does NOT count `d2` (exclusive end). The while-loop increments `cur` before testing, so it also excludes `hoje_d` and excludes `deadline` day. The behaviors are consistent.
- The negative-days branch (past deadline) is preserved unchanged — it remains a calendar-day count because the original code used `.days` there too.
- `int()` cast is needed because `np.busday_count` returns `numpy.intp`.

---

### FIX-03b — line 536: bare `except:`

**Current code (lines 527–537):**
```python
        for fmt in formatos:
            try:
                # Remove o timezone manualmente se existir (substitui por Z para UTC)
                if '+' in data_str or data_str.count('-') > 2:
                    # Remove timezone (tudo após o último ':' seguido de dígitos)
                    if 'T' in data_str:
                        data_str_sem_tz = data_str[:data_str.rfind('+' if '+' in data_str else '-')] if ('+' in data_str or data_str.rfind('-') > 10) else data_str
                        return pd.to_datetime(data_str_sem_tz)
                return pd.to_datetime(data_str, format=fmt)
            except:
                continue
```

**Problem:** Bare `except:` catches `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and all other base exceptions. Any signal or Streamlit shutdown event inside this loop would be silently swallowed.

**What exceptions actually occur here:** `pd.to_datetime()` raises `ValueError` when the string does not match the format, and `TypeError` when the input is not a string-like type. Those are the only two exceptions that should be caught.

**After fix:**
```python
            except (ValueError, TypeError):
                continue
```

**Confidence:** HIGH — `pd.to_datetime()` documentation confirms `ValueError` for parse failures and `TypeError` for wrong input types.

---

### FIX-03c — line 1912: `Historia` column KeyError

**Current code (lines 1911–1916):**
```python
    if exibir_todas:
        colunas_todas = ['Data-Lake', 'Historia'] + [c for c in df_filtrado.columns if c not in ['Data-Lake', 'Historia']]
        renderizar_tabela(df_filtrado[colunas_todas].sort_index(ascending=False), tema_selecionado)
    else:
        colunas_resumo = ['Data-Lake', 'Historia', 'Titulo Historia', 'Chave', 'Titulo', 'Status', 'Categoria_Analise']
        renderizar_tabela(df_filtrado[colunas_resumo].sort_index(ascending=False), tema_selecionado)
```

**Problem:** Both branches directly subscript `df_filtrado` with `'Historia'`. CONCERNS.md confirms the CSV schema from `script_atualizacao.py` does not include a `Historia` column (the column is named `Titulo Historia`). If `Historia` is absent, `df_filtrado[colunas_todas]` raises `KeyError` when "Exibir todas as colunas" is checked, and `df_filtrado[colunas_resumo]` similarly fails in the `else` branch.

**Fix approach — guard before building the column list:**
```python
    if exibir_todas:
        colunas_todas = [c for c in ['Data-Lake', 'Historia'] if c in df_filtrado.columns] + \
                        [c for c in df_filtrado.columns if c not in ['Data-Lake', 'Historia']]
        renderizar_tabela(df_filtrado[colunas_todas].sort_index(ascending=False), tema_selecionado)
    else:
        colunas_resumo_base = ['Data-Lake', 'Historia', 'Titulo Historia', 'Chave', 'Titulo', 'Status', 'Categoria_Analise']
        colunas_resumo = [c for c in colunas_resumo_base if c in df_filtrado.columns]
        renderizar_tabela(df_filtrado[colunas_resumo].sort_index(ascending=False), tema_selecionado)
```

**Why not `.get()`:** `df.get()` is a method on Series, not on column selection. The correct pattern for guarding column lists before subscript is `if c in df.columns`. Confidence: HIGH.

---

### FIX-04 — pytest.ini (new file)

**Current state:** No `pytest.ini`, `setup.cfg`, or `pyproject.toml` exists in the project root. Grep of the root confirms only `requirements.txt` and `app/`.

**Required content:**
```ini
[pytest]
filterwarnings =
    error::FutureWarning
    ignore::urllib3.exceptions.InsecureRequestWarning
```

**Why `ignore::urllib3`:** All three data-extraction scripts suppress `InsecureRequestWarning` at the module level via `urllib3.disable_warnings()`. If tests import those scripts or trigger HTTP calls, the warning would surface in pytest and get escalated to an error by the `error::FutureWarning` gate — except `FutureWarning` and `InsecureRequestWarning` are different classes. However, future test phases will exercise the scripts directly (TEST-08, TEST-09), and the SSL suppression is already documented as a known issue (CONCERNS.md). Adding the `ignore` filter now prevents confusion in later phases.

**Placement:** Project root — `g:/Meu Drive/Projetos/dashboard_fase_3/pytest.ini`.

**pytest.ini format rules (confirmed):**
- Must have `[pytest]` section header (not `[tool:pytest]` — that is for `setup.cfg`)
- `filterwarnings` is a multi-value key; one filter per indented line
- Filter syntax: `action::warning_class` (module/message patterns optional)

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 (pinned) | DataFrame operations | Already installed; fixes target its deprecated API |
| numpy | 2.2.1 (pinned) | `np.busday_count` | Already installed; used in `calcular_dias_uteis()` at line 607 |
| pytest | not pinned | Test runner + `filterwarnings` gate | Standard Python test runner |

**Note on pytest version:** `pytest` is not in `requirements.txt`. It must be available in the development/CI environment. The `filterwarnings` directive in `pytest.ini` has been supported since pytest 3.1 (2017); any modern version is sufficient.

**Installation (if pytest not present):**
```bash
pip install pytest
```

No additional packages needed for this phase.

---

## Architecture Patterns

### Pattern: Chained Series methods (pandas)

The general pandas migration pattern for deprecated `fillna(method=)` calls:

```python
# Before (deprecated since pandas 2.1, removed in pandas 3.0)
series.fillna(method='ffill')
series.fillna(method='bfill')

# After
series.ffill()
series.bfill()
```

The `.ffill()` / `.bfill()` methods exist on both `Series` and `DataFrame`. They accept `limit=` as a parameter if needed. Source: pandas 2.1 changelog and pandas 3.0 migration guide.

### Pattern: Styler element-wise functions (pandas)

```python
# Before (deprecated since pandas 1.4, removed in pandas 2.1+)
df.style.applymap(func, subset=['col'])

# After (pandas 2.1+ name)
df.style.map(func, subset=['col'])
```

`Styler.map()` is the direct rename of `Styler.applymap()`. Signature is identical. The function `func` still receives one scalar per element and returns a CSS string or `''`. Source: pandas 2.1 release notes.

### Pattern: Business-day counting with numpy

```python
import numpy as np

# np.busday_count(begindates, enddates)
# - begindates: inclusive start
# - enddates: exclusive end
# - Counts Mon–Fri by default (weekmask='1111100')
# Both arguments must be date-like (datetime.date or numpy.datetime64)

d1 = pd.Timestamp(start).date()   # convert to datetime.date
d2 = pd.Timestamp(end).date()
result = int(np.busday_count(d1, d2))
```

The `calcular_dias_uteis()` function at lines 591–607 already demonstrates this exact pattern and handles the `pd.isna` guard and `d2 < d1` edge case.

### Pattern: pytest filterwarnings gate

```ini
[pytest]
filterwarnings =
    error::FutureWarning
    ignore::urllib3.exceptions.InsecureRequestWarning
```

This turns any `FutureWarning` emitted during a test run into a test failure. The `ignore` line must come after `error` lines (or have a more specific match) — pytest processes filters in order and the first match wins.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Business-day counting | Custom while-loop (current code) | `np.busday_count()` | Already in codebase at line 607; handles leap years, edge cases correctly |
| Forward-fill NaN | `fillna(method='ffill')` | `.ffill()` | Direct pandas API; no logic to write |
| Cell-level styling | Custom HTML table | `Styler.map()` | pandas handles CSS correctly per cell |

---

## Common Pitfalls

### Pitfall 1: `np.busday_count` type requirements
**What goes wrong:** Passing a `pd.Timestamp` directly to `np.busday_count` raises `TypeError: Could not convert object to NumPy datetime`.
**Why it happens:** `np.busday_count` requires `datetime.date` or `numpy.datetime64`, not `pd.Timestamp`.
**How to avoid:** Always call `.date()` on Timestamps before passing: `pd.Timestamp(x).date()`.
**Warning signs:** `TypeError` in the apply step on `df_sla["Deadline"]`.

### Pitfall 2: `busday_count` off-by-one vs. the while-loop
**What goes wrong:** `np.busday_count(d1, d2)` is exclusive on both ends (`d1` is day 0, `d2` is not counted). The while-loop also starts at `hoje_d` and counts days `> hoje_d` and `<= deadline - 1`. Semantics match.
**Why it matters:** Confirm: if `deadline` is tomorrow (a weekday), the while-loop returns 1 and `np.busday_count(today, tomorrow)` also returns 1. They agree.
**How to avoid:** The existing `calcular_dias_uteis` function demonstrates correct usage — follow it exactly.

### Pitfall 3: `Styler.map` vs `Styler.applymap` pandas version boundary
**What goes wrong:** `Styler.map()` was introduced in pandas 1.4 as an alias, then `applymap` was deprecated in 2.1 and removed in 2.1+ (exact removal depends on version). On pandas 2.2.3 both names work, but `applymap` emits `FutureWarning`.
**How to avoid:** Use `style.map()` unconditionally — it works on 2.x and 3.x.

### Pitfall 4: pytest.ini `[pytest]` vs `[tool:pytest]`
**What goes wrong:** Using `[tool:pytest]` in `pytest.ini` — this section header is only valid in `setup.cfg`, not `pytest.ini`.
**How to avoid:** In `pytest.ini`, the header is always `[pytest]`.

### Pitfall 5: `Historia` column guard — both branches
**What goes wrong:** Fixing only the `if exibir_todas` branch. The `else` branch (line 1915) also hardcodes `'Historia'` in `colunas_resumo`. If only one branch is patched, the bug survives.
**How to avoid:** Apply the `if c in df_filtrado.columns` guard to both branches.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version not pinned; any ≥ 3.1 sufficient) |
| Config file | `pytest.ini` — does not exist yet; Wave 0 must create it |
| Quick run command | `pytest tests/test_phase1.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIX-01 | `.ffill()` produces same output as old `fillna(method='ffill')` on sample data | unit | `pytest tests/test_phase1.py::test_fix01_ffill -x` | No — Wave 0 |
| FIX-02 | `colorir_status` applied via `style.map()` returns same CSS strings as `style.applymap()` | unit | `pytest tests/test_phase1.py::test_fix02_style_map -x` | No — Wave 0 |
| FIX-03 | `np.busday_count` replacement returns same count as old while-loop for same inputs | unit | `pytest tests/test_phase1.py::test_fix03_busday -x` | No — Wave 0 |
| FIX-03b | `except (ValueError, TypeError)` does not catch `KeyboardInterrupt` | unit | `pytest tests/test_phase1.py::test_fix03b_exception_scope -x` | No — Wave 0 |
| FIX-03c | Column guard skips missing `Historia` without raising `KeyError` | unit | `pytest tests/test_phase1.py::test_fix03c_historia_guard -x` | No — Wave 0 |
| FIX-04 | `pytest.ini` exists with `filterwarnings = error::FutureWarning` | smoke | `pytest tests/test_phase1.py::test_fix04_pytest_ini -x` | No — Wave 0 |

**Important constraint from STATE.md:** Do NOT import `dashboard.py` directly in tests — it calls `st.set_page_config()` and other Streamlit calls at module scope, which crashes outside a Streamlit server context. Tests for the fixed functions must either:
- Copy the minimal function under test into `tests/test_phase1.py` as a fixture, or
- Import only if `streamlit` import side-effects are mocked.

For Phase 1, the simplest approach is to test the logic patterns directly without importing the monolith (the function extraction to `calculations.py` is Phase 3 work).

### Sampling Rate
- **Per task commit:** `pytest tests/test_phase1.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase1.py` — covers FIX-01 through FIX-04
- [ ] `tests/__init__.py` — package marker (if tests/ dir does not exist)
- [ ] `pytest.ini` — created as part of FIX-04 itself (dual purpose: gate + test file)

---

## Other FutureWarnings Scan

Grep was run for all deprecated patterns across the file. Results:

| Pattern | Occurrences | Lines | Risk |
|---------|-------------|-------|------|
| `fillna(method=` | 1 | 48 | Fixed by FIX-01 |
| `applymap` | 1 | 1214 | Fixed by FIX-02 |
| `DataFrame.append()` | 0 | — | Not present (removed in pandas 2.0; would have crashed already) |
| `inplace=True` on `sort_values`/`rename` | 2 | 801, 2108 | `inplace=True` is NOT deprecated in pandas 2.x; no FutureWarning |
| `interpolate(method=)` | 0 | — | Not present |
| `.map()` on Series (not Styler) | 2 | 941, 957 | Series.map() is not deprecated; different from Styler.map() |

**Conclusion:** Only the two deprecated calls enumerated in FIX-01 and FIX-02 are present. No additional FutureWarnings will be triggered by the installed pandas 2.2.3 beyond these two.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All fixes | Assumed present (project runs) | — | — |
| pandas | FIX-01, FIX-02 | Yes (pinned in requirements.txt) | 2.2.3 | — |
| numpy | FIX-03 | Yes (pinned in requirements.txt) | 2.2.1 | — |
| pytest | FIX-04, test gate | Not in requirements.txt | Unknown | `pip install pytest` |

**Missing dependencies with fallback:**
- pytest: not in `requirements.txt`; must be installed in dev/CI environment. Add `pytest` to `requirements.txt` or a separate `requirements-dev.txt`. The phase plan must include this step.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `fillna(method='ffill')` | `.ffill()` chained call | pandas 1.5 deprecated, removed in 3.0 | No behavior change; eliminates FutureWarning |
| `Styler.applymap()` | `Styler.map()` | pandas 1.4 deprecated, pandas 2.1 renamed | No behavior change; eliminates FutureWarning |
| `while` day-loop | `np.busday_count()` | Available since numpy 1.7 (2012) | O(1) vs O(n_days); consistent with existing code |

---

## Open Questions

1. **Should `pytest` be added to `requirements.txt` or a separate `requirements-dev.txt`?**
   - What we know: `requirements.txt` currently contains only runtime deps; pytest is a dev/CI tool.
   - What's unclear: CI pipeline (`atualizar_dados.yml`) installs from `requirements.txt`; a separate dev file would not be auto-installed.
   - Recommendation: Add `pytest` to `requirements.txt` for simplicity given the small project size, unless a separate dev requirements file is preferred. The planner should decide.

2. **Does the negative-days branch of `dias_uteis_restantes` need to return business days or calendar days?**
   - What we know: The current code returns calendar days for past deadlines (`-int((hoje_d - deadline).days)`). The function is only called for business-day SLA classification, so using calendar days for the past-deadline case is a pre-existing behavior choice.
   - Recommendation: Preserve the calendar-day behavior for past deadlines (no change); this is an intentional design choice, not a bug.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection — `app/dashboard/dashboard.py` lines 48, 536, 591–607, 1169–1217, 1911–1916, 2158–2171
- Direct file inspection — `requirements.txt` (confirmed pandas 2.2.3, numpy 2.2.1)
- Direct file inspection — `.planning/codebase/CONCERNS.md` (audit source for all issues)
- Direct file inspection — `.planning/config.json` (confirmed `nyquist_validation: true`)

### Secondary (MEDIUM confidence)
- pandas 2.1 release notes: `Styler.applymap` → `Styler.map` rename, `fillna(method=)` deprecation
- pytest documentation: `filterwarnings` ini option format
- numpy documentation: `np.busday_count(begindates, enddates)` signature and exclusive-end semantics

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and pinned; no new dependencies
- Architecture: HIGH — all changes are one-to-one API swaps; templates already in codebase
- Pitfalls: HIGH — identified from direct code inspection and pandas changelog

**Research date:** 2026-03-25
**Valid until:** 2026-09-25 (stable APIs; pandas 3.x migration is the only horizon to watch)
