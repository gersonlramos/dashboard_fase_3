# Summary: 04-02 — ETL Helper Tests + HTTP Mock Tests

**Phase:** 04-test-suite-data-pipeline
**Plan:** 02
**Wave:** 2
**Status:** COMPLETE (`f9760ea`)

## What Was Done

Created `tests/test_etl_atualizacao.py` with 23 tests covering TEST-08 and TEST-09.

### TEST-08: `extrair_data_lake` and `classificar_subtarefa`

| Class                         | Tests | Key Cases                                                                                            |
| ----------------------------- | ----- | ---------------------------------------------------------------------------------------------------- |
| `TestExtrairDataLake`         | 8     | None, 'N/A', empty string, bracket+hyphen, bracket without hyphen, no brackets, whitespace stripping |
| `TestClassificarSubtarefaEtl` | 9     | Story Bug, RN-FMK, `\bRN\b` word boundary, None, default                                             |

`TestClassificarSubtarefaEtl` mirrors `TestClassificarSubtarefa` from `test_calculations.py` to verify the ETL copy stayed in sync with `calculations.py`.

### TEST-09: `buscar_com_paginacao` with mocked HTTP

| Test                                            | Scenario                     | Assertions                                     |
| ----------------------------------------------- | ---------------------------- | ---------------------------------------------- |
| `test_single_page_returns_all_issues`           | `isLast: True`, 1 issue      | 1 issue returned, `requests.get` called once   |
| `test_multi_page_accumulates_all_issues`        | 2 pages                      | 2 issues returned, `requests.get` called twice |
| `test_multi_page_second_call_includes_token`    | nextPageToken                | `params['nextPageToken']` in second call       |
| `test_401_returns_empty_list`                   | status 401                   | empty list, 1 call                             |
| `test_no_issues_in_response_returns_empty`      | `issues: []`                 | empty list                                     |
| `test_missing_next_page_token_stops_pagination` | `isLast: False` but no token | stops after 1 call                             |

Patch target: `unittest.mock.patch('script_atualizacao.requests.get', ...)`.

## Files Created

| File                            | Change                             |
| ------------------------------- | ---------------------------------- |
| `tests/test_etl_atualizacao.py` | NEW — 23 tests (TEST-08 + TEST-09) |

## Verification

```
pytest tests/test_etl_atualizacao.py -v → 23 passed in 0.62s
pytest tests/ -q → 95 passed (72 baseline + 23 new)
```

Zero network calls made during test run — all HTTP mocked.
