# Code Conventions

**Analysis Date:** 2026-03-26

## Summary

Python-only project. No linter, formatter, or type-checker configuration present. Conventions below are inferred from source files in `app/` and `tests/`. A key architectural rule enforced by tests is that `dashboard.py` must never contain bare `except:` clauses, and the deprecated pandas `applymap` API must not appear in source.

---

## Language Style

- **Language:** Python 3.11
- **Indentation:** 4 spaces (PEP 8, no tabs observed)
- **Quotes:** Single quotes for plain strings; f-strings use whichever delimiter suits readability
- **Semicolons:** Not used
- **Type annotations:** None — no `typing` imports or annotations anywhere
- **Line length:** No enforced limit; `dashboard.py` has many lines exceeding 120 chars
- **Encoding:** UTF-8-BOM (`utf-8-sig`) for all CSV reads/writes to ensure Excel compatibility

---

## Naming Conventions

**Files:**
- Scripts: `snake_case` verb-noun — `script_atualizacao.py`, `extrair_historico.py`, `script_pendencias.py`
- Dashboard modules: flat short names — `dashboard.py`, `calculations.py`, `data_loader.py`
- Test files: `test_` prefix — `test_calculations.py`, `test_smoke.py`, `test_etl_atualizacao.py`
- CSV data: `SCREAMING_SNAKE_CASE` for main data (`FASE_3.csv`)

**Functions:**
- Public helpers: `snake_case` with Portuguese verb prefix — `calcular_curva_aprendizado()`, `carregar_dados_csv()`, `buscar_com_paginacao()`, `extrair_data_lake()`, `projetar_burndown()`
- Private/internal helpers: single leading underscore — `_make_response()`, `_write_csv()`, `_render_indicadores()`, `_barra()`

**Variables:**
- Module-level constants: `SCREAMING_SNAKE_CASE` — `DIR_DADOS`, `DADOS_DIR`, `SCRIPT_DIR`, `DASHBOARD_PATH`, `COLUMNS`, `CSV_HEADER`
- Local variables: `snake_case` in Portuguese — `historias_faltantes`, `ultima_data_real_bh`, `valores_planejado`, `ritmo`
- Short loop vars acceptable for numeric loops: `i`, `d`, `k`
- DataFrame column names: Portuguese with spaces matching CSV headers — `'Data-Lake'`, `'Titulo Historia'`, `'Status'`

**Classes:**
- Test classes only; PascalCase in English: `TestCalcularCurvaAprendizado`, `TestCarregarDadosCsv`, `TestBuscarComPaginacao`
- No production classes — the entire non-test codebase is procedural/functional

---

## Module Design

**Separation principle:** Pure calculation logic lives in `app/dashboard/calculations.py` — no Streamlit imports allowed there. This enables direct import in tests without triggering `st.set_page_config()` at module level in `dashboard.py`.

**Data loading:** `app/dashboard/data_loader.py` contains only raw I/O logic with no Streamlit cache decorators. The `dashboard.py` wraps the loader call with `@st.cache_data`.

**Scripts:** `app/scripts/` contains standalone ETL scripts that run independently of the dashboard. Key functions in these scripts are tested in `tests/test_etl_atualizacao.py` and `tests/test_data_loader_and_pendencias.py`.

**Imports:** stdlib first, then third-party, then local. No path aliases — local imports resolved via `sys.path.insert()` in `conftest.py` and individual test files.

**Exports:** No `__all__` defined. Functions are imported explicitly by name.

**Guard pattern for scripts:** `script_atualizacao.py` is guarded so it can be safely imported for testing without executing the ETL side effects. This was introduced in phase 04-01 (commit `cbbbc11`).

---

## Docstrings and Comments

**Docstrings:**
- Module-level docstrings explain file purpose and constraints (e.g., `calculations.py`, `conftest.py`, all test files)
- Function-level docstrings on public functions, written in Portuguese, plain prose style with `-` bullets for parameters:
  ```python
  def calcular_curva_aprendizado(...):
      """
      Gera pontos de uma curva sigmoide representando a curva de aprendizado do time.
      - inflexao: fracao do periodo onde o ritmo acelera (0.6 = 60% do periodo)
      """
  ```
- One-line docstrings for short helpers: `"""Raw CSV loader — no Streamlit cache."""`
- Test methods have no docstrings — the method name is the documentation

**Inline comments:**
- Used to explain non-obvious algorithm steps (sigmoid math, date normalization)
- Test file section dividers use box-drawing chars: `# ── TEST-02: calcular_curva_aprendizado ──────────────────────────────────────`
- Scripts use `# --- SECTION NAME ---` delimiters for major logic blocks
- All comments written in Portuguese

---

## Error Handling

**Rules enforced by tests:**
- Bare `except:` is forbidden — use `except (ValueError, TypeError)` or specific types (`except ParserError`)
- `applymap` must not appear in `dashboard.py` — use `df.style.map()` instead (pandas 2.x API)
- `FutureWarning` is elevated to error in `pytest.ini`, preventing silent pandas deprecation use

**Guard-clause pattern for null inputs:**
```python
if pd.isna(data_inicio) or pd.isna(data_fim) or total <= 0:
    return [], []
```
Functions return sentinel values (`[]`, `None`, `0`, `'N/A'`) for invalid inputs rather than raising.

**HTTP errors in scripts:** Check `response.status_code`, print error, return empty list or break — no exceptions raised to callers.

---

## Git Conventions

**Commit format:** Conventional Commits with Portuguese descriptions
```
feat(06-timeline-forecast-view): execute phase 06 forecast view
fix(05): heatmap cell text always black; remove lake filter selectbox
docs(04): phase 4 summaries, ROADMAP checkboxes, STATE advance to phase 5
chore: atualização automática dos dados Jira - 2026-03-26 13:34 UTC [skip ci]
```

**Types used:** `feat`, `fix`, `docs`, `chore`

**Scope format:**
- `(NN-slug)` for phase-level feature commits (e.g., `06-timeline-forecast-view`)
- `(NN)` for fixes within a phase (e.g., `(05)`)
- Omitted for cross-cutting changes

**`[skip ci]`** suffix on all automated Jira data-update commits to prevent CI feedback loops.

---

## Configuration Pattern

- All secrets via `python-dotenv`: `EMAIL`, `API_TOKEN` read from `.env` (gitignored)
- Paths built at runtime using `os.path.join(os.path.dirname(os.path.abspath(__file__)), ...)` — no hardcoded absolute paths
- Module-level constants defined before any function definitions
- Streamlit theme: `app/dashboard/.streamlit/config.toml`

---

## Gaps

- No type annotations anywhere
- No `__init__.py` files — scripts run directly, not imported as packages
- Inconsistent error handling style between scripts (`raise_for_status()` in one, status-code checks in others)
- `dashboard.py` is a monolith (2000+ lines) — strong candidate for modularization
- No automated formatter or linter enforced — code style consistency is manual
