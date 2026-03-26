# Summary: 01-04 — Install pytest.ini FutureWarning gate

**Phase:** 01-correctness-fixes  
**Plan:** 04  
**Completed:** 2026-03-25  
**Status:** ✅ Done

## What Was Built

- Created `pytest.ini` at project root with `filterwarnings = error::FutureWarning` + `ignore::urllib3.exceptions.InsecureRequestWarning`
- Added 2 `test_fix04_*` tests to `tests/test_phase1.py`
- Full suite: **14/14 tests passed**

## Verification

```
pytest tests/test_phase1.py -v → 14 passed in 1.56s
python -W error::FutureWarning -c "import pandas; import numpy" → no error
```

## Files Modified

- `pytest.ini` — created at project root
- `tests/test_phase1.py` — 2 test*fix04*\* tests appended

## Phase Success Criteria

- [x] Running `python -W error::FutureWarning -c "import pandas"` produces no warnings/exceptions
- [x] `pytest tests/test_phase1.py` exits 0 (14 passed)
- [x] Detalhes table `style.map()` fix in place (test_fix02_applymap_absent)
- [x] SLA business-day values match previous loop-based output (test_fix03_busday_matches_while_loop)
