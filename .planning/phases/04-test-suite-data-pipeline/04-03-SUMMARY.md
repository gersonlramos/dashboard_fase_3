# Summary: 04-03 — Data Loader Tests + ADF Converter Tests

**Phase:** 04-test-suite-data-pipeline
**Plan:** 03
**Wave:** 2
**Status:** COMPLETE (`f9760ea`)

## What Was Done

Created `tests/test_data_loader_and_pendencias.py` with 21 tests covering TEST-10 and TEST-11.

> **Note:** The plan specified two separate files (`test_data_loader.py` and `test_etl_pendencias.py`), but both test classes were combined into a single file. All stated behaviors are covered.

### TEST-10: `carregar_dados_csv`

| Test                                                 | Assertion                                                 |
| ---------------------------------------------------- | --------------------------------------------------------- |
| `test_valid_csv_returns_dataframe`                   | Returns `pd.DataFrame` instance                           |
| `test_valid_csv_row_count`                           | 3 rows from 3-row CSV                                     |
| `test_valid_csv_correct_columns`                     | `list(df.columns) == COLUMNS` (all 13 exact names)        |
| `test_first_column_no_bom_prefix`                    | No `\ufeff` in `df.columns[0]` despite utf-8-sig encoding |
| `test_file_not_found_returns_none`                   | Returns `None`                                            |
| `test_empty_csv_header_only_returns_empty_dataframe` | 0 rows, 13 columns                                        |
| `test_single_row_csv`                                | Status and Data-Lake values correct                       |

CSV fixtures written via `tmp_path` (pytest built-in), using `utf-8-sig` encoding to match production.

### TEST-11: `adf_para_texto`

All documented ADF node types covered:

| Node Type                      | Expected Output                    |
| ------------------------------ | ---------------------------------- |
| `None`                         | `""`                               |
| `str`                          | str as-is                          |
| `list`                         | joined children                    |
| `{"type": "text"}`             | `node["text"]`                     |
| `{"type": "hardBreak"}`        | `"\n"`                             |
| `{"type": "paragraph"}`        | children + `"\n"`                  |
| `{"type": "heading"}`          | children + `"\n"`                  |
| `{"type": "bulletList"}`       | `"• item\n• item\n"`               |
| `{"type": "orderedList"}`      | `"1. item\n2. item\n"`             |
| unknown type                   | joined children (no extra newline) |
| non-dict/str/list (int, float) | `""`                               |
| nested doc                     | flattened correctly                |

## Files Created

| File                                       | Change                             |
| ------------------------------------------ | ---------------------------------- |
| `tests/test_data_loader_and_pendencias.py` | NEW — 21 tests (TEST-10 + TEST-11) |

## Verification

```
pytest tests/test_data_loader_and_pendencias.py -v → 21 passed in 0.90s
pytest tests/ -q → 116 passed (95 + 21)
```
