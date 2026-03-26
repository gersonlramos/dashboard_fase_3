# Phase 06-02 Summary: Confidence Band + Milestones

**Phase:** 06-timeline-forecast-view  
**Plan:** 02  
**Completed:** 2026-03-26

## What Was Built

- Implemented forecast chart logic in `📅 Previsão` tab:
  - P50 central trace
  - P85 upper trace with `fill='tonexty'` confidence band
  - linear fallback trace when Monte Carlo is unavailable
- Added milestone markers derived from `lakes_fase` (`max(data_fim)` per lake) using `add_vline` with string dates and lake labels.
- Ensured hover templates use `<extra></extra>` to suppress extra trace-name tooltip box.

## Files Modified

- `app/dashboard/dashboard.py`

## Verification

- `python -m pytest tests/test_smoke.py -q` passed
- `python -m pytest tests/test_forecast_calculations.py -q` passed
