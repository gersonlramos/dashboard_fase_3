# Phase 05, Plan 01 — Summary

## What Was Built

- Added "🗺️ Mapa de Migração" as the 5th item in the sidebar radio navigation.
- Inserted 4 module-level constants at lines 105–134 (after `plotly_legend_style`):
  - `STATUS_COLOR_MAP`: 12 status→hex color entries covering all real CSV statuses.
  - `STATUS_BUCKET`: 10 status→bucket-name mappings (5 buckets).
  - `BUCKET_ORDER`: ordered list `['Não Iniciado', 'Em Andamento', 'Concluído', 'Cancelado', 'Bloqueado']`.
  - `BUCKET_COLORS`: matching hex colors list.
- Inserted `_compute_heatmap_pivot(df)` helper function (before `carregar_dados`).
- Added `elif aba_selecionada == "🗺️ Mapa de Migração":` routing stub calling `_compute_heatmap_pivot`.

## Files Modified

- `app/dashboard/dashboard.py`

## Decisions

- Status bucket mapping uses `fillna('Bloqueado')` for any unrecognized status.
- Lakes are sorted alphabetically (9 lakes: BMC, CLIENTE, COMERCIAL, COMPRAS, FINANCE, MOPAR, RH, SHARED SERVICES, SUPPLY CHAIN).

## Commit

`c72c914`
