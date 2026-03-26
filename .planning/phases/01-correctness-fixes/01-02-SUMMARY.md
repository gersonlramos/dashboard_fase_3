# Summary: 01-02 — Fix applymap deprecation

**Phase:** 01-correctness-fixes  
**Plan:** 02  
**Completed:** 2026-03-25  
**Status:** ✅ Done

## What Was Built

- Replaced `df_render.style.applymap(colorir_status, subset=['Status'])` at `dashboard.py:1214` with `style.map(...)` — `Styler.applymap` was renamed to `Styler.map` in pandas 2.1; the old name emits FutureWarning
- Added 3 `test_fix02_*` tests to `tests/test_phase1.py`

## Verification

```
pytest tests/test_phase1.py -k "fix02" → 3 passed
grep applymap app/dashboard/dashboard.py → 0 matches
```

## Files Modified

- `app/dashboard/dashboard.py` — line 1214: `style.map(` (was `style.applymap(`)
- `tests/test_phase1.py` — 3 test*fix02*\* tests appended
