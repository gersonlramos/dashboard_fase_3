# Summary: 03-01 — Extract calculations.py + conftest fixture

**Phase:** 03-test-suite-calculations  
**Plan:** 01  
**Wave:** 1  
**Status:** COMPLETE (`bbd1187`)

## What Was Done

- Created `app/dashboard/calculations.py` with 7 pure-Python functions extracted verbatim from `dashboard.py` and `script_atualizacao.py`:
  - `calcular_curva_aprendizado` (sigmoid learning-curve projection)
  - `calcular_dias_uteis` (business-day counter via `np.busday_count`)
  - `colorir_status` (CSS colour lookup for status strings)
  - `normalizar_id_historia` (strip/upper/hyphen-normalize Jira IDs)
  - `parse_data_criacao` (multi-format date parser)
  - `classificar_subtarefa` (regex-based category classifier)
  - `projetar_burndown` (lifted from inner closure — was `gerar_projecao` — with all captured vars as explicit params)
- Added `from calculations import (...)` at `dashboard.py` line 9; replaced the `gerar_projecao` inner closure with three `projetar_burndown(...)` calls.
- Created `tests/conftest.py` with `sample_df` fixture (3-row DataFrame matching the real FASE_3.csv 13-column schema).

## Files Modified / Created

| File                            | Change                                        |
| ------------------------------- | --------------------------------------------- |
| `app/dashboard/calculations.py` | NEW — 7 extracted functions                   |
| `app/dashboard/dashboard.py`    | Added import; replaced gerar_projecao closure |
| `tests/conftest.py`             | NEW — sample_df pytest fixture                |

## Key Decisions

- `projetar_burndown` needed explicit parameters (ritmo, prazo_limite, historias_faltantes, total_planejado, realizado_atual, ultima_data_real_bh) because it was a closure capturing those names from the enclosing scope — not extractable verbatim without signature changes.
- No functions removed from `dashboard.py`; the `from calculations import` shadows them, preserving runtime behavior while enabling isolated testing.

## Verification

- `python -c "from calculations import calcular_curva_aprendizado, ..."` → ALL OK
- `pytest tests/test_phase1.py -q` → 14 passed (regression gate maintained)
