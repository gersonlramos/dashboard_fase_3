# Phase 02-02 Summary: Refresh Button + orjson

**Phase:** 02-performance  
**Plan:** 02  
**Completed:** 2026-03-26  
**Commits:** 4c38362, 09a4e77, 2443eb2, 5ea14a5, b808e53, af1c43c

## What Was Built

### Refresh Button

Added "🔄 Atualizar dados" button to the sidebar (above Filtros section):

```python
if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()
```

Styled with theme-aware CSS in both light and dark blocks: blue (`#1f77b4`) background, white text, rounded corners, no hover outline.

### orjson dependency

Added `orjson` to `requirements.txt` for faster JSON serialisation (used by Streamlit's cache serialiser).

## Bug Fixes Applied During Execution

| Bug                                                                 | Fix                                                                                                                |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `NameError: calcular_ciclo_desenvolvimento not defined` at line 458 | Replaced individual `.clear()` calls with `st.cache_data.clear()` — clears all cached functions atomically         |
| Button rendered with dark default style in light theme              | Added `[data-testid="stSidebar"] div[data-testid="stButton"]` + `[data-baseweb="button"]` CSS to both theme blocks |
| Dark hover rectangle on button                                      | Added `outline: none; box-shadow: none` to `:hover`, `:focus`, `:active`, `:focus-visible`                         |
| Tooltip appeared with dark background in light mode                 | Removed `help=` parameter from button entirely                                                                     |

## Files Modified

- `app/dashboard/dashboard.py` — button block + CSS in both theme blocks
- `requirements.txt` — added `orjson`

## Verification

Human checkpoint: ✅ approved by user 2026-03-26  
Regression: `pytest tests/test_phase1.py` → 14/14 passed

## Requirements Addressed

- PERF-03: manual cache invalidation via sidebar button
- PERF-04: orjson added to requirements
