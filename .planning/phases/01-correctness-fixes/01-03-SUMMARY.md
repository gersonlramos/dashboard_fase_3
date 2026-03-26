# Summary: 01-03 — Replace while-loop, tighten except, add Historia guard

**Phase:** 01-correctness-fixes  
**Plan:** 03  
**Completed:** 2026-03-25  
**Status:** ✅ Done

## What Was Built

Three sub-fixes applied to `dashboard.py`:

**FIX-03a:** Replaced `dias_uteis_restantes()` while-loop (O(n_days)) with `np.busday_count()`.  
Implementation note: shifted both bounds +1 day (`hoje_d+1` → `deadline+1`) so `np.busday_count`'s inclusive-start semantics match the while-loop's exclusive-start — confirmed equivalent for all weekday and weekend deadlines.

**FIX-03b:** Tightened bare `except:` at line 536 to `except (ValueError, TypeError):` — prevents silent swallowing of `KeyboardInterrupt` and `SystemExit`.

**FIX-03c:** Added column existence guard to `Historia` references at lines 1911–1916 using list comprehensions (`[c for c in list if c in df_filtrado.columns]`) — prevents `KeyError` when CSV does not include the `Historia` column.

Added 5 `test_fix03_*` tests to `tests/test_phase1.py`.

## Verification

```
pytest tests/test_phase1.py -k "fix03" → 5 passed
grep "except:" app/dashboard/dashboard.py → 0 matches
```

## Files Modified

- `app/dashboard/dashboard.py` — 3 targeted edits (FIX-03a/b/c)
- `tests/test_phase1.py` — 5 test*fix03*\* tests appended
