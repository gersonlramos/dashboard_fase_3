# Code Conventions

**Analysis Date:** 2026-03-25

## Summary

Python-only project with a Streamlit dashboard (`app/dashboard/dashboard.py`) and three data-extraction scripts under `app/scripts/`. No linter, formatter, or type-checker configuration is present. Conventions below are inferred from the four source files.

## Language Style

- **Language:** Python 3.11 (pinned in `.devcontainer/devcontainer.json` and `.github/workflows/atualizar_dados.yml`)
- **Indentation:** 4 spaces (PEP 8, no tabs observed)
- **Quotes:** Single quotes for plain strings (`'utf-8-sig'`, `'Todos'`); f-strings use double-quoted delimiters where readability benefits
- **Semicolons:** Not used
- **Type annotations:** None — no `typing` imports or annotations anywhere in the codebase
- **Line length:** No enforced limit; `dashboard.py` has many long lines (80–120+ chars)
- **Encoding:** UTF-8-BOM (`utf-8-sig`) for all CSV reads/writes to ensure Excel compatibility

## Naming Conventions

**Files:**
- Scripts: `snake_case` with verb-noun pattern — `script_atualizacao.py`, `extrair_historico.py`, `script_pendencias.py`
- Dashboard: single flat name — `dashboard.py`
- CSV data files: `SCREAMING_SNAKE_CASE` for main data (`FASE_3.csv`), `lowercase-with-hyphens` for historics (`historico_completo-BMC.csv`)
- Directories: `snake_case` — `app/dados/`, `app/scripts/`, `app/dashboard/`

**Functions:**
- Public helpers: `snake_case` with verb prefix — `calcular_curva_aprendizado()`, `carregar_dados()`, `buscar_com_paginacao()`, `extrair_campos()`
- Private/internal helpers: single leading underscore — `_render_indicadores()`, `_paginar_jql()`, `_barra()`
- Nested helpers: defined inside caller scope — `_barra` inside `_render_indicadores`, `parse_data_criacao` inside data loading block in `dashboard.py`

**Variables:**
- Module-level constants: `SCREAMING_SNAKE_CASE` — `DIR_DADOS`, `EMAIL`, `API_TOKEN`, `EPIC`, `FIELDS`, `URL_SEARCH`, `JIRA_BASE_URL`
- Local variables: `snake_case` — `all_issues`, `next_page_token`, `epic_key`, `batch_size`
- Temporary/loop variables in `dashboard.py`: short underscore-prefixed names — `_bg`, `_txt`, `_brd`, `_df_l`, `_pct_pl`
- DataFrame column names: Portuguese with spaces, matching CSV headers — `'Data-Lake'`, `'Titulo Historia'`, `'Status Antigo'`

**Constants:**
- `SCREAMING_SNAKE_CASE` throughout all scripts: `DIR_DADOS`, `FILE_CSV`, `FILE_HISTORICO`, `URL_ISSUE`, `AUTH`
- In `dashboard.py`, theme variables use `snake_case` with domain prefix: `plotly_template`, `plotly_font_color`, `plotly_paper_bgcolor`, `plotly_axis_style`

## Component/Module Patterns

- No classes — the entire codebase is procedural/functional
- `dashboard.py` is a single-file monolith (2351 lines): imports → constants → helper functions → `st.set_page_config()` → CSS injection → data loading → sidebar → UI sections rendered top to bottom
- Scripts follow: imports → constants → helper functions → imperative execution at module level
- Only `script_pendencias.py` uses a `main()` function with an entry-point guard pattern (called explicitly at bottom, no `if __name__ == '__main__'`)
- `script_atualizacao.py` and `extrair_historico.py` execute at import time with no `main()` guard
- Inline HTML/CSS rendered through `st.markdown(..., unsafe_allow_html=True)` — no template files

## Import Organization

No automated sorter (`isort`, `ruff`) is configured. Observed order:

1. Standard library (`os`, `re`, `csv`, `datetime`, `glob`)
2. Third-party packages (`requests`, `urllib3`, `pandas`, `numpy`, `streamlit`, `plotly`)
3. Local imports: none (no shared internal packages/modules)

Notable deviation: `import glob` appears deferred inside a function body (`calcular_ciclo_desenvolvimento` in `dashboard.py`) rather than at file top.

`load_dotenv()` is called immediately after imports in all scripts that use environment variables.

## Comment Style

- Section headers use `# --- SECTION NAME ---` delimiters for major logic blocks in scripts
- Heavier separator style in `script_pendencias.py`: `# ---------------------------------------------------------------------------`
- Inline comments explain non-obvious decisions: `# Reduzido para respeitar limite do Jira`
- `print()` statements used pervasively for execution logging — no logging framework
- All comments and docstrings written in **Portuguese (Brazilian)**

## Documentation Style

- **Docstrings:** Triple double-quoted strings, used selectively — not on all functions
- Format: plain prose with parameter bullets (no NumPy/Google/Sphinx style):
  ```python
  def calcular_curva_aprendizado(data_inicio, data_fim, total, inflexao=0.6, inclinacao=9, ...):
      """
      Gera pontos de uma curva sigmoide representando a curva de aprendizado do time.
      - inflexao: fração do período onde o ritmo acelera (0.6 = 60% do período)
      ...
      """
  ```
- One-line docstrings for simple helpers:
  ```python
  def _paginar_jql(jql, expand=None):
      """Executa um JQL com paginação e retorna todas as issues."""
  ```
- Module-level docstring present only in `extrair_historico.py`
- Variable/function names are in Portuguese: `epicos`, `historias`, `pendencias`, `arquivo_saida`, `calcular_dias_uteis`

## Error Handling Patterns

- HTTP errors: check `response.status_code != 200`, print message, then `break` or `exit(1)` — used in `script_atualizacao.py` and `extrair_historico.py`
- `script_pendencias.py` uses `resp.raise_for_status()` — more idiomatic, inconsistent with other scripts
- Date parsing: `pd.to_datetime(..., errors='coerce')` for safe handling of malformed dates
- CSV loading: `try/except ParserError` with manual fallback parser in `carregar_dados()` in `dashboard.py`
- Top-level `try/except Exception as e: print(...)` wraps the batch-processing block in `script_atualizacao.py`
- `dashboard.py` uses `st.error()` and `st.stop()` when critical data files are missing

## Configuration Pattern

- All secrets via `python-dotenv`: `EMAIL`, `API_TOKEN` read from `.env` (gitignored)
- Paths built at runtime: `os.path.join(os.path.dirname(os.path.abspath(__file__)), ...)` — no hardcoded absolute paths
- Constants defined at module top before any function definitions
- Streamlit theme: `app/dashboard/.streamlit/config.toml`

## Linting & Formatting

- **No tools configured** — no `.flake8`, `.pylintrc`, `ruff.toml`, `pyproject.toml`, `setup.cfg`, `.pre-commit-config.yaml`, or `.editorconfig`
- VS Code extensions in devcontainer: `ms-python.python`, `ms-python.vscode-pylance` (static analysis, no formatter enforced)
- Code style consistency is entirely manual

## Gaps

- No type annotations anywhere — parameter types must be inferred from usage
- No `__init__.py` files — scripts are run directly, not imported as packages
- Inconsistent error handling style across scripts
- Nested function definitions inline in `dashboard.py` instead of extracted to module level
- `dashboard.py` at 2351 lines is a strong candidate for modularization
