# Summary: 03-03 — AppTest smoke test

**Phase:** 03-test-suite-calculations  
**Plan:** 03  
**Wave:** 2  
**Status:** COMPLETE (`322efbf`)

## What Was Done

Created `tests/test_smoke.py` with a Streamlit AppTest smoke test:

```python
def test_dashboard_loads_without_exception():
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=60)
    at.run()
    assert not at.exception
```

- `autouse=True` fixture clears `st.cache_data` before and after each test to prevent stale cache contamination.
- Uses real CSV data on disk (no mocking needed — AppTest runs the full dashboard in isolated Streamlit session state).
- Resolved `ModuleNotFoundError: No module named 'calculations'` by adding `sys.path.insert` at module level in the root `conftest.py` — AppTest runs in the same process, so path additions are visible to the exec'd dashboard script.

## Files Created

| File                  | Change                   |
| --------------------- | ------------------------ |
| `tests/test_smoke.py` | NEW — AppTest smoke test |

## Key Technical Notes

- Streamlit 1.55.0 has `AppTest` in `streamlit.testing.v1` (available since 1.28 ✅).
- `at.run()` runs the full dashboard script synchronously in the test thread.
- `at.exception` is an `ElementList`; testing `not at.exception` (falsy when empty) is the right pattern.
- `st.set_page_config()` in dashboard.py does NOT crash AppTest (only direct `import dashboard` triggers it).

## Verification

```
pytest tests/test_smoke.py -v → 1 passed in 7.70s
pytest tests/ -v → 72 passed total
```
