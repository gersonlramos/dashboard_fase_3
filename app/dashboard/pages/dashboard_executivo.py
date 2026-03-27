import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
import sys
from datetime import datetime, timezone, timedelta

# Garante que dashboard/ esteja no path (quando rodado via st.navigation)
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))   # pages/
_dashboard_dir = os.path.dirname(SCRIPT_DIR)                   # dashboard/
if _dashboard_dir not in sys.path:
    sys.path.insert(0, _dashboard_dir)

from calculations import get_completion_dates
from data_loader import carregar_dados_csv

# Diretorios — pages/ -> dashboard/ -> app/
APP_DIR    = os.path.dirname(_dashboard_dir)
DADOS_DIR  = os.path.join(APP_DIR, 'dados')
ASSETS_DIR = os.path.join(APP_DIR, 'assets')


# Carregar dados
arquivo_selecionado = os.path.join(DADOS_DIR, "FASE_3.csv")
df = carregar_dados_csv(arquivo_selecionado)
if df is None:
    st.error(f"Arquivo '{arquivo_selecionado}' nao encontrado!")
    st.stop()
if 'Chave' in df.columns and 'Deadline Historia' in df.columns:
    df = get_completion_dates(df, DADOS_DIR)
else:
    df['Completion Date'] = pd.to_datetime(df['Deadline Historia'], errors='coerce')

# Normalizar Data-Lake
df['Data-Lake'] = df['Data-Lake'].astype(str).str.strip().str.upper()

# Logo acima da navegação de páginas (CSS aumenta a altura do slot)
_logo_path = os.path.join(ASSETS_DIR, "AIR_logo.png")
if os.path.exists(_logo_path):
    st.logo(_logo_path, size="large")
    st.markdown("""
    <style>
        [data-testid="stLogo"] { height: 4rem !important; max-width: 100% !important; }
        [data-testid="stLogo"] img { height: 4rem !important; width: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# Data de atualização — calculada antes da sidebar para uso no rodapé
_data_atu_str = "—"
if os.path.exists(arquivo_selecionado):
    _mtime = datetime.fromtimestamp(os.path.getmtime(arquivo_selecionado), tz=timezone(timedelta(hours=-3)))
    _data_atu_str = _mtime.strftime('%d/%m/%Y %H:%M')

st.sidebar.header("🔍 Filtros")
data_lakes_unicos = ['Todos'] + sorted([str(d) for d in df['Data-Lake'].unique() if pd.notna(d) and str(d) not in ['N/A', 'NAN']])
data_lake_selecionado = st.sidebar.selectbox("Data-Lake:", data_lakes_unicos, index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Configurações")
tema_selecionado = st.sidebar.radio("Tema:", ["🌙 Escuro", "☀️ Claro"], index=0, horizontal=True)
st.sidebar.markdown(f"📅 **Atualizado em:** {_data_atu_str}")

# ── Configurações de tema ──────────────────────────────────────────────────────
plotly_template      = "plotly_white" if tema_selecionado == "☀️ Claro" else "plotly_dark"
plotly_font_color    = "#0d1b2a"      if tema_selecionado == "☀️ Claro" else "#e8edf2"
plotly_paper_bgcolor = "#f0f4f8"      if tema_selecionado == "☀️ Claro" else "#0d1b2a"
plotly_plot_bgcolor  = "#ffffff"      if tema_selecionado == "☀️ Claro" else "#1b2a3b"
plotly_axis_style = dict(
    tickfont=dict(color="#0d1b2a"),
    title_font=dict(color="#0d1b2a"),
    linecolor="#1f77b4",
    gridcolor="#c8daf0"
) if tema_selecionado == "☀️ Claro" else dict(
    tickfont=dict(color="#e8edf2"),
    title_font=dict(color="#e8edf2"),
    linecolor="#1f77b4",
    gridcolor="#1e3048"
)
plotly_legend_style = dict(
    font=dict(color="#0d1b2a"),
    title=dict(font=dict(color="#0d1b2a")),
    bgcolor="#f0f4f8",
    bordercolor="#1f77b4",
    borderwidth=1
) if tema_selecionado == "☀️ Claro" else dict(
    font=dict(color="#e8edf2"),
    title=dict(font=dict(color="#e8edf2")),
    bgcolor="#1b2a3b",
    bordercolor="#1f77b4",
    borderwidth=1
)

hr_style = "<hr style='margin: 10px 0; border: 1px solid #1a3a5c;'/>" if tema_selecionado == "☀️ Claro" else "<hr style='margin: 10px 0; border: 1px solid #2a4a6b;'/>"

# ── Filtrar dados ──────────────────────────────────────────────────────────────
df_filtrado = df.copy()
if data_lake_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Data-Lake'] == data_lake_selecionado]

# ── Banner ──────────────────────────────────────────────────────────────────────
_banner_path = os.path.join(ASSETS_DIR, "cover LD_profissionais_01.png")
if os.path.exists(_banner_path):
    st.image(_banner_path, use_container_width=True)

_hoje = pd.Timestamp(datetime.now(timezone(timedelta(hours=-3))).date())

_status_done = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled'}

# ── Monta df_lake ──────────────────────────────────────────────────────────────
_tem_datas_jira = 'Start Date Historia' in df.columns and 'Deadline Historia' in df.columns
if _tem_datas_jira:
    df_lake = (
        df[['Titulo Historia', 'Data-Lake', 'Start Date Historia', 'Deadline Historia']]
        .drop_duplicates(subset='Titulo Historia')
        .rename(columns={
            'Titulo Historia':     'titulo',
            'Data-Lake':           'lake',
            'Start Date Historia': 'data_inicio',
            'Deadline Historia':   'data_fim',
        })
        .copy()
    )
    df_lake['id_historia'] = df_lake['titulo'].str.extract(r'(\[[^\]]+\])', expand=False)
else:
    _csv_lake = os.path.join(DADOS_DIR, 'datas_esperadas_por_lake.csv')
    if os.path.exists(_csv_lake):
        df_lake = pd.read_csv(_csv_lake, encoding='utf-8-sig')
        df_lake['lake'] = df_lake['lake'].astype(str).str.strip().str.upper()
        df_lake['lake'] = df_lake['lake'].str.replace(r'\s+[A-Z]$', '', regex=True)
    else:
        df_lake = pd.DataFrame(columns=['id_historia', 'titulo', 'lake', 'data_inicio', 'data_fim'])

df_lake['lake'] = df_lake['lake'].astype(str).str.strip().str.upper()

# _df_lake_pct: schedule por lake com data_fim como Timestamp
_df_lake_pct = df_lake.copy()
_df_lake_pct['data_fim'] = pd.to_datetime(_df_lake_pct['data_fim'], errors='coerce', dayfirst=True)


# ── Progresso — Seleção Atual ──────────────────────────────────────────────────
def _render_indicadores(df_base):
    """Renderiza cards de progresso reagindo ao df_base (já filtrado)."""
    _bg      = "#1b2a3b" if tema_selecionado != "☀️ Claro" else "#ffffff"
    _txt     = "#e8edf2" if tema_selecionado != "☀️ Claro" else "#0d1b2a"
    _brd     = "#1f3a5c" if tema_selecionado != "☀️ Claro" else "#d0dff0"
    _bg_bar  = "#1e3048" if tema_selecionado != "☀️ Claro" else "#e0e8f0"

    def _barra(pct, cor):
        return f"""<div style="background:{_bg_bar}; border-radius:8px; height:14px; width:100%;
                               margin-top:6px; overflow:hidden;">
            <div style="width:{min(pct,100):.1f}%; background:{cor}; height:100%; border-radius:8px;"></div>
        </div>"""

    lakes_no_filtro = sorted(df_base['Data-Lake'].dropna().unique())
    if not lakes_no_filtro:
        return

    df_plan_filtrado = _df_lake_pct[_df_lake_pct['lake'].isin(lakes_no_filtro)]

    _total_hist = df_plan_filtrado['id_historia'].nunique()
    _hist_plan  = (df_plan_filtrado['data_fim'] <= _hoje).sum()
    _pct_plan   = (_hist_plan / _total_hist * 100) if _total_hist > 0 else 0.0

    _total_sub  = len(df_base)
    _done_sub   = df_base['Status'].astype(str).str.strip().str.lower().isin(_status_done).sum()
    _pct_real   = (_done_sub / _total_sub * 100) if _total_sub > 0 else 0.0
    _delta      = _pct_real - _pct_plan
    _cor_delta  = "#2ca02c" if _delta >= 0 else "#d62728"
    _sinal      = "▲" if _delta >= 0 else "▼"

    # ── Card geral ──
    st.markdown(f"""
    <div style="background:{_bg}; border:1px solid {_brd}; border-radius:10px;
                padding:20px 24px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <span style="font-weight:700; font-size:20px; color:{_txt};">📊 Progresso — Seleção Atual</span>
            <span style="font-size:20px; color:{_cor_delta}; font-weight:700;">
                {_sinal} {abs(_delta):.1f}% vs planejado
            </span>
        </div>
        <div style="display:flex; gap:40px;">
            <div style="flex:1;">
                <div style="font-size:15px; color:#aaa; font-weight:600; margin-bottom:4px;">Planejado</div>
                <div style="font-size:32px; font-weight:800; color:#5ba3d9;">{_pct_plan:.1f}%</div>
                {_barra(_pct_plan, "#5ba3d9")}
            </div>
            <div style="flex:1;">
                <div style="font-size:15px; color:#aaa; font-weight:600; margin-bottom:4px;">Realizado</div>
                <div style="font-size:32px; font-weight:800; color:{_cor_delta};">{_pct_real:.1f}%</div>
                {_barra(_pct_real, _cor_delta)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cards por lake ──
    if data_lake_selecionado == 'Todos' or len(lakes_no_filtro) <= 1:
        return

    _lake_stats = []
    for _lake in lakes_no_filtro:
        _df_l   = _df_lake_pct[_df_lake_pct['lake'] == _lake]
        _tot_l  = _df_l['id_historia'].nunique()
        _pl_l   = (_df_l['data_fim'] <= _hoje).sum()
        _pct_pl = (_pl_l / _tot_l * 100) if _tot_l > 0 else 0.0

        _df_s   = df_base[df_base['Data-Lake'] == _lake]
        _tot_s  = len(_df_s)
        _dn_s   = _df_s['Status'].astype(str).str.strip().str.lower().isin(_status_done).sum()
        _pct_rl = (_dn_s / _tot_s * 100) if _tot_s > 0 else 0.0

        _lake_stats.append({"lake": _lake, "planejada": _pct_pl, "realizada": _pct_rl})

    cols_por_linha = 3
    for i in range(0, len(_lake_stats), cols_por_linha):
        bloco = _lake_stats[i:i + cols_por_linha]
        cols  = st.columns(cols_por_linha)
        for col, stat in zip(cols, bloco):
            _pl = stat["planejada"]
            _rl = stat["realizada"]
            _dc = "#2ca02c" if _rl >= _pl else "#d62728"
            with col:
                st.markdown(f"""
                <div style="background:{_bg}; border:1px solid {_brd}; border-radius:8px;
                            padding:14px 16px; margin-bottom:10px;">
                    <div style="font-weight:700; font-size:14px; color:{_txt};
                                margin-bottom:10px; border-bottom:1px solid {_brd}; padding-bottom:6px;">
                        {stat['lake']}
                    </div>
                    <div style="font-size:13px; color:#aaa; font-weight:600; margin-bottom:2px;">Planejado</div>
                    <div style="font-size:22px; font-weight:800; color:#5ba3d9;">{_pl:.1f}%</div>
                    {_barra(_pl, "#5ba3d9")}
                    <div style="font-size:13px; color:#aaa; font-weight:600; margin:10px 0 2px 0;">Realizado</div>
                    <div style="font-size:22px; font-weight:800; color:{_dc};">{_rl:.1f}%</div>
                    {_barra(_rl, _dc)}
                </div>
                """, unsafe_allow_html=True)


_render_indicadores(df_filtrado)

st.markdown(hr_style, unsafe_allow_html=True)

# ── Planejado Vs Realizado e Tendência — Tabelas e Views ──────────────────────
_csv_obj = os.path.join(DADOS_DIR, 'quantidades_objetos_historias.csv')
if os.path.exists(_csv_obj):
    _df_obj = pd.read_csv(_csv_obj, sep=';', encoding='latin-1')
    _df_obj['tabelas'] = pd.to_numeric(_df_obj['tabelas'], errors='coerce').fillna(0)
    _df_obj['views']   = pd.to_numeric(_df_obj['views'],   errors='coerce').fillna(0)
    _df_obj['objetos'] = _df_obj['tabelas'] + _df_obj['views']

    _hist_deadlines = (
        df[['Historia', 'Data-Lake', 'Deadline Historia']]
        .drop_duplicates(subset='Historia')
        .rename(columns={'Deadline Historia': 'deadline'})
    )
    _df_obj = _df_obj.merge(_hist_deadlines, left_on='Id', right_on='Historia', how='left')

    if data_lake_selecionado != 'Todos':
        _df_obj = _df_obj[_df_obj['Data-Lake'] == data_lake_selecionado]

    _df_obj['deadline'] = pd.to_datetime(_df_obj['deadline'], errors='coerce')
    _df_obj_valid = _df_obj.dropna(subset=['deadline']).copy()

    _total_tab  = int(_df_obj_valid['tabelas'].sum())
    _total_view = int(_df_obj_valid['views'].sum())
    _total_obj  = int(_df_obj_valid['objetos'].sum())

    _plan_obj  = _df_obj_valid.groupby('deadline')['objetos'].sum().reset_index(name='obj_dia').sort_values('deadline')
    _plan_obj['obj_acum'] = _plan_obj['obj_dia'].cumsum()
    _plan_tab  = _df_obj_valid.groupby('deadline')['tabelas'].sum().reset_index(name='tab_dia').sort_values('deadline')
    _plan_tab['tab_acum'] = _plan_tab['tab_dia'].cumsum()
    _plan_view = _df_obj_valid.groupby('deadline')['views'].sum().reset_index(name='view_dia').sort_values('deadline')
    _plan_view['view_acum'] = _plan_view['view_dia'].cumsum()

    _status_done_obj = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled', 'cancelado'}
    _df_sub = df.copy()
    _df_sub['_done'] = _df_sub['Status'].astype(str).str.strip().str.lower().isin(_status_done_obj)
    _df_sub['Data Atualizacao'] = pd.to_datetime(_df_sub['Data Atualizacao'], errors='coerce', utc=True).dt.tz_convert(None).dt.normalize()

    _hist_status = (
        _df_sub.groupby('Historia')
        .agg(total_sub=('Chave', 'count'), done_sub=('_done', 'sum'), data_entrega=('Data Atualizacao', 'max'))
        .reset_index()
    )
    _hist_status['entregue'] = _hist_status['done_sub'] >= _hist_status['total_sub']
    _hist_entregues = _hist_status[_hist_status['entregue'] & _hist_status['data_entrega'].notna()]

    _real_obj = _hist_entregues.merge(_df_obj_valid[['Id', 'objetos', 'tabelas', 'views']], left_on='Historia', right_on='Id', how='inner')
    if not _real_obj.empty:
        _real_acum = (
            _real_obj.groupby('data_entrega')[['objetos', 'tabelas', 'views']]
            .sum().reset_index().sort_values('data_entrega')
        )
        _real_acum['obj_acum']  = _real_acum['objetos'].cumsum()
        _real_acum['tab_acum']  = _real_acum['tabelas'].cumsum()
        _real_acum['view_acum'] = _real_acum['views'].cumsum()
    else:
        _real_acum = pd.DataFrame()

    _prazo_obj = _plan_obj['deadline'].max() if not _plan_obj.empty else pd.NaT
    _datas_proj_obj, _vals_proj_obj = [], []
    _datas_proj_obj_m, _vals_proj_obj_m = [], []
    _datas_proj_obj_p, _vals_proj_obj_p = [], []
    if not _real_acum.empty and pd.notna(_prazo_obj):
        _realizado_obj_atual = float(_real_acum['obj_acum'].iloc[-1])
        _ultima_dt_obj = _real_acum['data_entrega'].iloc[-1]
        if _realizado_obj_atual < _total_obj:
            _x = np.arange(len(_real_acum))
            _y = _real_acum['obj_acum'].values
            _ritmo = max(float(np.polyfit(_x, _y, 1)[0]) if len(_x) > 1 else float(_y[-1]), 0.01)
            def _proj_obj(ritmo):
                ds, vs = [], []
                faltam = _total_obj - _realizado_obj_atual
                for i in range(int(np.ceil(faltam / ritmo)) + 1):
                    d = _ultima_dt_obj + pd.Timedelta(days=i)
                    v = min(_realizado_obj_atual + ritmo * i, _total_obj)
                    ds.append(d); vs.append(v)
                    if d >= _prazo_obj or v >= _total_obj:
                        break
                return ds, vs
            _datas_proj_obj,   _vals_proj_obj   = _proj_obj(_ritmo)
            _datas_proj_obj_m, _vals_proj_obj_m = _proj_obj(_ritmo * 1.3)
            _datas_proj_obj_p, _vals_proj_obj_p = _proj_obj(_ritmo * 0.7)

    fig_burnup_obj = go.Figure()
    if not _plan_obj.empty:
        fig_burnup_obj.add_trace(go.Scatter(x=_plan_obj['deadline'], y=_plan_obj['obj_acum'], mode='lines+markers', name='Planejado (Total)', line=dict(color='royalblue')))
        fig_burnup_obj.add_trace(go.Scatter(x=_plan_tab['deadline'], y=_plan_tab['tab_acum'], mode='lines', name='Planejado (Tabelas)', line=dict(color='steelblue', dash='dot', width=1.5), opacity=0.7))
        fig_burnup_obj.add_trace(go.Scatter(x=_plan_view['deadline'], y=_plan_view['view_acum'], mode='lines', name='Planejado (Views)', line=dict(color='cornflowerblue', dash='dot', width=1.5), opacity=0.7))
    if not _real_acum.empty:
        fig_burnup_obj.add_trace(go.Scatter(x=_real_acum['data_entrega'], y=_real_acum['obj_acum'], mode='lines+markers', name='Realizado (Total)', line=dict(color='orange')))
        fig_burnup_obj.add_trace(go.Scatter(x=_real_acum['data_entrega'], y=_real_acum['tab_acum'], mode='lines', name='Realizado (Tabelas)', line=dict(color='darkorange', dash='dot', width=1.5), opacity=0.7))
        fig_burnup_obj.add_trace(go.Scatter(x=_real_acum['data_entrega'], y=_real_acum['view_acum'], mode='lines', name='Realizado (Views)', line=dict(color='gold', dash='dot', width=1.5), opacity=0.7))
    if len(_datas_proj_obj_m) > 1:
        fig_burnup_obj.add_trace(go.Scatter(x=_datas_proj_obj_m, y=_vals_proj_obj_m, mode='lines', name='Projeção (Melhor)', line=dict(color='green', dash='dash', width=2), opacity=0.6))
    if len(_datas_proj_obj) > 1:
        fig_burnup_obj.add_trace(go.Scatter(x=_datas_proj_obj, y=_vals_proj_obj, mode='lines+markers', name='Projeção (Atual)', line=dict(color='red', dash='dot', width=2)))
    if len(_datas_proj_obj_p) > 1:
        fig_burnup_obj.add_trace(go.Scatter(x=_datas_proj_obj_p, y=_vals_proj_obj_p, mode='lines', name='Projeção (Pior)', line=dict(color='darkred', dash='dash', width=2), opacity=0.6))

    if pd.notna(_prazo_obj) and not _plan_obj.empty:
        _ini_obj   = _plan_obj['deadline'].min()
        _ticks_obj = pd.date_range(start=_ini_obj, end=_prazo_obj, freq='2W').tolist()
        if _ticks_obj and (_prazo_obj - _ticks_obj[-1]).days < 7:
            _ticks_obj.pop()
        _ticks_obj.append(_prazo_obj)
        _tickvals_obj = _ticks_obj
        _ticktext_obj = [t.strftime('%d/%m/%Y') for t in _ticks_obj]
        _xrange_obj   = [_ini_obj, _prazo_obj]
    else:
        _tickvals_obj = _ticktext_obj = _xrange_obj = None

    fig_burnup_obj.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>%{y:.0f}<extra></extra>")
    fig_burnup_obj.update_layout(
        xaxis_title='Data', yaxis_title='Objetos acumulados', legend_title='Legenda', height=450,
        template=plotly_template, paper_bgcolor=plotly_paper_bgcolor,
        plot_bgcolor=plotly_plot_bgcolor, font=dict(color=plotly_font_color),
        xaxis=dict(tickformat='%d/%m/%Y', range=_xrange_obj, tickvals=_tickvals_obj, ticktext=_ticktext_obj, **plotly_axis_style),
        yaxis=dict(**plotly_axis_style),
        legend=plotly_legend_style,
    )

    st.subheader('📦 Planejado Vs Realizado e Tendência — Tabelas e Views')
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Total de Objetos", _total_obj, help="Tabelas + Views")
    with col_kpi2:
        st.metric("Total de Tabelas", _total_tab)
    with col_kpi3:
        st.metric("Total de Views", _total_view)
    st.plotly_chart(fig_burnup_obj, use_container_width=True)

st.markdown(hr_style, unsafe_allow_html=True)

# ── Gantt: Linha do Tempo por Data-Lake ───────────────────────────────────────
st.subheader("📅 Linha do Tempo por Data-Lake")

_arquivo_proc = os.path.join(DADOS_DIR, "processos_seguintes.csv")
if os.path.exists(_arquivo_proc):
    _df_proc = pd.read_csv(_arquivo_proc, encoding="utf-8-sig")
    _df_proc["Start Date"] = pd.to_datetime(_df_proc["Start Date"], errors="coerce")
    _df_proc["Deadline"]   = pd.to_datetime(_df_proc["Deadline"],   errors="coerce")

    _df_proc["Lake"] = _df_proc["Titulo"].str.extract(r'\[([^\]]+)\]', expand=False).str.strip().str.upper()
    _df_proc["Fase"] = _df_proc["Titulo"].apply(lambda t: (
        "Desenvolvimento"    if "Desenvolvimento" in str(t) or "desenvolvimento" in str(t) else
        "Homologação"        if "Homologa" in str(t) else
        "Preparo Produção"   if "Preparo" in str(t) else
        "Produção Assistida" if "Produção Assistida" in str(t) or "Assis" in str(t) else
        None
    ))

    if data_lake_selecionado != 'Todos':
        _df_proc = _df_proc[_df_proc["Lake"] == data_lake_selecionado]

    _dev_hist = df_lake.copy()
    _dev_hist["data_inicio"] = pd.to_datetime(_dev_hist["data_inicio"], errors="coerce")
    _dev_hist["data_fim"]    = pd.to_datetime(_dev_hist["data_fim"],    errors="coerce")

    if data_lake_selecionado != 'Todos':
        _dev_hist = _dev_hist[_dev_hist["lake"] == data_lake_selecionado]

    _dev_por_lake = (
        _dev_hist.groupby("lake")
        .agg(start=("data_inicio", "min"), end=("data_fim", "max"))
        .reset_index()
        .rename(columns={"lake": "Lake"})
    )
    _dev_por_lake["Fase"] = "Desenvolvimento"

    _proc_fases = _df_proc[_df_proc["Fase"].isin(["Homologação", "Preparo Produção", "Produção Assistida"])].copy()
    _proc_fases = _proc_fases.rename(columns={"Start Date": "start", "Deadline": "end"})
    _proc_fases = _proc_fases[["Lake", "Fase", "start", "end"]].dropna(subset=["start", "end", "Lake"])

    _df_gantt = pd.concat([
        _dev_por_lake[["Lake", "Fase", "start", "end"]],
        _proc_fases
    ], ignore_index=True).dropna(subset=["start", "end", "Lake"])

    if data_lake_selecionado != 'Todos':
        _df_gantt = _df_gantt[_df_gantt["Lake"] == data_lake_selecionado]

    _cores_fase = {
        "Desenvolvimento":    "#1f77b4",
        "Homologação":        "#ff7f0e",
        "Preparo Produção":   "#2ca02c",
        "Produção Assistida": "#9467bd",
    }
    _ordem_fase   = ["Desenvolvimento", "Homologação", "Preparo Produção", "Produção Assistida"]
    _lake_ordem_idx = {
        "BMC": 0,
        "COMPRAS": 1,
        "MOPAR": 2,
        "CLIENTE": 3,
        "SHAREDSERVICES": 4,
        "RH": 5,
        "FINANCE": 6,
        "SUPPLYCHAIN": 7,
        "COMMERCIAL": 8,
        "COMERCIAL": 8,
    }
    _lakes_ordem = sorted(
        _df_gantt["Lake"].dropna().unique(),
        key=lambda _l: (_lake_ordem_idx.get(str(_l).strip().upper().replace(" ", ""), 999), str(_l)),
    )

    if not _df_gantt.empty:
        _fig_gantt = go.Figure()
        _data_ref  = _df_gantt["start"].min()

        _legendas_adicionadas = set()
        for _lake in _lakes_ordem:
            for _fase in _ordem_fase:
                _row = _df_gantt[(_df_gantt["Lake"] == _lake) & (_df_gantt["Fase"] == _fase)]
                if _row.empty:
                    continue
                _r   = _row.iloc[0]
                _dur = (_r["end"] - _r["start"]).days
                _off = (_r["start"] - _data_ref).days
                _cor = _cores_fase.get(_fase, "#7f7f7f")
                _show_legend = _fase not in _legendas_adicionadas
                _legendas_adicionadas.add(_fase)

                _fig_gantt.add_trace(go.Bar(
                    x=[_dur],
                    y=[_lake],
                    base=[_off],
                    orientation="h",
                    marker_color=_cor,
                    name=_fase,
                    legendgroup=_fase,
                    showlegend=_show_legend,
                    hovertemplate=(
                        f"<b>{_lake}</b><br>"
                        f"Fase: {_fase}<br>"
                        f"Início: {_r['start'].strftime('%d/%m/%Y')}<br>"
                        f"Fim: {_r['end'].strftime('%d/%m/%Y')}<br>"
                        f"Duração: {_dur} dias<extra></extra>"
                    ),
                ))

        _hoje_off = (pd.Timestamp.now().normalize() - _data_ref).days
        _fig_gantt.add_vline(
            x=_hoje_off, line_dash="dash",
            line_color="#e8edf2" if tema_selecionado != "☀️ Claro" else "#333",
            annotation_text="Hoje", annotation_position="top right",
            annotation_font_color="#e8edf2" if tema_selecionado != "☀️ Claro" else "#333",
        )

        _data_fim_gantt = _df_gantt["end"].max()
        _ticks_gantt    = pd.date_range(start=_data_ref, end=_data_fim_gantt, freq="2W")
        if _ticks_gantt.empty:
            _ticks_gantt = pd.DatetimeIndex([_data_ref])
        # Garante que a ultima data de entrega apareca explicitamente no eixo X.
        _ticks_gantt = _ticks_gantt.append(pd.DatetimeIndex([_data_fim_gantt]))
        _ticks_gantt = _ticks_gantt.drop_duplicates().sort_values()
        _tick_offs      = [int((d - _data_ref).days) for d in _ticks_gantt]
        _tick_labels    = [d.strftime("%d/%m/%Y") for d in _ticks_gantt]

        _fig_gantt.update_layout(
            barmode="overlay",
            template=plotly_template,
            paper_bgcolor=plotly_paper_bgcolor,
            plot_bgcolor=plotly_plot_bgcolor,
            font=dict(color=plotly_font_color),
            height=max(300, len(_lakes_ordem) * 80 + 100),
            margin=dict(l=20, r=20, t=30, b=60),
            xaxis=dict(
                title="Data",
                tickvals=_tick_offs,
                ticktext=_tick_labels,
                tickangle=-45,
                **plotly_axis_style,
            ),
            yaxis=dict(autorange="reversed", **plotly_axis_style),
            legend=plotly_legend_style,
        )
        st.plotly_chart(_fig_gantt, use_container_width=True)
    else:
        st.info("Nenhum dado disponível para o Gantt.")
else:
    st.info("Arquivo `processos_seguintes.csv` não encontrado. Execute o script de atualização.")


# ── Rodapé ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; font-size:12px; opacity:0.6;">
        v1.0 &nbsp;|&nbsp;
        Desenvolvido por <a href="https://www.linkedin.com/in/gersonlramos/" target="_blank"
        style="color:inherit; text-decoration:underline;">Gerson Ramos</a>
    </div>
    """,
    unsafe_allow_html=True,
)
