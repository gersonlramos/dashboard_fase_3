# Features Research

**Researched:** 2026-03-25
**Domain:** Plotly/Streamlit dashboard features — migration heatmaps, timeline/forecast views, velocity trends, UX patterns
**Confidence:** HIGH (core Plotly patterns), MEDIUM (forecast model selection), HIGH (Streamlit UX)

---

## Summary

This research covers two new views for the GCP→AWS migration dashboard: a **migration heatmap** (status grid per data-lake) and a **timeline/forecast view** (projected end date with confidence range and milestone markers). The existing codebase uses `go.Figure` / `px.*` with `plotly_template` theme switching throughout — new charts must follow the same pattern to stay consistent with dark/light mode.

The real data has 9 lakes (BMC, CLIENTE, COMERCIAL, COMPRAS, FINANCE, MOPAR, RH, SHARED SERVICES, SUPPLY CHAIN), one Epic per lake, histories per lake ranging from 1 (BMC) to 127 (SHARED SERVICES), and 7 observed status values: `Open`, `To Do`, `In progress`, `In Test`, `Waiting Test`, `Done`, `Canceled`. The project is at an early stage — COMPRAS is the most active lake with subtasks in many states; most lakes have nearly all subtasks still `Open`.

**Primary recommendation:** Build the heatmap as a `px.imshow()` on a numeric-encoded status matrix (9 lakes × N categories), and the forecast view as a `go.Scatter` timeline reusing the existing `±30% velocity` pattern already proven in the burndown chart, augmented with `fill='tonexty'` confidence bands and `add_vline`/`add_vrect` milestone markers.

---

## Migration Heatmap Patterns

### What the heatmap should show

Two sensible variants — pick based on PM feedback:

| Variant | Rows | Columns | Cell value |
|---------|------|---------|------------|
| **A — Progress grid** | Data-Lake (9) | Status category (7) | Count of subtasks OR % of lake total |
| **B — Completion rate** | Data-Lake (9) | Fixed columns: % Done, % In Progress, % Blocked/Open | Gradient 0–100% |

Variant B is more scannable for a single-page executive view. Variant A shows full distribution.

### Recommended data transformation

```python
# Canonical status grouping (map 7 raw values to 5 display buckets)
STATUS_BUCKET = {
    "Open":         "Backlog",
    "To Do":        "Backlog",
    "In progress":  "Em andamento",
    "In Test":      "Em andamento",
    "Waiting Test": "Em andamento",
    "Done":         "Concluído",
    "Canceled":     "Cancelado",
}

# Pivot: rows = lakes, columns = buckets, values = count
df["bucket"] = df["Status"].map(STATUS_BUCKET).fillna("Outro")
pivot = (
    df.groupby(["Data-Lake", "bucket"])
    .size()
    .unstack(fill_value=0)
)
# Normalize to % of row total
pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
```

The `pct` DataFrame (9 rows × 5 cols) feeds directly into `px.imshow()`.

### Plotly approach: `px.imshow()` (recommended)

The official Plotly docs now recommend `px.imshow()` over the deprecated `ff.create_annotated_heatmap`. Source: [Plotly Annotated Heatmaps docs](https://plotly.com/python/annotated-heatmap/).

```python
import plotly.express as px

fig = px.imshow(
    pct,                          # numpy array or DataFrame
    x=pct.columns.tolist(),       # bucket names
    y=pct.index.tolist(),         # lake names
    color_continuous_scale=[      # discrete-style stops (see color section)
        [0.0,  "#2d4a6b"],        # 0% done → deep blue-grey
        [0.3,  "#e8a838"],        # 30% → amber
        [0.7,  "#2ca02c"],        # 70% → green
        [1.0,  "#1a6e1a"],        # 100% → deep green
    ],
    zmin=0, zmax=100,
    text_auto=".0f",              # show integer % in each cell
    aspect="auto",
)
fig.update_traces(
    hovertemplate="%{y}<br>%{x}: %{z:.1f}%<extra></extra>",
    textfont_size=12,
)
fig.update_layout(
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    font=dict(color=plotly_font_color),
    coloraxis_showscale=False,    # hide sidebar colorbar for status heatmap
    margin=dict(l=120, r=20, t=40, b=60),
    height=320,
)
```

For Variant A (raw count matrix), use `go.Heatmap` directly:

```python
import plotly.graph_objects as go

# STATUS_NUMERIC maps status string → integer rank for color encoding
STATUS_NUMERIC = {
    "Cancelado": 0, "Backlog": 1, "Em andamento": 2,
    "Em teste": 3, "Concluído": 4
}

# Build z matrix: shape (n_lakes, n_histories) — one cell per story
# Sort histories by planned start date for consistent column order
z = []  # list of lists
for lake in LAKE_ORDER:
    row = [STATUS_NUMERIC.get(bucket_of(row), 1) for row in lake_stories]
    z.append(row)

fig = go.Figure(go.Heatmap(
    z=z,
    x=story_ids,
    y=LAKE_ORDER,
    colorscale=DISCRETE_COLORSCALE,  # see color section
    zmin=0, zmax=4,
    xgap=2, ygap=2,           # cell spacing for visual separation
    hovertemplate="%{y}<br>Story %{x}<br>Status: %{text}<extra></extra>",
    text=status_text_matrix,
))
```

Note: `xgap` and `ygap` are `go.Heatmap`-specific; `px.imshow` does not expose them directly.

### Key `go.Heatmap` parameters (confidence: HIGH — from official docs)

| Parameter | Purpose |
|-----------|---------|
| `z` | 2D list/array of numeric values |
| `x` | Column labels (stories or buckets) |
| `y` | Row labels (lake names) |
| `colorscale` | List of `[0–1 stop, color]` pairs |
| `zmin` / `zmax` | Anchor the color scale |
| `xgap` / `ygap` | Pixel gap between cells |
| `text` | 2D matrix of strings shown in each cell |
| `hovertemplate` | Custom hover using `{y}`, `{x}`, `{z}`, `{text}` |

### Data shape summary

```
DataFrame shape for px.imshow:
  rows    = 9 (one per data lake)
  columns = 5 (one per status bucket)
  values  = float 0–100 (percentage of lake subtasks in that bucket)

DataFrame shape for story-level go.Heatmap:
  rows    = 9 (lakes)
  columns = max(stories_per_lake) — SHARED SERVICES has 127
  values  = int 0–4 (status rank)
  → 127 columns is borderline for readability; consider filtering
    to a selected lake when shown at story level
```

### Color schemes for status categories

The project already has a partial color map in `colorir_status`. This research recommends a consolidated, WCAG-aware palette:

| Status bucket | Color (dark theme) | Color (light theme) | Hex |
|--------------|-------------------|---------------------|-----|
| Backlog / Open | Steel blue | Light blue | `#4a7fc1` / `#5ba3d9` |
| Em andamento | Amber / orange | Orange | `#e8a838` / `#f0a050` |
| Em teste | Purple | Lavender | `#9467bd` / `#b490d8` |
| Concluído | Green | Dark green | `#2ca02c` / `#1a8c1a` |
| Cancelado | Muted grey | Mid grey | `#7f7f7f` / `#999` |
| Bloqueado* | Red | Crimson | `#d62728` / `#c0392b` |

*No "Bloqueado" status exists in current data but should be reserved.

WCAG note: Color alone is insufficient. Always pair with text labels inside cells (text_auto or annotation_text). Contrast ratio between amber (#e8a838) and dark background (#1b2a3b) is ~5.8:1 — passes WCAG AA. Green (#2ca02c) on dark background is ~4.2:1 — passes. Source: [Carbon Design accessible palettes](https://medium.com/carbondesign/color-palettes-and-accessibility-features-for-data-visualization-7869f4874fca).

Discrete colorscale for `go.Heatmap` (0–4 numeric ranks):

```python
HEATMAP_COLORSCALE = [
    [0.00, "#7f7f7f"],  # 0 = Cancelado (grey)
    [0.20, "#7f7f7f"],
    [0.20, "#4a7fc1"],  # 1 = Backlog (blue)
    [0.40, "#4a7fc1"],
    [0.40, "#e8a838"],  # 2 = Em andamento (amber)
    [0.60, "#e8a838"],
    [0.60, "#9467bd"],  # 3 = Em teste (purple)
    [0.80, "#9467bd"],
    [0.80, "#2ca02c"],  # 4 = Concluído (green)
    [1.00, "#2ca02c"],
]
```

This step-function pattern (each color appears at two consecutive stops) creates perfectly discrete bands with no interpolation. Source: [Plotly community thread on discrete heatmap colors](https://community.plotly.com/t/colors-for-discrete-ranges-in-heatmaps/7780).

---

## Timeline / Forecast View Patterns

### The existing forecast approach (must stay consistent)

The burndown chart already implements:
- Planned line (`planejado_acum`)
- Actual line (`realizado_acum`)
- Projection (current velocity): ±30% band (`ritmo_hist_dia * 1.3` / `* 0.7`)
- Best/worst cases as separate dashed `go.Scatter` traces
- `add_vline` for "Hoje" marker

The new Timeline/Forecast view should **reuse and extend** this pattern, not replace it.

### Three forecast model options

| Model | Inputs | Complexity | Best for |
|-------|--------|-----------|---------|
| **Linear extrapolation** (current) | Velocity last N days | Low | Stable teams, late project |
| **Rolling-window velocity** | 7-day or 14-day rolling mean | Low–Medium | Detecting acceleration/deceleration |
| **Monte Carlo simulation** | Distribution of daily velocities | Medium | Probabilistic confidence intervals |

**Recommendation for this project:** Rolling-window velocity as the primary projection, with Monte Carlo for the confidence band. Rationale: the project has sparse real completions (most lakes still Open), so a rolling window over the few existing `Done` events will be too noisy. Monte Carlo sampling from daily-throughput distribution gives honest uncertainty bounds even with thin data.

### Monte Carlo algorithm (confidence: HIGH — multiple sources agree)

The standard approach used by Expedia Engineering, Scrum.org, and Agile Seekers:

```python
import numpy as np

def monte_carlo_forecast(
    daily_throughput: list[float],  # historical done-per-day series
    remaining: int,                 # subtasks/stories still to complete
    n_simulations: int = 5000,
    seed: int = 42,
) -> dict:
    """
    Returns P50, P70, P85, P95 completion date offsets (days from today).
    """
    rng = np.random.default_rng(seed)
    if len(daily_throughput) < 3:
        # Insufficient data — fall back to linear
        return None

    throughput_arr = np.array(daily_throughput)
    results = []
    for _ in range(n_simulations):
        days = 0
        completed = 0
        while completed < remaining:
            # Sample one day's throughput from historical distribution
            daily = rng.choice(throughput_arr)
            completed += max(0, daily)
            days += 1
            if days > 365 * 2:  # safety cap — 2 years
                break
        results.append(days)

    results_arr = np.array(results)
    return {
        "p50": int(np.percentile(results_arr, 50)),
        "p70": int(np.percentile(results_arr, 70)),
        "p85": int(np.percentile(results_arr, 85)),
        "p95": int(np.percentile(results_arr, 95)),
    }
```

Source: [Monte Carlo Forecasting in Software Delivery — Expedia Group Tech](https://medium.com/expedia-group-tech/monte-carlo-forecasting-in-software-delivery-474bb49cb3f9), [Agile Forecasting with Monte Carlo — Agile Seekers](https://agileseekers.com/blog/using-monte-carlo-simulations-to-predict-delivery-timelines).

**Recommended percentile display:**
- **P50** — median forecast (label: "Previsão Central")
- **P85** — conservative commitment date (label: "Previsão Conservadora")
- Shaded band between P50 and P85 using `fill='tonexty'`

### Milestone markers on Plotly timeline

Two approaches depending on what fits:

**`add_vline` — vertical dashed line per milestone:**
```python
milestones = {
    "Cutover BMC":   pd.Timestamp("2026-04-07"),
    "Cutover COMPRAS": pd.Timestamp("2026-04-16"),
    # ... derive from datas_esperadas_por_lake.csv data_fim per lake
}

for label, date in milestones.items():
    fig.add_vline(
        x=date,
        line_dash="dot",
        line_color="#ff7f0e",          # orange — consistent with Gantt phases
        line_width=1.5,
        annotation_text=label,
        annotation_position="top left",
        annotation_font_color=plotly_font_color,
        annotation_font_size=10,
    )
```

**`add_vrect` — shaded band for a phase gate window:**
```python
fig.add_vrect(
    x0=phase_start, x1=phase_end,
    fillcolor="rgba(255, 127, 14, 0.12)",  # semi-transparent orange
    line_width=0,
    layer="below",
    annotation_text="Fase Homologação",
    annotation_position="top left",
)
```

Source: [Plotly Shapes docs](https://plotly.com/python/shapes/).

**Important caveat:** `add_vline` with datetime x-axis has a known issue in some Plotly versions (see [GitHub issue #3065](https://github.com/plotly/plotly.py/issues/3065)) where `x` must be passed as a string `"YYYY-MM-DD"`, not a Timestamp object. The existing codebase already uses the offset-day workaround in the Gantt chart (`_hoje_off = (pd.Timestamp.now().normalize() - _data_ref).days`). For the new timeline, use date strings directly since the x-axis will be real dates (not offset integers).

### Forecast band construction

```python
# Upper bound trace (invisible line to set fill target)
fig.add_trace(go.Scatter(
    x=forecast_dates,
    y=forecast_p85,
    mode="lines",
    line=dict(color="rgba(0,0,0,0)", width=0),  # invisible
    name="P85",
    showlegend=False,
))

# Lower bound trace — fills to the previous (upper) trace
fig.add_trace(go.Scatter(
    x=forecast_dates,
    y=forecast_p50,
    fill="tonexty",
    fillcolor="rgba(44, 160, 44, 0.15)",   # green semi-transparent
    mode="lines",
    line=dict(color="#2ca02c", dash="dash", width=1.5),
    name="Intervalo P50–P85",
))
```

Source: [Plotly Filled Area Plots docs](https://plotly.com/python/filled-area-plots/).

### Milestone data source

`datas_esperadas_por_lake.csv` provides per-story planned start/end dates (columns: `squad`, `lake`, `id_historia`, `numero`, `titulo`, `papel`, `recurso`, `duracao_dias_uteis`, `data_inicio`, `data_fim`). The last `data_fim` per lake = planned cutover date for that lake. This file is the canonical source for milestone markers.

```python
lakes_fim = (
    pd.read_csv(DADOS_DIR / "datas_esperadas_por_lake.csv")
    .assign(data_fim=lambda d: pd.to_datetime(d["data_fim"], dayfirst=True))
    .groupby("lake")["data_fim"]
    .max()
    .reset_index()
)
```

---

## Velocity Trend Visualization

### What "velocity trend" means in this project

`ritmo_hist_dia` (stories completed per calendar day) is already calculated in the burndown. The trend is whether this rate is increasing (team accelerating) or decreasing (team slowing down).

### Rolling mean approach

```python
# Requires: burn_real series — one row per date with 'realizado' count
burn_real["rolling_7d"] = (
    burn_real.set_index("data")["realizado"]
    .rolling("7D", min_periods=1)
    .mean()
    .values
)
burn_real["rolling_14d"] = (
    burn_real.set_index("data")["realizado"]
    .rolling("14D", min_periods=1)
    .mean()
    .values
)
```

Plot both windows on the same axis; the gap between them shows acceleration (14d > 7d = slowing recently) or deceleration (7d > 14d = recent pickup).

### Acceleration indicator

```python
if len(burn_real) >= 14:
    recent_7d = burn_real["realizado"].tail(7).sum() / 7
    prior_7d  = burn_real["realizado"].iloc[-14:-7].sum() / 7
    delta_pct = (recent_7d - prior_7d) / max(prior_7d, 0.001) * 100
    # delta_pct > 0  → accelerating
    # delta_pct < 0  → decelerating
```

Display this as a `st.metric` delta:
```python
st.metric(
    label="Velocidade (7d)",
    value=f"{recent_7d:.2f} hist/dia",
    delta=f"{delta_pct:+.1f}% vs semana anterior",
    delta_color="normal",   # green = up, red = down
    help="Média de histórias concluídas por dia nos últimos 7 dias úteis",
)
```

### Visualization on the forecast chart

Add the rolling velocity as a secondary y-axis area chart beneath the burnup:

```python
fig.add_trace(go.Scatter(
    x=burn_real["data"],
    y=burn_real["rolling_7d"],
    mode="lines",
    fill="tozeroy",
    fillcolor="rgba(148, 103, 189, 0.15)",  # purple, semi-transparent
    line=dict(color="#9467bd", width=1),
    name="Velocidade 7d (hist/dia)",
    yaxis="y2",
))

fig.update_layout(
    yaxis2=dict(
        title="Velocidade (hist/dia)",
        overlaying="y",
        side="right",
        showgrid=False,
        **plotly_axis_style,
    )
)
```

Note: Secondary y-axis requires `go.Figure`, not `px.*`. The existing dashboard already uses `go.Figure` throughout — no change in approach needed.

### Current data caveat

As of 2026-03-25, only COMPRAS has meaningful `Done`/`In Test`/`Waiting Test` counts. BMC has 19 subtasks `In progress` but 0 `Done`. Most lakes are entirely `Open`. Velocity charts will be sparse or zero for most lakes at this stage. The implementation should:
1. Show the velocity chart only when `len(burn_real) >= 3`
2. Otherwise display: `st.info("Dados insuficientes para calcular velocidade — aguardando primeiras conclusões.")`

---

## UX Patterns for Streamlit Dashboards

### `st.metric` with sparklines and tooltips (Streamlit 1.55)

The project uses Streamlit 1.55 (from PROJECT.md). `st.metric` in 1.55 supports:
- `label` — displayed above value
- `value` — main number/text
- `delta` — change indicator (red/green arrow)
- `delta_color` — `"normal"` / `"inverse"` / `"off"`
- `help` — tooltip shown on hover next to label
- `border` — border around card (available in recent 1.x versions)

Source: [st.metric docs](https://docs.streamlit.io/develop/api-reference/data/st.metric).

In Streamlit 1.55, `chart_data`, `delta_description`, and `delta_arrow` may not be available (these appear in 2025 releases). Do not rely on them. Verify against the installed version before use.

```python
# Safe pattern for 1.55:
st.metric(
    label="Previsão de Conclusão",
    value="15/06/2026",
    delta="12 dias atrasado",
    delta_color="inverse",  # red = late (inverse because later = worse)
    help="Baseado na velocidade média dos últimos 14 dias úteis",
)
```

### Metric card layout patterns

The existing dashboard uses `st.columns` for metric rows extensively (e.g., `col_burn1, col_burn2, col_burn3, col_burn4 = st.columns(4)`). For the new views, follow the same pattern:

```python
# Per-lake summary row above the heatmap
col_done, col_prog, col_open, col_forecast = st.columns(4)
with col_done:
    st.metric("Concluídas", f"{done_pct:.0f}%", delta=f"{done_pct - planned_pct:.1f}% vs plano")
with col_prog:
    st.metric("Em Andamento", str(in_progress_count))
with col_open:
    st.metric("Backlog Restante", str(open_count))
with col_forecast:
    st.metric("Previsão Entrega", forecast_date_str, delta=delta_str, delta_color=delta_color)
```

### `st.expander` for detail drill-down

```python
with st.expander("Ver detalhes por História"):
    st.dataframe(
        df_lake_detail.style.applymap(colorir_status, subset=["Status"]),
        use_container_width=True,
        height=300,
    )
```

Use expanders for: per-lake story lists, Monte Carlo simulation parameters, raw CSV inspection. Keeps the executive view clean.

### Tab placement recommendation

The existing tab navigation is sidebar-based (`st.sidebar.radio`). For the new views:
- Add "Heatmap" and "Previsão" as new options in the existing `aba_selecionada` sidebar radio
- Render each view inside the existing `if aba_selecionada == "..."` conditional blocks
- This avoids introducing a second navigation pattern

### Hover tooltip best practices

The existing dashboard uses `hovertemplate` on Plotly traces. Follow the established pattern:

```python
hovertemplate=(
    "<b>%{y}</b><br>"          # lake name in bold
    "Status: %{text}<br>"      # status label from text matrix
    "Histórias: %{z:.0f}%<br>" # numeric value
    "<extra></extra>"           # removes trace name box
)
```

`<extra></extra>` is critical — without it, Plotly appends the trace name in a separate box, cluttering the tooltip.

### Color-consistency rule

The existing codebase uses these colors for status in tables (from `colorir_status`):
- Done → `#90EE90` (light green) for table cells
- In Progress → `#87CEEB` (sky blue) for table cells
- To Do → `#FFE4B5` (moccasin) for table cells

The heatmap should use **different, more saturated** colors because it uses fill vs. text background. The table colors are very light (pastel) and will not read as distinct in a heatmap. Use the saturated palette from the Color Schemes section above.

---

## Table Stakes vs Differentiators

### Table stakes (users expect these)

| Feature | Why expected | Implementation effort |
|---------|-------------|----------------------|
| Status summary per lake | Core migration visibility | Low — pivot FASE_3.csv |
| Planned vs actual completion % | Standard PMO output | Already done in existing burndown |
| Single end-date forecast | Any PM tool provides this | Already done (±30% band) |
| Color coding by status | Universal UX convention | Low — follow existing colorir_status |
| "Today" marker on timeline | Standard on any Gantt/timeline | Already done (add_vline "Hoje") |
| Dark/light theme | Already in the dashboard | Free — reuse plotly_template variable |

### Differentiators (notable / not commonly seen)

| Feature | Why differentiating | Implementation effort |
|---------|--------------------|-----------------------|
| Monte Carlo confidence band on forecast | Honest probabilistic range vs. false precision of single-number forecast | Medium — numpy sampling, ~50 lines |
| Velocity trend with acceleration signal | Shows if the team is speeding up or slowing — rare in PMO dashboards | Medium — rolling window + secondary y-axis |
| Per-lake completion heatmap with text overlay | Visual, scannable, actionable — not just a table | Low-Medium — px.imshow, ~40 lines |
| Milestone cutover markers on burnup | Connects planned delivery to actual trajectory in one view | Low — add_vline loop over lakes_fim |
| P50 vs P85 distinction explained in UI | Most tools hide the math; showing percentiles builds trust | Low — st.metric help parameter |
| `st.metric` forecast cards above charts | Sets executive context before detail | Low — follow existing metric row pattern |

### What NOT to build

| Feature | Reason to skip |
|---------|---------------|
| Interactive backlog editor | Dashboard is read-only; data comes from Jira via CI |
| Per-story Gantt (127 stories for SHARED SERVICES) | Too dense; existing per-lake Gantt already covers this |
| Real-time Jira API calls from dashboard | No live DB constraint; CSV-only architecture is locked |
| Animation / auto-play timeline | Poor UX in dashboard context; adds complexity without value |
| Custom JS components | Would require `unsafe_allow_html` already flagged as XSS risk |

---

## Implementation Notes for the Planner

### Heatmap integration point

The heatmap fits naturally in a new `aba_selecionada == "Heatmap"` block. It requires no new data files — only FASE_3.csv (already loaded as `df`). The pivot/percentage transform is 10 lines of pandas.

### Forecast/timeline integration point

The forecast view requires `datas_esperadas_por_lake.csv` (already loaded as `lakes_fase`) and the existing `burn_real_acum` / `ritmo_hist_dia` variables computed in the burndown section. Both are global-scope variables already computed before the tab rendering blocks.

### Monte Carlo data availability

As of March 2026, `burn_real_acum` is near-empty (only COMPRAS has completions). The Monte Carlo implementation must gracefully degrade: if fewer than 3 distinct days of throughput data exist, skip Monte Carlo and show only the linear projection with the existing ±30% band.

### Dependency on `@st.cache_data`

PROJECT.md notes that `carregar_dados()` lacks `@st.cache_data`. Adding a heatmap (which reads FASE_3.csv) and a forecast view (which reads datas_esperadas_por_lake.csv) will increase per-interaction reload time further. The planner should schedule cache addition before or alongside these features.

---

## Sources

### Primary (HIGH confidence)
- [Plotly Heatmaps docs](https://plotly.com/python/heatmaps/) — `go.Heatmap` parameter reference
- [Plotly Annotated Heatmap docs](https://plotly.com/python/annotated-heatmap/) — `px.imshow()` recommended over `ff.create_annotated_heatmap`
- [Plotly Filled Area Plots](https://plotly.com/python/filled-area-plots/) — `fill='tonexty'`, `fillcolor` for forecast bands
- [Plotly Shapes](https://plotly.com/python/shapes/) — `add_vline`, `add_vrect` for milestones
- [Streamlit st.metric docs](https://docs.streamlit.io/develop/api-reference/data/st.metric) — `help`, `delta_color`, `border`
- Codebase analysis of `dashboard.py` (2,351 lines) — existing patterns, variable names, color conventions

### Secondary (MEDIUM confidence)
- [Monte Carlo Forecasting in Software Delivery — Expedia Group Tech](https://medium.com/expedia-group-tech/monte-carlo-forecasting-in-software-delivery-474bb49cb3f9) — P50/P85 percentile recommendations, algorithm structure
- [Agile Forecasting Monte Carlo — Agile Seekers](https://agileseekers.com/blog/using-monte-carlo-simulations-to-predict-delivery-timelines) — confirms sampling approach
- [Carbon Design accessible color palettes](https://medium.com/carbondesign/color-palettes-and-accessibility-features-for-data-visualization-7869f4874fca) — contrast ratios for heatmap colors
- [Plotly community — discrete heatmap colorscales](https://community.plotly.com/t/colors-for-discrete-ranges-in-heatmaps/7780) — step-function colorscale technique

### Tertiary (LOW confidence — flag for validation)
- Streamlit 1.55 specific feature availability for `border`, `chart_data`, `delta_description` in `st.metric` — docs show 2025 release notes; verify against installed version before implementing

---

## Metadata

**Confidence breakdown:**
- Heatmap data shape and `px.imshow` approach: HIGH — verified against official Plotly docs
- Discrete colorscale step-function: MEDIUM — verified via community thread + official colorscale docs
- Monte Carlo algorithm: MEDIUM — multiple practitioner sources agree, no official Plotly/Streamlit doc
- Streamlit `st.metric` parameters: HIGH for basic params (label/value/delta/help), LOW for newer params (chart_data, delta_description) in Streamlit 1.55 specifically
- Milestone `add_vline`/`add_vrect`: HIGH — official Plotly docs

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (Plotly and Streamlit are stable; check Streamlit 1.55 changelog before implementing metric card sparklines)
