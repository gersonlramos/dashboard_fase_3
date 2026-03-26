# Summary: 03-02 — Unit tests for calculations.py

**Phase:** 03-test-suite-calculations  
**Plan:** 02  
**Wave:** 2  
**Status:** COMPLETE (`322efbf`)

## What Was Done

Created `tests/test_calculations.py` with 57 unit tests covering all 7 functions:

| Class                          | Function                     | Tests | Edge Cases                                                |
| ------------------------------ | ---------------------------- | ----- | --------------------------------------------------------- |
| `TestCalcularCurvaAprendizado` | `calcular_curva_aprendizado` | 8     | NaT start/end, total=0, single-day, monotonicity          |
| `TestCalcularDiasUteis`        | `calcular_dias_uteis`        | 7     | NaT, same day, fim<inicio, weekend skip                   |
| `TestColoriStatus`             | `colorir_status`             | 8     | all known statuses (parametrized), unknowns               |
| `TestClassificarSubtarefa`     | `classificar_subtarefa`      | 9     | None, case-insensitive, word boundary RN                  |
| `TestNormalizarIdHistoria`     | `normalizar_id_historia`     | 8     | None, NaT, brackets, various hyphen spacing               |
| `TestParseDataCriacao`         | `parse_data_criacao`         | 5     | None, empty, ISO, BR, standard datetime                   |
| `TestProjetarBurndown`         | `projetar_burndown`          | 7     | zero/negative ritmo, optimistic/pessimistic, prazo cutoff |

## Files Created

| File                         | Change                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `tests/test_calculations.py` | NEW — 57 unit tests                                                            |
| `conftest.py` (project root) | NEW — `sys.path.insert` so AppTest exec'd dashboard.py can import calculations |

## Key Technical Notes

- `np.busday_count` exclusive-start semantics: Mon→Fri = 4 (not 5). Tests assert 4.
- `sys.path.insert` at module level in `test_calculations.py` (and via root conftest for AppTest) — needed because `calculations.py` sits in `app/dashboard/`, not on the default path.
- Root `conftest.py` is the correct place to set `sys.path` for AppTest since AppTest exec's the script in the same Python process but doesn't inherit path from test module imports.

## Verification

```
pytest tests/test_calculations.py -v → 57 passed in 0.60s
pytest tests/ -v → 72 passed (57 new + 14 phase1 + 1 smoke)
```
