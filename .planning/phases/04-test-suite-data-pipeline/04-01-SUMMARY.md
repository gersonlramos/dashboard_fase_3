# Summary: 04-01 — Guard ETL script + extract data_loader.py

**Phase:** 04-test-suite-data-pipeline
**Plan:** 01
**Wave:** 1
**Status:** COMPLETE (`cbbbc11`)

## What Was Done

### Task 1: Guard `script_atualizacao.py`

Everything from line 100 onwards (`# --- BUSCAR TODOS OS ÉPICOS DO PROJETO ---` and all execution code below it) was wrapped in `if __name__ == '__main__':`. Lines 1-99 (imports, config vars, and three function defs: `extrair_data_lake`, `classificar_subtarefa`, `buscar_com_paginacao`) remain at module scope unchanged.

Result: `import script_atualizacao` completes silently with zero network calls.

### Task 2: Extract `carregar_dados_csv` + update `dashboard.py`

Created `app/dashboard/data_loader.py` with the exact CSV-loading body from `carregar_dados` (including the `ParserError` fallback), but without the `@st.cache_data` decorator and without any Streamlit import.

Updated `dashboard.py`:

- Added `from data_loader import carregar_dados_csv` at line 14
- Replaced `carregar_dados` body with `return carregar_dados_csv(arquivo)` (1 line)

The `@st.cache_data(ttl=900)` decorator and function signature remain on `carregar_dados` in `dashboard.py` — it is now a thin cache wrapper.

## Files Modified / Created

| File                                | Change                                                        |
| ----------------------------------- | ------------------------------------------------------------- |
| `app/scripts/script_atualizacao.py` | Added `if __name__ == '__main__':` guard at line 100          |
| `app/dashboard/data_loader.py`      | NEW — `carregar_dados_csv(arquivo)` pure CSV loader           |
| `app/dashboard/dashboard.py`        | Added import; replaced carregar_dados body with delegate call |

## Verification

- `cd app/scripts && python -c "import script_atualizacao; print(script_atualizacao.extrair_data_lake('[COMPRAS-123]'))"` → `COMPRAS` (no HTTP output)
- `cd app/dashboard && python -c "from data_loader import carregar_dados_csv; print('OK')"` → `OK`
- `pytest tests/ -q` → 72 passed (no regressions)
