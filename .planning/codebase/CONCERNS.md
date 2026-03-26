# Codebase Concerns

**Analysis Date:** 2026-03-25

## Critical Issues

**SSL verification disabled across all HTTP requests:**
- All three scripts disable SSL certificate verification (`verify=False`) and suppress the resulting warnings with `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)`
- Files: `app/scripts/script_atualizacao.py` (lines 80, 113, 139, 243), `app/scripts/extrair_historico.py` (line 94), `app/scripts/script_pendencias.py` (line 102)
- Impact: MITM attacks can intercept Jira API tokens in transit. Justification comment says "corporate networks," but this disables all certificate chain validation unconditionally, including in CI/CD on GitHub Actions runners.

**Deprecated pandas API in active code path:**
- `fillna(method='ffill')` is deprecated since pandas 2.1 and raises a `FutureWarning` (removed in future versions). The project pins `pandas==2.2.3`, so it still runs but will break on the next pandas major release.
- File: `app/dashboard/dashboard.py` line 48 inside `calcular_curva_aprendizado()`
- Fix: replace with `.ffill()` chained call.

**`DataFrame.applymap` deprecated (renamed to `map`):**
- `df_render.style.applymap(colorir_status, subset=['Status'])` at line 1214 uses `applymap`, which was deprecated in pandas 1.4+ and renamed to `map`. Will produce `FutureWarning` at runtime.
- File: `app/dashboard/dashboard.py` line 1214

## Technical Debt

**Monolithic dashboard file (2,351 lines):**
- `app/dashboard/dashboard.py` contains the entire application: data loading, business logic, statistical calculations (sigmoid curve, burndown, burnup, SLA classification), and UI rendering all in a single flat script.
- No functions or modules separate concerns. Adding new views or modifying calculations requires navigating a very large file with no clear structure.
- Fix: Extract computation functions to `app/dashboard/calculations.py` and rendering helpers to `app/dashboard/components.py`.

**Hardcoded project and epic keys across scripts:**
- `projeto = "BF3E4"` in `app/scripts/script_atualizacao.py` line 21
- `EPIC = "BF3E4-293"` in `app/scripts/script_pendencias.py` line 21
- Epic-to-name mapping hardcoded as a dict in `app/scripts/extrair_historico.py` lines 23–32
- File references `pendencias_BF3E4-293.csv` and `historico_BF3E4-293.csv` hardcoded in `app/dashboard/dashboard.py` lines 1921–1922
- Impact: Extending to another project or adding a new epic requires editing multiple unrelated source files with no single point of configuration.

**Hardcoded Jira base URL:**
- `url = "https://fcagil.atlassian.net/rest/api/3/search/jql"` appears in all three scripts without env var fallback.
- Files: `app/scripts/script_atualizacao.py` line 17, `app/scripts/extrair_historico.py` line 19, `app/scripts/script_pendencias.py` lines 13–14

**Hardcoded burn-up start date:**
- `data_inicio_burnup = pd.Timestamp('2026-03-13')` hardcoded in `app/dashboard/dashboard.py` line 947
- Impact: When the project phase changes, this date must be manually updated in the source file.

**Duplicate status list definitions:**
- "Done/Closed/Resolved/Concluído/Concluida/Canceled/Cancelled" is defined as a set or list in at least 5 different places throughout `app/dashboard/dashboard.py` (lines 276, 495, 822, 979, 1933). Any change to canonical status names requires updating all sites.

**Bare `except:` clause silences all errors:**
- Inside `parse_data_criacao()` at line 536 of `app/dashboard/dashboard.py`, a `except:` with no exception type catches everything including `KeyboardInterrupt` and `SystemExit`. Errors in date parsing are silently swallowed, making debugging difficult.

**Custom CSV parser with fragile column-count assumptions:**
- `carregar_dados()` in `app/dashboard/dashboard.py` lines 395–422 contains a fallback CSV parser that assumes exactly 11 columns and infers the `Titulo` field by position. If the CSV schema changes (columns added/removed), this silently produces corrupt data instead of raising an error.

**`script_atualizacao.py` is not a proper Python module:**
- The script executes top-level API calls at import time (lines 100–133 call the Jira API and `exit()` at module scope). It cannot be imported, tested, or reused as a library.
- Files: `app/scripts/script_atualizacao.py`

## Security Concerns

**API credentials in environment variables — correct, but no rotation mechanism:**
- `EMAIL` and `API_TOKEN` are loaded via `python-dotenv` locally and passed as GitHub Actions secrets (`JIRA_EMAIL`, `JIRA_API_TOKEN`). This is the correct approach.
- Risk: No evidence of token expiry monitoring or rotation policy. A leaked token would grant read access to the Atlassian workspace.

**`unsafe_allow_html=True` used throughout the dashboard:**
- Multiple `st.markdown(..., unsafe_allow_html=True)` calls render raw HTML strings built from Jira data (issue titles, descriptions, etc.)
- File: `app/dashboard/dashboard.py` — pervasive throughout the file
- Risk: If a Jira issue title or description contains a `<script>` tag or malicious HTML, it will be injected into the dashboard DOM. This is an XSS vector if the dashboard is ever exposed publicly or to untrusted users.
- Current mitigation: Dashboard likely runs on internal/controlled network only.

**Data committed to git repository:**
- All extracted CSV files under `app/dados/` (including `FASE_3.csv`, history files, and pendency files) are committed to the repository by the CI workflow. This means all Jira issue titles, statuses, and assignee-adjacent data are permanently in git history.
- File: `.github/workflows/atualizar_dados.yml` lines 57–63

## Performance Concerns

**SLA business-days calculation uses a Python loop:**
- `dias_uteis_restantes()` in `app/dashboard/dashboard.py` lines 2158–2171 iterates day-by-day in a `while` loop to count business days instead of using `numpy.busday_count`. As the number of pending items grows, this is called once per row and runs on every Streamlit rerender.
- Fix: Replace with `np.busday_count(hoje_d, deadline)` consistent with `calcular_dias_uteis()` already defined at line 592.

**Full history files reloaded on every dashboard render:**
- `calcular_ciclo_desenvolvimento()` in `app/dashboard/dashboard.py` lines 609–738 uses `glob.glob` and `pd.read_csv` inside a function that is called during each Streamlit render cycle. With 9 history CSV files, this performs 9 disk reads per render. No caching (`@st.cache_data`) is applied.

**Linear projection uses full dataframe iteration:**
- `calcular_ciclo_desenvolvimento()` iterates every row of the combined history dataframe inside a nested loop (per-issue, per-history-item) without vectorization. For large history datasets this will be slow.

**No `@st.cache_data` on data loading:**
- `carregar_dados()` at line 383 and all history loading functions lack `@st.cache_data` decorator. Every user interaction reruns the full data loading pipeline from disk.

## Dependency Concerns

- `streamlit==1.55.0` — This is an extremely recent version (released early 2025). The project is pinned to an exact version. Any `pip install` in CI will use this exact release, which is good for reproducibility. However, `applymap` and `fillna(method=...)` deprecations suggest the code was written against an older pandas API without being updated.
- `pandas==2.2.3` — Current stable, but the deprecated `fillna(method='ffill')` and `applymap` calls will break on pandas 3.x.
- No `pip-compile` or lockfile beyond `requirements.txt` — transitive dependency versions are not pinned, so the `pip install -r requirements.txt` in CI could pick up incompatible transitive versions.

## Incomplete Areas

**`quantidade_subtarefas` field is always zero:**
- In `app/scripts/script_atualizacao.py` line 284, the variable `quantidade_subtarefas` is initialized to `0` and written directly to the CSV without ever being populated. The column exists in `FASE_3.csv` but contains no meaningful data.

**`jql_customizado` in `extrair_historico.py` is never used:**
- `jql_customizado = ""` at line 38 and `tipo_busca` is hardcoded to `"epic"` at line 36. The `jql` branch at lines 61–63 is dead code — it can never be reached in the current script structure because `tipo_busca` is never changed at runtime.
- File: `app/scripts/extrair_historico.py`

**`Historia` column referenced but may not exist:**
- Line 1912 references `df_filtrado['Historia']` as a column, but the CSV schema produced by `script_atualizacao.py` does not include a `Historia` column (the field is `Titulo Historia`). This would raise a `KeyError` at runtime when "Exibir todas as colunas" is checked.

## Code Quality

**Inconsistent variable naming styles:**
- Some variables use `snake_case` (`data_inicio`, `epic_key`), others use short prefixed names (`_bg`, `_txt`, `_brd`, `_bg_bar`) indicating internal state in inline functions, and others use single-letter names (`f`, `k`, `v`). No convention is documented.

**Magic numbers for projection adjustments:**
- `ritmo_hist_dia * 1.3` (optimistic) and `ritmo_hist_dia * 0.7` (pessimistic) appear in both the burndown and burnup projection calculations without named constants or comments explaining the ±30% basis.
- Files: `app/dashboard/dashboard.py` lines 927–928, 1059–1060

**Magic numbers for sigmoid curve:**
- `inflexao=0.6` and `inclinacao=9` are default parameters in `calcular_curva_aprendizado()` at line 14. These are documented in the docstring but appear as raw numbers in caller sites without named constants.

**Duplicate theme-switching logic:**
- The pattern `"#1b2a3b" if tema_selecionado != "☀️ Claro" else "#ffffff"` (or similar color pairs) is repeated dozens of times throughout `app/dashboard/dashboard.py` instead of being stored in a theme dict computed once.

**`import glob` inside a function body:**
- `import glob` appears inside `calcular_ciclo_desenvolvimento()` at line 615 rather than at the top of the module. This is a style inconsistency with all other imports.

**Bare `continue` silences CSV read errors:**
- In `calcular_ciclo_desenvolvimento()` lines 658–663, a `except Exception as e:` catches all read errors and continues silently, so a corrupt history file would be ignored without any user-visible warning.

## Recommended Priorities

1. **Fix deprecated pandas API calls** — `fillna(method='ffill')` at line 48 of `app/dashboard/dashboard.py` and `applymap` at line 1214 will cause runtime failures when pandas 3 is adopted. Low-effort, high-risk fix.
2. **Add `@st.cache_data` to data loading functions** — `carregar_dados()` and the history-loading inside `calcular_ciclo_desenvolvimento()` re-read all CSV files on every Streamlit interaction. Adding the decorator prevents this with minimal code change.
3. **Replace the looping `dias_uteis_restantes()` with `np.busday_count`** — Consistent with `calcular_dias_uteis()` already in the codebase, eliminates the O(n_days) loop.
4. **Consolidate the duplicate status set definitions** — Define `STATUS_DONE` and `STATUS_CANCELED` as module-level constants once in `app/dashboard/dashboard.py` and reference them throughout.
5. **Escape user-provided content before rendering via `unsafe_allow_html`** — At minimum, apply HTML escaping to Jira-sourced strings (titles, descriptions) before injecting them into markdown HTML blocks to prevent XSS if the dashboard is ever exposed beyond a controlled network.

---

*Concerns audit: 2026-03-25*
