import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timezone, timedelta
import os
from pandas.errors import ParserError

# Obter o diretório do script e do diretório de dados
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'dados')

def calcular_curva_aprendizado(data_inicio, data_fim, total, inflexao=0.6, inclinacao=9, datas_planejado=None, valores_planejado=None):
    """
    Gera pontos de uma curva sigmoide representando a curva de aprendizado do time.
    - inflexao: fração do período onde o ritmo acelera (0.6 = 60% do período)
    Valor > 0.5 garante que a curva fica abaixo do planejado no início e
    cruza/supera após a metade, refletindo atraso inicial e aceleração posterior.
    - inclinacao: quão abrupta é a transição (k=8 gera curva suave mas perceptível)
    - datas_planejado, valores_planejado: se fornecidos, aplica a sigmoide sobre o Planejado
    
    Quando recebe o Planejado como referência, a sigmoide modula os valores planejados
    em vez de ir uniformemente de 0 a total, garantindo que a curva siga os degraus do planejado.
    """
    if pd.isna(data_inicio) or pd.isna(data_fim) or total <= 0:
        return [], []
    
    datas = pd.date_range(start=data_inicio, end=data_fim, freq='D')
    n = len(datas)
    if n < 2:
        return [data_inicio, data_fim], [0, total]
    
    # Gera curva sigmoide de 0 a 1 (normalizada)
    t_meio = inflexao
    k = inclinacao
    valores_raw = [1 / (1 + np.exp(-k * (i / (n - 1) - t_meio))) for i in range(n)]
    v_min, v_max = valores_raw[0], valores_raw[-1]
    valores_sigmoide_norm = [(v - v_min) / (v_max - v_min) for v in valores_raw]
    
    # Se houver valores planejados, aplica a sigmoide sobre eles
    if datas_planejado is not None and valores_planejado is not None and len(datas_planejado) > 0:
        # Interpola o planejado para cada dia
        df_plan = pd.DataFrame({'data': pd.to_datetime(datas_planejado), 'valor': valores_planejado})
        df_plan = df_plan.sort_values('data')
        df_datas = pd.DataFrame({'data': datas})
        df_interpolado = pd.merge_asof(df_datas, df_plan, on='data', direction='forward')
        valores_plan_interp = df_interpolado['valor'].ffill().fillna(0).tolist()
        
        # Aplica a sigmoide sobre os valores planejados interpolados
        valores_finais = [v_sig * v_plan for v_sig, v_plan in zip(valores_sigmoide_norm, valores_plan_interp)]
    else:
        # Caso padrão: aplica a sigmoide diretamente sobre o total
        valores_finais = [total * v for v in valores_sigmoide_norm]
    
    return list(datas), valores_finais

# Configuração da página
st.set_page_config(
    page_title="Dashboard Jira - Subtarefas",
    page_icon="📊",
    layout="wide"
)

# Seletor de tema na sidebar (no topo)
st.sidebar.markdown("### ⚙️ Configurações")
tema_selecionado = st.sidebar.radio("Tema:", ["🌙 Escuro", "☀️ Claro"], index=0, horizontal=True)
plotly_template = "plotly_white" if tema_selecionado == "☀️ Claro" else "plotly_dark"
plotly_font_color = "#0d1b2a" if tema_selecionado == "☀️ Claro" else "#e8edf2"
plotly_paper_bgcolor = "#f0f4f8" if tema_selecionado == "☀️ Claro" else "#0d1b2a"
plotly_plot_bgcolor = "#ffffff" if tema_selecionado == "☀️ Claro" else "#1b2a3b"
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

# Aplicar CSS customizado baseado no tema
if tema_selecionado == "☀️ Claro":
    st.markdown("""
    <style>
        /* ── TEMA CLARO: Branco limpo com acentos azul corporativo ── */
        .stApp {
            background-color: #f0f4f8 !important;
            color: #0d1b2a !important;
        }
        .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {
            color: #0d1b2a !important;
        }
        /* Sidebar com azul claro */
        [data-testid="stSidebar"] {
            background-color: #dce8f5 !important;
            border-right: 2px solid #1f77b4 !important;
        }
        [data-testid="stSidebar"] * {
            color: #0d1b2a !important;
        }
        /* Selectbox / dropdowns */
        [data-testid="stSelectbox"] > div > div,
        [data-baseweb="select"] > div,
        [data-baseweb="popover"] {
            background-color: #ffffff !important;
            color: #0d1b2a !important;
            border-color: #1f77b4 !important;
        }
        [data-baseweb="select"] span,
        [data-baseweb="select"] div {
            color: #0d1b2a !important;
            background-color: #ffffff !important;
        }
        [data-baseweb="menu"],
        [data-baseweb="menu"] ul,
        [data-baseweb="menu"] li {
            background-color: #ffffff !important;
            color: #0d1b2a !important;
        }
        [data-baseweb="menu"] li:hover {
            background-color: #dce8f5 !important;
        }
        [data-testid="stRadio"] label { color: #0d1b2a !important; }
        /* Métricas */
        .stMetric label { color: #1f77b4 !important; font-weight: 600 !important; }
        .stMetric [data-testid="stMetricValue"] { color: #0d1b2a !important; }
        /* Tabelas */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] > div > div,
        .stDataFrameResizable,
        [data-testid="stDataFrame"] [class*="wrapper"],
        [data-testid="stDataFrame"] [class*="container"] {
            background-color: #ffffff !important;
        }
        [data-testid="stCheckbox"] label { color: #0d1b2a !important; }
        /* Alertas */
        [data-testid="stAlert"] {
            background-color: #dce8f5 !important;
            color: #0d1b2a !important;
            border-left: 4px solid #1f77b4 !important;
        }
        /* Subheaders */
        [data-testid="stHeadingWithActionElements"] h2,
        [data-testid="stHeadingWithActionElements"] h3 {
            color: #0d1b2a !important;
            border-bottom: 2px solid #1f77b4;
            padding-bottom: 4px;
        }
        /* Barra superior */
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        .stAppHeader {
            background-color: #f0f4f8 !important;
        }
        header[data-testid="stHeader"] span,
        header[data-testid="stHeader"] p,
        header[data-testid="stHeader"] a {
            color: #0d1b2a !important;
        }
        /* Expander */
        [data-testid="stExpander"] {
            border: 1px solid #1f77b4 !important;
            border-radius: 6px !important;
        }
        /* Botao Atualizar dados */
        [data-testid="stSidebar"] div[data-testid="stButton"] > button,
        [data-testid="stSidebar"] button[kind="secondary"],
        [data-testid="stSidebar"] [data-baseweb="button"] {
            background-color: #1f77b4 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 6px !important;
            width: 100% !important;
            font-weight: 600 !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button p,
        [data-testid="stSidebar"] div[data-testid="stButton"] > button span,
        [data-testid="stSidebar"] [data-baseweb="button"] p,
        [data-testid="stSidebar"] [data-baseweb="button"] span {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
        [data-testid="stSidebar"] button[kind="secondary"]:hover,
        [data-testid="stSidebar"] [data-baseweb="button"]:hover {
            background-color: #155a8a !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:focus,
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:active,
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:focus-visible,
        [data-testid="stSidebar"] [data-baseweb="button"]:focus,
        [data-testid="stSidebar"] [data-baseweb="button"]:active,
        [data-testid="stSidebar"] [data-baseweb="button"]:focus-visible {
            outline: none !important;
            box-shadow: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        /* ── TEMA ESCURO: Navy/Slate corporativo ── */
        .stApp {
            background-color: #0d1b2a !important;
            color: #e8edf2 !important;
        }
        .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label {
            color: #e8edf2 !important;
        }
        /* Sidebar navy mais escuro */
        [data-testid="stSidebar"] {
            background-color: #0a1520 !important;
            border-right: 2px solid #1f77b4 !important;
        }
        [data-testid="stSidebar"] * { color: #e8edf2 !important; }
        /* Selectbox */
        [data-testid="stSelectbox"] > div > div,
        [data-baseweb="select"] > div,
        [data-baseweb="popover"] {
            background-color: #1b2a3b !important;
            color: #e8edf2 !important;
            border-color: #1f77b4 !important;
        }
        [data-baseweb="select"] span,
        [data-baseweb="select"] div {
            color: #e8edf2 !important;
            background-color: #1b2a3b !important;
        }
        [data-baseweb="menu"],
        [data-baseweb="menu"] ul,
        [data-baseweb="menu"] li {
            background-color: #1b2a3b !important;
            color: #e8edf2 !important;
        }
        [data-baseweb="menu"] li:hover { background-color: #243447 !important; }
        [data-testid="stRadio"] label { color: #e8edf2 !important; }
        /* Métricas */
        .stMetric label { color: #5ba3d9 !important; font-weight: 600 !important; }
        .stMetric [data-testid="stMetricValue"] { color: #e8edf2 !important; }
        /* Tabelas */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] > div > div,
        .stDataFrameResizable,
        [data-testid="stDataFrame"] [class*="wrapper"],
        [data-testid="stDataFrame"] [class*="container"] {
            background-color: #1b2a3b !important;
        }
        [data-testid="stCheckbox"] label { color: #e8edf2 !important; }
        /* Alertas */
        [data-testid="stAlert"] {
            background-color: #1b2a3b !important;
            color: #e8edf2 !important;
            border-left: 4px solid #1f77b4 !important;
        }
        /* Subheaders */
        [data-testid="stHeadingWithActionElements"] h2,
        [data-testid="stHeadingWithActionElements"] h3 {
            color: #e8edf2 !important;
            border-bottom: 2px solid #1f77b4;
            padding-bottom: 4px;
        }
        /* Barra superior */
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        .stAppHeader {
            background-color: #0a1520 !important;
        }
        /* Expander */
        [data-testid="stExpander"] {
            border: 1px solid #1f77b4 !important;
            border-radius: 6px !important;
        }
        /* Botao Atualizar dados */
        [data-testid="stSidebar"] div[data-testid="stButton"] > button,
        [data-testid="stSidebar"] button[kind="secondary"],
        [data-testid="stSidebar"] [data-baseweb="button"] {
            background-color: #1f77b4 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 6px !important;
            width: 100% !important;
            font-weight: 600 !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button p,
        [data-testid="stSidebar"] div[data-testid="stButton"] > button span,
        [data-testid="stSidebar"] [data-baseweb="button"] p,
        [data-testid="stSidebar"] [data-baseweb="button"] span {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
        [data-testid="stSidebar"] button[kind="secondary"]:hover,
        [data-testid="stSidebar"] [data-baseweb="button"]:hover {
            background-color: #2a9bd4 !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:focus,
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:active,
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:focus-visible,
        [data-testid="stSidebar"] [data-baseweb="button"]:focus,
        [data-testid="stSidebar"] [data-baseweb="button"]:active,
        [data-testid="stSidebar"] [data-baseweb="button"]:focus-visible {
            outline: none !important;
            box-shadow: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Título principal
st.markdown("""
<div style="text-align: center; background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: white; margin: 0;">Projeto Migração Stellantis</h1>
    <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0;">Acompanhamento de Entregas - Fase 3</p>
</div>
""", unsafe_allow_html=True)

# Data de atualização (UTC-3 = horário de Brasília)
brt_time = datetime.now(timezone(timedelta(hours=-3)))
st.markdown(f"**📅 Atualizado em:** {brt_time.strftime('%d/%m/%Y %H:%M:%S')} | **Fase:** FASE 3")

_hoje = pd.Timestamp(brt_time.date())
_status_done = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled'}

def _render_indicadores(df_base):
    """Renderiza cards de progresso reagindo ao df_base (já filtrado)."""
    _bg  = "#1b2a3b" if tema_selecionado != "☀️ Claro" else "#ffffff"
    _txt = "#e8edf2" if tema_selecionado != "☀️ Claro" else "#0d1b2a"
    _brd = "#1f3a5c" if tema_selecionado != "☀️ Claro" else "#d0dff0"
    _bg_bar = "#1e3048" if tema_selecionado != "☀️ Claro" else "#e0e8f0"

    def _barra(pct, cor):
        return f"""<div style="background:{_bg_bar}; border-radius:6px; height:10px; width:100%;
                               margin-top:4px; overflow:hidden;">
            <div style="width:{min(pct,100):.1f}%; background:{cor}; height:100%; border-radius:6px;"></div>
        </div>"""

    # Lakes presentes no df_base filtrado
    lakes_no_filtro = sorted(df_base['Data-Lake'].dropna().unique())

    # Se nenhum lake reconhecível, não renderiza
    if not lakes_no_filtro:
        return

    # Filtra datas_esperadas apenas para os lakes do filtro
    df_plan_filtrado = _df_lake_pct[_df_lake_pct['lake'].isin(lakes_no_filtro)]

    # Totais considerando o filtro
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
                padding:16px 20px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-weight:700; font-size:15px; color:{_txt};">📊 Progresso — Seleção Atual</span>
            <span style="font-size:13px; color:{_cor_delta}; font-weight:600;">
                {_sinal} {abs(_delta):.1f}% vs planejado
            </span>
        </div>
        <div style="display:flex; gap:32px;">
            <div style="flex:1;">
                <div style="font-size:12px; color:#888; margin-bottom:2px;">Planejado</div>
                <div style="font-size:22px; font-weight:700; color:#5ba3d9;">{_pct_plan:.1f}%</div>
                {_barra(_pct_plan, "#5ba3d9")}
            </div>
            <div style="flex:1;">
                <div style="font-size:12px; color:#888; margin-bottom:2px;">Realizado</div>
                <div style="font-size:22px; font-weight:700; color:{_cor_delta};">{_pct_real:.1f}%</div>
                {_barra(_pct_real, _cor_delta)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cards por lake (só quando exatamente 1 lake está selecionado no filtro) ──
    if data_lake_selecionado == 'Todos' or len(lakes_no_filtro) <= 1:
        return

    _lake_stats = []
    for _lake in lakes_no_filtro:
        _df_l  = _df_lake_pct[_df_lake_pct['lake'] == _lake]
        _tot_l = _df_l['id_historia'].nunique()
        _pl_l  = (_df_l['data_fim'] <= _hoje).sum()
        _pct_pl = (_pl_l / _tot_l * 100) if _tot_l > 0 else 0.0

        _df_s  = df_base[df_base['Data-Lake'] == _lake]
        _tot_s = len(_df_s)
        _dn_s  = _df_s['Status'].astype(str).str.strip().str.lower().isin(_status_done).sum()
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
                            padding:12px 14px; margin-bottom:10px;">
                    <div style="font-weight:700; font-size:13px; color:{_txt};
                                margin-bottom:8px; border-bottom:1px solid {_brd}; padding-bottom:5px;">
                        {stat['lake']}
                    </div>
                    <div style="font-size:11px; color:#888; margin-bottom:1px;">Planejado</div>
                    <div style="font-size:16px; font-weight:700; color:#5ba3d9;">{_pl:.1f}%</div>
                    {_barra(_pl, "#5ba3d9")}
                    <div style="font-size:11px; color:#888; margin:7px 0 1px 0;">Realizado</div>
                    <div style="font-size:16px; font-weight:700; color:{_dc};">{_rl:.1f}%</div>
                    {_barra(_rl, _dc)}
                </div>
                """, unsafe_allow_html=True)


# Função para carregar dados
@st.cache_data(ttl=900)
def carregar_dados(arquivo):
    if os.path.exists(arquivo):
        try:
            return pd.read_csv(arquivo, encoding='utf-8-sig')
        except ParserError:
            # Fallback para linhas com vírgulas sem aspas no campo "Titulo".
            with open(arquivo, 'r', encoding='utf-8-sig') as f:
                linhas = f.readlines()

            if not linhas:
                return pd.DataFrame()

            cabecalho = linhas[0].strip().split(',')
            if len(cabecalho) != 11:
                raise

            registros = []
            for idx, linha in enumerate(linhas[1:], start=2):
                linha = linha.rstrip('\n').rstrip('\r')
                if not linha:
                    continue

                partes = linha.split(',')
                if len(partes) < 11:
                    # Linha incompleta: ignora de forma segura.
                    continue

                # Estrutura esperada: 5 colunas fixas + Titulo (com vírgulas) + 5 colunas fixas finais.
                inicio = partes[:5]
                fim = partes[-5:]
                titulo = ','.join(partes[5:-5]).strip()
                if titulo.startswith('"') and titulo.endswith('"'):
                    titulo = titulo[1:-1]

                registro = inicio + [titulo] + fim
                if len(registro) == 11:
                    registros.append(registro)

            df = pd.DataFrame(registros, columns=cabecalho)
            return df
    return None

# Carregar arquivo FASE 3
arquivo_selecionado = os.path.join(DADOS_DIR, "FASE_3.csv")

df = carregar_dados(arquivo_selecionado)

if df is None:
    st.error(f"Arquivo '{arquivo_selecionado}' nao encontrado!")
    st.info("Execute primeiro o script de extracao para gerar o arquivo CSV.")
    st.stop()

# ── Indicadores de % Planejada e Realizada ──────────────────────────────────
if 'Deadline Historia' in df.columns:
    _df_lake_pct = (
        df[['Titulo Historia', 'Data-Lake', 'Deadline Historia']]
        .drop_duplicates(subset='Titulo Historia')
        .rename(columns={'Data-Lake': 'lake', 'Deadline Historia': 'data_fim', 'Titulo Historia': 'id_historia'})
        .copy()
    )
    _df_lake_pct['data_fim'] = pd.to_datetime(_df_lake_pct['data_fim'], errors='coerce')
    _df_lake_pct['lake'] = _df_lake_pct['lake'].astype(str).str.strip().str.upper()
else:
    _csv_lake_pct = os.path.join(DADOS_DIR, 'datas_esperadas_por_lake.csv')
    if os.path.exists(_csv_lake_pct):
        _df_lake_pct = pd.read_csv(_csv_lake_pct, encoding='utf-8-sig')
        _df_lake_pct['data_fim'] = pd.to_datetime(_df_lake_pct['data_fim'], dayfirst=True, errors='coerce')
        _df_lake_pct['lake'] = _df_lake_pct['lake'].astype(str).str.strip().str.upper()
    else:
        _df_lake_pct = pd.DataFrame(columns=['id_historia', 'lake', 'data_fim'])

# Botão de atualização de dados
if st.sidebar.button("🔄 Atualizar dados", help="Limpa o cache e recarrega os CSVs"):
    st.cache_data.clear()  # limpa carregar_dados + calcular_ciclo_desenvolvimento
    st.rerun()

# Filtros na sidebar
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros")

# Filtro por Data-Lake
# Normalizar para uppercase para evitar duplicatas (ex: COMPRAS vs Compras)
df['Data-Lake'] = df['Data-Lake'].astype(str).str.strip().str.upper()
data_lakes_unicos = ['Todos'] + sorted([str(d) for d in df['Data-Lake'].unique() if pd.notna(d) and str(d) not in ['N/A', 'NAN']])
data_lake_selecionado = st.sidebar.selectbox("Data-Lake:", data_lakes_unicos, index=0)

# Aplicar filtro de Data-Lake primeiro
df_filtrado = df.copy()
if data_lake_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Data-Lake'] == data_lake_selecionado]

# Filtro por História (usando título) - baseado no filtro de Data-Lake
historias_unicas = ['Todas'] + sorted([str(h) for h in df_filtrado['Titulo Historia'].unique() if pd.notna(h)])
historia_selecionada = st.sidebar.selectbox("História:", historias_unicas)

# Aplicar filtro de História
if historia_selecionada != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['Titulo Historia'] == historia_selecionada]

# Filtro por Categoria - baseado nos filtros anteriores
categorias_unicas = ['Todas'] + sorted([str(c) for c in df_filtrado['Categoria_Analise'].unique() if pd.notna(c)])
categoria_selecionada = st.sidebar.selectbox("Categoria:", categorias_unicas)

# Aplicar filtro de Categoria
if categoria_selecionada != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['Categoria_Analise'] == categoria_selecionada]

# Seleção de visualização
st.sidebar.markdown("---")
st.sidebar.markdown("**Visualize:**")
aba_selecionada = st.sidebar.radio(
    "Visualize:",
    ["📊 Executivo", "📈 Gráficos", "📋 Detalhes", "⚠️ Pendências"],
    label_visibility="collapsed"
)

# Definir status concluídos e cancelados
status_concluidos = ['Done', 'Closed', 'Resolved', 'Concluído', 'Concluida', 'Canceled', 'Cancelled', 'Cancelado']

# Calcular métricas
total_subtarefas = len(df_filtrado)
concluidas = len(df_filtrado[df_filtrado['Status'].isin(status_concluidos)])
pendentes = total_subtarefas - concluidas
percentual_concluido = (concluidas / total_subtarefas * 100) if total_subtarefas > 0 else 0
percentual_pendente = 100 - percentual_concluido

# Calcular issues abertos há mais de 1 semana (Story Bug, RN, RN-FMK)
categorias_criticas = ['Story Bug', 'RN', 'RN-FMK']
df_nao_concluidos = df_filtrado[~df_filtrado['Status'].isin(status_concluidos)]
df_criticos = df_nao_concluidos[df_nao_concluidos['Categoria_Analise'].isin(categorias_criticas)].copy()

# Converter coluna de data de criação para datetime e calcular diferença
try:
    # Método robusto de parsing de data
    def parse_data_criacao(data_str):
        if pd.isna(data_str) or data_str == '':
            return pd.NaT
        
        # Converte para string e remove espaços
        data_str = str(data_str).strip()
        
        # Tenta parsing com diferentes formatos
        formatos = [
            '%Y-%m-%dT%H:%M:%S.%f%z',  # ISO com microsegundos e timezone
            '%Y-%m-%dT%H:%M:%S%z',      # ISO sem microsegundos com timezone
            '%Y-%m-%d %H:%M:%S',        # Formato padrão sem timezone
            '%d/%m/%Y',                  # Formato BR
        ]
        
        for fmt in formatos:
            try:
                # Remove o timezone manualmente se existir (substitui por Z para UTC)
                if '+' in data_str or data_str.count('-') > 2:
                    # Remove timezone (tudo após o último ':' seguido de dígitos)
                    if 'T' in data_str:
                        data_str_sem_tz = data_str[:data_str.rfind('+' if '+' in data_str else '-')] if ('+' in data_str or data_str.rfind('-') > 10) else data_str
                        return pd.to_datetime(data_str_sem_tz)
                return pd.to_datetime(data_str, format=fmt)
            except (ValueError, TypeError):
                continue
        
        # Se nenhum formato funcionou, tenta o parsing automático do pandas
        return pd.to_datetime(data_str, errors='coerce')
    
    # Aplica o parsing robusto
    df_criticos['Data Criacao'] = df_criticos['Data Criacao'].apply(parse_data_criacao)
    
    # Remove linhas com datas inválidas
    df_criticos = df_criticos[df_criticos['Data Criacao'].notna()].copy()
    
    # Calcula dias em aberto
    data_atual = pd.Timestamp.now()
    df_criticos['Dias_Aberto'] = (data_atual - df_criticos['Data Criacao']).dt.days
    
    # Filtra issues com mais de 7 dias abertos
    issues_abertos_1_semana = len(df_criticos[df_criticos['Dias_Aberto'] > 7])
except Exception as e:
    issues_abertos_1_semana = 0
    df_criticos = pd.DataFrame()  # DataFrame vazio em caso de erro

# =====================
# Gráfico de Burn-out semanal (Planejado vs Real)
# =====================
# Monta df_lake a partir do FASE_3.csv — uma linha por história com datas do Jira
# (colunas Start Date Historia / Deadline Historia disponíveis após rodar script atualizado)
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
    # id_historia = apenas o trecho entre colchetes, para dar match com normalizar_id_historia
    df_lake['id_historia'] = df_lake['titulo'].str.extract(r'(\[[^\]]+\])', expand=False)
else:
    # Fallback: lê o CSV legado enquanto o script não for executado
    _csv_lake = os.path.join(DADOS_DIR, 'datas_esperadas_por_lake.csv')
    if os.path.exists(_csv_lake):
        df_lake = pd.read_csv(_csv_lake, encoding='utf-8-sig')
        df_lake['lake'] = df_lake['lake'].astype(str).str.strip().str.upper()
        df_lake['lake'] = df_lake['lake'].str.replace(r'\s+[A-Z]$', '', regex=True)
    else:
        df_lake = pd.DataFrame(columns=['id_historia', 'titulo', 'lake', 'data_inicio', 'data_fim'])

df_lake['lake'] = df_lake['lake'].astype(str).str.strip().str.upper()

def calcular_dias_uteis(data_inicio, data_fim):
    """
    Calcula quantidade de dias úteis entre duas datas (exclui sábados e domingos).
    """
    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0
    
    # Converte para datetime64
    d1 = pd.Timestamp(data_inicio).date()
    d2 = pd.Timestamp(data_fim).date()
    
    # Se data_fim < data_inicio, retorna 0
    if d2 < d1:
        return 0
    
    # busday_count conta dias úteis (seg-sex)
    return np.busday_count(d1, d2)

@st.cache_data(ttl=900)
def calcular_ciclo_desenvolvimento(data_lake_filtro='Todos'):
    """
    Calcula o ciclo de desenvolvimento médio das histórias baseado nos arquivos de histórico.
    Considera os status: IN DEVELOPMENT, WAITING CODE REVIEW, IN CODE REVIEW, WAITING TEST, TEST
    Retorna: (ciclo_medio_dias_uteis, num_historias) ou (None, None) se não houver dados
    """
    import glob
    
    status_desenvolvimento = {
        'IN DEVELOPMENT',
        'WAITING CODE REVIEW',
        'IN CODE REVIEW',
        'WAITING TEST',
        'TEST'
    }
    
    # Mapear nome do lake para nome do arquivo
    lake_to_file = {
        'BMC': 'BMC',
        'CLIENTE': 'CLIENTE',
        'COMERCIAL': 'COMERCIAL',
        'COMPRAS': 'COMPRAS',
        'FINANCE': 'FINANCE',
        'MOPAR': 'MOPAR',
        'RH': 'RH',
        'SHARED SERVICES': 'SHAREDSERVICES',
        'SUPPLY CHAIN': 'SUPPLYCHAIN'
    }
    
    # Determinar quais arquivos carregar
    if data_lake_filtro == 'Todos':
        arquivos = glob.glob(os.path.join(DADOS_DIR, 'historico', 'historico_completo-*.csv'))
    else:
        arquivo_key = lake_to_file.get(data_lake_filtro)
        if arquivo_key:
            arquivo_path = os.path.join(DADOS_DIR, 'historico', f'historico_completo-{arquivo_key}.csv')
            if os.path.exists(arquivo_path):
                arquivos = [arquivo_path]
            else:
                return None, None
        else:
            return None, None
    
    if not arquivos:
        return None, None
    
    # Carregar todos os históricos
    df_hist_list = []
    for arquivo in arquivos:
        try:
            df_temp = pd.read_csv(arquivo, encoding='utf-8-sig')
            if not df_temp.empty:
                df_hist_list.append(df_temp)
        except Exception as e:
            continue
    
    if not df_hist_list:
        return None, None
    
    df_historico = pd.concat(df_hist_list, ignore_index=True)
    
    if df_historico.empty:
        return None, None
    
    # Converter datas com timezone
    df_historico['Data Mudanca'] = pd.to_datetime(df_historico['Data Mudanca'], errors='coerce')
    df_historico = df_historico.dropna(subset=['Data Mudanca'])
    
    if df_historico.empty:
        return None, None
    
    # Normalizar status para uppercase para garantir match
    df_historico['Status Antigo'] = df_historico['Status Antigo'].astype(str).str.strip().str.upper()
    df_historico['Status Novo'] = df_historico['Status Novo'].astype(str).str.strip().str.upper()
    
    # Normalizar status_desenvolvimento para uppercase também
    status_desenvolvimento = {s.upper() for s in status_desenvolvimento}
    
    # Agrupar por história (Chave)
    historias_tempo = {}
    data_atual = pd.Timestamp.now(tz='UTC')
    
    for chave in df_historico['Chave'].unique():
        df_hist_chave = df_historico[df_historico['Chave'] == chave].sort_values('Data Mudanca').reset_index(drop=True)
        
        periodos_desenvolvimento = []  # Lista de (data_entrada, data_saida)
        data_entrada = None
        
        # Processa cada mudança de status
        for i, row in df_hist_chave.iterrows():
            status_novo = row['Status Novo']
            data_mudanca = row['Data Mudanca']
            
            # Se o timezone não está definido, assume UTC
            if data_mudanca.tz is None:
                data_mudanca = data_mudanca.tz_localize('UTC')
            else:
                data_mudanca = data_mudanca.tz_convert('UTC')
            
            # Histórico da mudança
            if status_novo in status_desenvolvimento:
                # Entrou em status de desenvolvimento
                if data_entrada is None:
                    data_entrada = data_mudanca
            else:
                # Saiu de status de desenvolvimento
                if data_entrada is not None:
                    periodos_desenvolvimento.append((data_entrada, data_mudanca))
                    data_entrada = None
        
        # Se ainda está em desenvolvimento, conta até agora
        if data_entrada is not None:
            periodos_desenvolvimento.append((data_entrada, data_atual))
        
        # Calcula dias úteis totais
        dias_uteis_total = 0
        for entrada, saida in periodos_desenvolvimento:
            dias_uteis_total += calcular_dias_uteis(entrada, saida)
        
        if dias_uteis_total > 0:
            historias_tempo[chave] = dias_uteis_total
    
    if not historias_tempo:
        return None, None
    
    # Calcular média
    ciclo_medio = sum(historias_tempo.values()) / len(historias_tempo)
    num_historias = len(historias_tempo)
    
    return ciclo_medio, num_historias

def calcular_ciclo_ideal(data_lake_filtro='Todos'):
    """
    Calcula o ciclo ideal médio baseado nas datas planejadas (Start Date / Deadline)
    extraídas do Jira via FASE_3.csv.
    Retorna: (ciclo_ideal_dias_uteis, num_historias) ou (None, None) se não houver dados
    """
    df_ideal = df_lake.copy()

    if data_lake_filtro != 'Todos':
        df_ideal = df_ideal[df_ideal['lake'] == data_lake_filtro]

    if df_ideal.empty:
        return None, None

    df_ideal['data_inicio'] = pd.to_datetime(df_ideal['data_inicio'], errors='coerce')
    df_ideal['data_fim']    = pd.to_datetime(df_ideal['data_fim'],    errors='coerce')
    df_ideal = df_ideal.dropna(subset=['data_inicio', 'data_fim'])

    if df_ideal.empty:
        return None, None

    ciclos_planejados = []
    for _, row in df_ideal.iterrows():
        dias_uteis = calcular_dias_uteis(row['data_inicio'], row['data_fim'])
        if dias_uteis > 0:
            ciclos_planejados.append(dias_uteis)

    if not ciclos_planejados:
        return None, None

    return sum(ciclos_planejados) / len(ciclos_planejados), len(ciclos_planejados)

def normalizar_id_historia(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip().upper()
    texto = texto.replace('[', '').replace(']', '')
    texto = ' '.join(texto.split())
    texto = texto.replace(' - ', '-')
    texto = texto.replace(' -', '-')
    texto = texto.replace('- ', '-')
    return texto


# Planejado: sempre baseado no datas_esperadas_por_lake.csv (data_fim por história)
if data_lake_selecionado == 'Todos':
    lakes_fase = df_lake.copy()
else:
    lakes_fase = df_lake[df_lake['lake'] == data_lake_selecionado].copy()

lakes_fase['data_fim']    = pd.to_datetime(lakes_fase['data_fim'],    dayfirst=not _tem_datas_jira, errors='coerce')
lakes_fase['data_inicio'] = pd.to_datetime(lakes_fase['data_inicio'], dayfirst=not _tem_datas_jira, errors='coerce')
lakes_fase['id_historia_norm'] = lakes_fase['id_historia'].apply(normalizar_id_historia)

# Planejado agrupado por DIA (data_fim exata)
burn_planejado = (
    lakes_fase.dropna(subset=['data_fim'])
    .groupby('data_fim')
    .size()
    .reset_index(name='planejado')
)
burn_planejado.rename(columns={'data_fim': 'data'}, inplace=True)
burn_planejado['data'] = pd.to_datetime(burn_planejado['data'])

# Adiciona ponto inicial zerado na data de início do planejamento
_data_inicio_plan = lakes_fase['data_inicio'].min() if 'data_inicio' in lakes_fase.columns and not lakes_fase['data_inicio'].isna().all() else None
if _data_inicio_plan is not None and pd.notna(_data_inicio_plan):
    burn_planejado = pd.concat(
        [pd.DataFrame([{'data': _data_inicio_plan, 'planejado': 0}]), burn_planejado],
        ignore_index=True
    ).sort_values('data')

# Real: história concluída quando todas as subtarefas estiverem concluídas
df_real_base = df.copy()
if data_lake_selecionado != 'Todos':
    df_real_base = df_real_base[df_real_base['Data-Lake'] == data_lake_selecionado]

df_real_base['id_historia_raw'] = df_real_base['Titulo Historia'].str.extract(r'\[([^\]]+)\]', expand=False)
df_real_base['id_historia_norm'] = df_real_base['id_historia_raw'].apply(normalizar_id_historia)
ids_planejados = set(lakes_fase['id_historia_norm'].dropna().unique())
df_real_base = df_real_base[df_real_base['id_historia_norm'].isin(ids_planejados)].copy()

status_entregue = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled'}
df_real_base['status_norm'] = df_real_base['Status'].astype(str).str.strip().str.lower()
df_real_base['entregue_subtarefa'] = df_real_base['status_norm'].isin(status_entregue)
df_real_base['data_atualizacao_dt'] = pd.to_datetime(df_real_base['Data Atualizacao'], errors='coerce', utc=True)

# Realizado parcial: cada subtarefa concluída contribui com uma fração da história
totais_por_historia = (
    df_real_base.groupby('id_historia_norm')
    .size()
    .reset_index(name='total_subtarefas_historia')
)

subtarefas_concluidas = df_real_base[
    df_real_base['entregue_subtarefa'] & df_real_base['data_atualizacao_dt'].notna()
].copy()

if not subtarefas_concluidas.empty:
    subtarefas_concluidas = subtarefas_concluidas.merge(
        totais_por_historia,
        on='id_historia_norm',
        how='left'
    )
    subtarefas_concluidas['peso_historia'] = 1 / subtarefas_concluidas['total_subtarefas_historia']
    subtarefas_concluidas['data'] = subtarefas_concluidas['data_atualizacao_dt'].dt.tz_convert(None).dt.normalize()
    burn_real_parcial = (
        subtarefas_concluidas.groupby('data')['peso_historia']
        .sum()
        .reset_index(name='realizado_parcial')
    )
else:
    burn_real_parcial = pd.DataFrame({'data': pd.Series(dtype='datetime64[ns]'), 'realizado_parcial': pd.Series(dtype='float64')})

hist_entregues = (
    df_real_base.groupby('id_historia_norm')
    .agg(
        historia_entregue=('entregue_subtarefa', 'all'),
        data_entrega_real=('data_atualizacao_dt', 'max')
    )
    .reset_index()
)
hist_entregues = hist_entregues[
    hist_entregues['historia_entregue'] & hist_entregues['data_entrega_real'].notna()
].copy()

if not hist_entregues.empty:
    hist_entregues['data'] = hist_entregues['data_entrega_real'].dt.tz_convert(None).dt.normalize()
    burn_real = hist_entregues.groupby('data').size().reset_index(name='realizado')
else:
    burn_real = pd.DataFrame({'data': pd.Series(dtype='datetime64[ns]'), 'realizado': pd.Series(dtype='int64')})

# Junta planejado e realizado (histórias 100% concluídas)
burn = pd.merge(burn_planejado, burn_real, on='data', how='outer').fillna(0)
burn = burn.sort_values('data')
burn['planejado_acum'] = burn['planejado'].cumsum()
burn['realizado_acum'] = burn['realizado'].cumsum()

# Série de realizado acumulado (apenas datas com entregas reais)
if not burn_real.empty:
    burn_real_acum = burn_real.sort_values('data').copy()
    burn_real_acum['realizado_acum'] = burn_real_acum['realizado'].cumsum()
    ultima_data_real_bh = burn_real_acum['data'].max()
    burn_real_mask = burn['data'] <= ultima_data_real_bh
else:
    burn_real_acum = pd.DataFrame()
    ultima_data_real_bh = pd.NaT
    burn_real_mask = pd.Series(False, index=burn.index)

datas_proj = []
valores_proj = []
datas_proj_melhor = []
valores_proj_melhor = []
datas_proj_pior = []
valores_proj_pior = []
ritmo_hist_dia = 0.0
realizado_atual = 0.0

total_planejado = float(burn['planejado'].sum()) if not burn.empty else 0.0
prazo_final_planejado = lakes_fase['data_fim'].max() if 'data_fim' in lakes_fase.columns and not lakes_fase.empty else pd.NaT

if not burn_real_acum.empty and pd.notna(ultima_data_real_bh) and pd.notna(prazo_final_planejado):
    realizado_atual = float(burn_real_acum['realizado_acum'].iloc[-1])

    if realizado_atual > 0 and realizado_atual < total_planejado:
        x = np.arange(len(burn_real_acum))
        y = burn_real_acum['realizado_acum'].values
        ritmo_hist_dia = float(np.polyfit(x, y, 1)[0]) if len(x) > 1 else float(y[-1])
        ritmo_hist_dia = max(ritmo_hist_dia, 0.01)

        historias_faltantes = total_planejado - realizado_atual

        def gerar_projecao(ritmo, prazo_limite):
            datas, valores = [], []
            dias_necessarios = int(np.ceil(historias_faltantes / ritmo))
            for i in range(dias_necessarios + 1):
                data_proj = ultima_data_real_bh + pd.Timedelta(days=i)
                if pd.notna(prazo_limite) and data_proj > prazo_limite:
                    break
                valor_proj = realizado_atual + ritmo * i
                datas.append(data_proj)
                valores.append(min(valor_proj, total_planejado))
                if valor_proj >= total_planejado:
                    break
            return datas, valores

        datas_proj, valores_proj = gerar_projecao(ritmo_hist_dia, prazo_final_planejado)
        datas_proj_melhor, valores_proj_melhor = gerar_projecao(ritmo_hist_dia * 1.3, prazo_final_planejado)
        datas_proj_pior, valores_proj_pior = gerar_projecao(ritmo_hist_dia * 0.7, prazo_final_planejado)

# ── BURN-UP POR PONTOS ────────────────────────────────────────────────────────
# (cálculos permanecem fora das abas)

# Mapa de pontos por tamanho
_pontos_tamanho = {'P': 3, 'M': 5, 'G': 8}

# Extrai tamanho e pontos por história única (1 linha por Titulo Historia)
df_historias_unicas = df_filtrado.drop_duplicates(subset='Titulo Historia').copy()
df_historias_unicas['_tamanho'] = df_historias_unicas['Titulo Historia'].str.extract(
    r'TAMANHO:\s*([PGM])', expand=False
)
df_historias_unicas['_pontos'] = df_historias_unicas['_tamanho'].map(_pontos_tamanho).fillna(0)
total_pontos = df_historias_unicas['_pontos'].sum()

# Linha de planejado: acumula pontos por sexta-feira usando data_fim de cada história
prazo_burnup = lakes_fase['data_fim'].max() if 'data_fim' in lakes_fase.columns and not lakes_fase.empty else pd.NaT
# Início fixo: primeira sexta a partir de 13/03/2026
data_inicio_burnup = pd.Timestamp('2026-03-13')

if pd.notna(prazo_burnup) and total_pontos > 0 and 'data_fim' in lakes_fase.columns:
    # Usa apenas histórias que existem no FASE_3.csv (histórias únicas já extraídas)
    # Cruza lakes_fase com as histórias do FASE_3 pela id normalizada
    _ids_fase3 = set(df_real_base['id_historia_norm'].dropna().unique())
    lakes_fase_filtrado = lakes_fase[lakes_fase['id_historia_norm'].isin(_ids_fase3)].copy()

    lakes_fase_filtrado['_pontos_plan'] = lakes_fase_filtrado['titulo'].str.extract(
        r'TAMANHO:\s*([PGM])', expand=False
    ).map({'P': 3, 'M': 5, 'G': 8}).fillna(0)

    # Agrupa pontos por data_fim exata e acumula
    plan_por_data = (
        lakes_fase_filtrado.groupby('data_fim')['_pontos_plan']
        .sum()
        .reset_index()
        .sort_values('data_fim')
    )
    plan_por_data['pontos_acum'] = plan_por_data['_pontos_plan'].cumsum()

    # Adiciona ponto inicial zerado em 13/03
    _inicio = pd.DataFrame([{'data_fim': data_inicio_burnup, 'pontos_acum': 0}])
    plan_por_data = pd.concat([_inicio, plan_por_data], ignore_index=True).sort_values('data_fim')

    datas_plan_bp = list(plan_por_data['data_fim'])
    valores_plan_bp = list(plan_por_data['pontos_acum'])
else:
    datas_plan_bp = []
    valores_plan_bp = []

# Realizado: história entregue quando TODAS as subtarefas são Done ou Canceled
status_entregue_bp = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled'}
df_bp = df_filtrado.copy()
df_bp['status_norm_bp'] = df_bp['Status'].astype(str).str.strip().str.lower()
df_bp['entregue_bp'] = df_bp['status_norm_bp'].isin(status_entregue_bp)
df_bp['data_atu_bp'] = pd.to_datetime(df_bp['Data Atualizacao'], errors='coerce', utc=True)

# Pontos por história (extraídos do título)
_mapa_pontos_hist = (
    df_historias_unicas[['Titulo Historia', '_pontos']]
    .set_index('Titulo Historia')['_pontos']
    .to_dict()
)
df_bp['_pontos_hist'] = df_bp['Titulo Historia'].map(_mapa_pontos_hist).fillna(0)

# Agrupa por história: entregue = todas subtarefas concluídas
hist_bp = (
    df_bp.groupby('Titulo Historia')
    .agg(
        historia_entregue=('entregue_bp', 'all'),
        data_entrega_bp=('data_atu_bp', 'max'),
        pontos=('_pontos_hist', 'first')
    )
    .reset_index()
)
hist_bp_entregues = hist_bp[
    hist_bp['historia_entregue'] & hist_bp['data_entrega_bp'].notna()
].copy()

if not hist_bp_entregues.empty:
    hist_bp_entregues['data'] = hist_bp_entregues['data_entrega_bp'].dt.tz_convert(None).dt.normalize()
    burn_bp_real = (
        hist_bp_entregues.groupby('data')['pontos']
        .sum()
        .reset_index(name='pontos_dia')
        .sort_values('data')
    )
    burn_bp_real['pontos_acum'] = burn_bp_real['pontos_dia'].cumsum()
    ultima_data_bp = burn_bp_real['data'].max()
    pontos_entregues = float(burn_bp_real['pontos_acum'].iloc[-1])
else:
    burn_bp_real = pd.DataFrame({
        'data': pd.Series(dtype='datetime64[ns]'),
        'pontos_dia': pd.Series(dtype='float64'),
        'pontos_acum': pd.Series(dtype='float64')
    })
    ultima_data_bp = pd.NaT
    pontos_entregues = 0.0

# Projeção a partir do ritmo real (regressão linear semanal)
datas_proj_bp = []
valores_proj_bp = []
datas_proj_bp_melhor = []
valores_proj_bp_melhor = []
datas_proj_bp_pior = []
valores_proj_bp_pior = []

if not burn_bp_real.empty and pontos_entregues > 0 and pd.notna(prazo_burnup) and pontos_entregues < total_pontos:
    x_bp = np.arange(len(burn_bp_real))
    y_bp = burn_bp_real['pontos_acum'].values
    ritmo_bp = float(np.polyfit(x_bp, y_bp, 1)[0]) if len(x_bp) > 1 else float(y_bp[-1])
    ritmo_bp = max(ritmo_bp, 0.01)

    def _proj_bp(ritmo, prazo):
        datas, valores = [], []
        faltam = total_pontos - pontos_entregues
        dias = int(np.ceil(faltam / ritmo))
        for i in range(dias + 1):
            d = ultima_data_bp + pd.Timedelta(days=i)
            if pd.notna(prazo) and d >= prazo:
                datas.append(prazo)
                valores.append(min(pontos_entregues + ritmo * i, total_pontos))
                break
            v = pontos_entregues + ritmo * i
            datas.append(d)
            valores.append(min(v, total_pontos))
            if v >= total_pontos:
                break
        return datas, valores

    datas_proj_bp, valores_proj_bp = _proj_bp(ritmo_bp, prazo_burnup)
    datas_proj_bp_melhor, valores_proj_bp_melhor = _proj_bp(ritmo_bp * 1.3, prazo_burnup)
    datas_proj_bp_pior, valores_proj_bp_pior = _proj_bp(ritmo_bp * 0.7, prazo_burnup)

fig_burnup = go.Figure()

if len(datas_plan_bp) > 0:
    fig_burnup.add_trace(go.Scatter(
        x=list(datas_plan_bp), y=valores_plan_bp,
        mode='lines+markers', name='Planejado',
        line=dict(color='royalblue')
    ))

if not burn_bp_real.empty:
    fig_burnup.add_trace(go.Scatter(
        x=burn_bp_real['data'], y=burn_bp_real['pontos_acum'],
        mode='lines+markers', name='Realizado',
        line=dict(color='orange')
    ))

_datas_sig_bp, _valores_sig_bp = calcular_curva_aprendizado(
    data_inicio_burnup, prazo_burnup, total_pontos,
    datas_planejado=datas_plan_bp, valores_planejado=valores_plan_bp
)
if len(_datas_sig_bp) > 1:
    fig_burnup.add_trace(go.Scatter(
        x=_datas_sig_bp, y=_valores_sig_bp,
        mode='lines', name='Entrega Esperada',
        line=dict(color='mediumpurple', dash='dash', width=2),
        opacity=0.8
    ))

if len(datas_proj_bp_melhor) > 1:
    fig_burnup.add_trace(go.Scatter(
        x=datas_proj_bp_melhor, y=valores_proj_bp_melhor,
        mode='lines', name='Projeção (Melhor)',
        line=dict(color='green', dash='dash', width=2), opacity=0.6
    ))
if len(datas_proj_bp) > 1:
    fig_burnup.add_trace(go.Scatter(
        x=datas_proj_bp, y=valores_proj_bp,
        mode='lines+markers', name='Projeção (Atual)',
        line=dict(color='red', dash='dot', width=2)
    ))
if len(datas_proj_bp_pior) > 1:
    fig_burnup.add_trace(go.Scatter(
        x=datas_proj_bp_pior, y=valores_proj_bp_pior,
        mode='lines', name='Projeção (Pior)',
        line=dict(color='darkred', dash='dash', width=2), opacity=0.6
    ))

xaxis_range_bp = [data_inicio_burnup, prazo_burnup] if pd.notna(prazo_burnup) else None

if pd.notna(prazo_burnup):
    _ticks_bp = pd.date_range(start=data_inicio_burnup, end=prazo_burnup, freq='2W').tolist()
    if _ticks_bp and (prazo_burnup - _ticks_bp[-1]).days < 7:
        _ticks_bp.pop()
    _ticks_bp.append(prazo_burnup)
    _tickvals_bp = _ticks_bp
    _ticktext_bp = [t.strftime('%d/%m/%Y') for t in _ticks_bp]
else:
    _tickvals_bp = None
    _ticktext_bp = None

fig_burnup.update_layout(
    xaxis_title='Data',
    yaxis_title='Pontos acumulados',
    legend_title='Legenda',
    height=450,
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    plot_bgcolor=plotly_plot_bgcolor,
    font=dict(color=plotly_font_color),
    xaxis=dict(tickformat='%d/%m/%Y', range=xaxis_range_bp, tickvals=_tickvals_bp, ticktext=_ticktext_bp, **plotly_axis_style),
    yaxis=dict(**plotly_axis_style),
    legend=plotly_legend_style
)
# ── RENDERIZAÇÃO ORGANIZADA POR ABAS ─────────────────────────────────────────

# Cálculos de suporte para aba_exec (burnup por histórias)
_data_ini_burnout = lakes_fase['data_inicio'].min() if 'data_inicio' in lakes_fase.columns and not lakes_fase['data_inicio'].isna().all() else (burn['data'].min() if not burn.empty else pd.NaT)
# Extrair datas e valores do planejado acumulado para a curva de aprendizado
_datas_plan_hist = list(burn['data']) if not burn.empty else []
_valores_plan_hist = list(burn['planejado_acum']) if not burn.empty else []
_datas_sig, _valores_sig = calcular_curva_aprendizado(
    _data_ini_burnout, prazo_final_planejado, total_planejado,
    datas_planejado=_datas_plan_hist, valores_planejado=_valores_plan_hist
)

total_historias = int(total_planejado)
historias_concluidas = int(realizado_atual) if realizado_atual > 0 else 0
percentual_concluido_hist = (historias_concluidas / total_historias * 100) if total_historias > 0 else 0

if ritmo_hist_dia > 0 and realizado_atual > 0 and realizado_atual < total_planejado:
    historias_faltantes = total_planejado - realizado_atual
    dias_faltantes = int(np.ceil(historias_faltantes / ritmo_hist_dia))
    previsao_conclusao = ultima_data_real_bh + pd.Timedelta(days=dias_faltantes)
    previsao_melhor = ultima_data_real_bh + pd.Timedelta(days=int(np.ceil(historias_faltantes / (ritmo_hist_dia * 1.3))))
    previsao_pior   = ultima_data_real_bh + pd.Timedelta(days=int(np.ceil(historias_faltantes / (ritmo_hist_dia * 0.7))))
elif historias_concluidas >= total_historias and total_historias > 0:
    previsao_conclusao = burn_real_acum.loc[burn_real_acum['realizado_acum'] >= total_historias, 'data'].min() if not burn_real_acum.empty else pd.NaT
    previsao_melhor = previsao_conclusao
    previsao_pior   = previsao_conclusao
else:
    previsao_conclusao = pd.NaT
    previsao_melhor = pd.NaT
    previsao_pior   = pd.NaT

in_progress = len(df_filtrado[df_filtrado['Status'].str.lower() == 'in progress'])

# Funções de renderização de tabelas (definidas fora das abas)
def colorir_status(val):
    cores_status = {
        'Done': 'background-color: #90EE90; color: black',
        'Closed': 'background-color: #90EE90; color: black',
        'Resolved': 'background-color: #90EE90; color: black',
        'Concluído': 'background-color: #90EE90; color: black',
        'Concluida': 'background-color: #90EE90; color: black',
        'In Progress': 'background-color: #87CEEB; color: black',
        'To Do': 'background-color: #FFE4B5; color: black',
        'Backlog': 'background-color: #D3D3D3; color: black',
        'Canceled': 'background-color: #FFD700; color: black',
        'Cancelled': 'background-color: #FFD700; color: black',
        'Cancelado': 'background-color: #FFD700; color: black'
    }
    return cores_status.get(val, '')

def renderizar_tabela(df_render, tema):
    if tema == "☀️ Claro":
        cores_status_html = {
            'Done': '#90EE90', 'Closed': '#90EE90', 'Resolved': '#90EE90',
            'Concluído': '#90EE90', 'Concluida': '#90EE90',
            'In Progress': '#87CEEB', 'To Do': '#FFE4B5', 'Backlog': '#D3D3D3',
            'Canceled': '#FFD700', 'Cancelled': '#FFD700', 'Cancelado': '#FFD700'
        }
        html = '<div style="overflow-x:auto; overflow-y:auto; max-height:300px;">'
        html += '<table style="width:100%; border-collapse:collapse; font-size:13px; background:#fff; color:#1f1f1f;">'
        html += '<thead><tr style="background:#e8e8e8; position:sticky; top:0;">'
        for col in df_render.columns:
            html += f'<th style="padding:6px 8px; text-align:left; border-bottom:1px solid #ccc; white-space:nowrap; color:#1f1f1f;">{col}</th>'
        html += '</tr></thead><tbody>'
        for idx_r, (_, row) in enumerate(df_render.iterrows()):
            bg_row = '#ffffff' if idx_r % 2 == 0 else '#f9f9f9'
            html += f'<tr style="background:{bg_row};">'
            for col in df_render.columns:
                val = str(row[col]) if pd.notna(row[col]) else ''
                if col == 'Status':
                    cor = cores_status_html.get(val, 'transparent')
                    html += f'<td style="padding:5px 8px; border-bottom:1px solid #eee; background:{cor}; color:#1f1f1f; white-space:nowrap;">{val}</td>'
                else:
                    html += f'<td style="padding:5px 8px; border-bottom:1px solid #eee; color:#1f1f1f;">{val}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.dataframe(
            df_render.style.map(colorir_status, subset=['Status']),
            use_container_width=True,
            height=300
        )

# Cálculo fig_burn (fora das abas, pois é usado na aba_graficos)
fig_burn = go.Figure()
fig_burn.add_trace(go.Scatter(
    x=burn['data'],
    y=burn['planejado_acum'],
    mode='lines+markers',
    name='Planejado',
    line=dict(color='royalblue')
))
if not burn_real_acum.empty:
    fig_burn.add_trace(go.Scatter(
        x=burn_real_acum['data'],
        y=burn_real_acum['realizado_acum'],
        mode='lines+markers',
        name='Realizado',
        line=dict(color='orange')
    ))

if len(_datas_sig) > 1:
    fig_burn.add_trace(go.Scatter(
        x=_datas_sig, y=_valores_sig,
        mode='lines', name='Entrega Esperada',
        line=dict(color='mediumpurple', dash='dash', width=2),
        opacity=0.8
    ))

if len(datas_proj_melhor) > 1:
    fig_burn.add_trace(go.Scatter(
        x=datas_proj_melhor,
        y=valores_proj_melhor,
        mode='lines',
        name='Projeção (Melhor)',
        line=dict(color='green', dash='dash', width=2),
        opacity=0.6
    ))

if len(datas_proj) > 1:
    fig_burn.add_trace(go.Scatter(
        x=datas_proj,
        y=valores_proj,
        mode='lines+markers',
        name='Projeção (Atual)',
        line=dict(color='red', dash='dot', width=2)
    ))

if len(datas_proj_pior) > 1:
    fig_burn.add_trace(go.Scatter(
        x=datas_proj_pior,
        y=valores_proj_pior,
        mode='lines',
        name='Projeção (Pior)',
        line=dict(color='darkred', dash='dash', width=2),
        opacity=0.6
    ))

if pd.notna(prazo_final_planejado):
    data_inicio_grafico = lakes_fase['data_inicio'].min() if 'data_inicio' in lakes_fase.columns and not lakes_fase['data_inicio'].isna().all() else (burn['data'].min() if not burn.empty else prazo_final_planejado)
    xaxis_range = [data_inicio_grafico, prazo_final_planejado]
    _ticks_bh = pd.date_range(start=data_inicio_grafico, end=prazo_final_planejado, freq='2W').tolist()
    # Remove o último tick automático se estiver a menos de 7 dias da data final
    if _ticks_bh and (prazo_final_planejado - _ticks_bh[-1]).days < 7:
        _ticks_bh.pop()
    _ticks_bh.append(prazo_final_planejado)
    _tickvals_bh = _ticks_bh
    _ticktext_bh = [t.strftime('%d/%m/%Y') for t in _ticks_bh]
else:
    xaxis_range = None
    _tickvals_bh = None
    _ticktext_bh = None

fig_burn.update_layout(
    xaxis_title='Data',
    yaxis_title='Historias acumuladas',
    legend_title='Legenda',
    height=450,
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    plot_bgcolor=plotly_plot_bgcolor,
    font=dict(color=plotly_font_color),
    xaxis=dict(tickformat='%d/%m/%Y', range=xaxis_range, tickvals=_tickvals_bh, ticktext=_ticktext_bh, **plotly_axis_style),
    yaxis=dict(**plotly_axis_style),
    legend=plotly_legend_style
)

# Cálculos de gráficos de distribuição (fora das abas)
status_counts = df_filtrado['Status'].value_counts().reset_index()
status_counts.columns = ['Status', 'Quantidade']

fig_status = px.pie(
    status_counts,
    values='Quantidade',
    names='Status',
    hole=0.4,
    color_discrete_sequence=px.colors.sequential.Blues_r
)
fig_status.update_layout(
    height=300,
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    font=dict(color=plotly_font_color),
    legend=plotly_legend_style
)

fig_progress = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=percentual_concluido,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': "% Concluído", 'font': {'size': 24}},
    delta={'reference': 100, 'increasing': {'color': "green"}},
    gauge={
        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
        'bar': {'color': "darkblue"},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
        'steps': [
            {'range': [0, 50], 'color': '#ffcccc'},
            {'range': [50, 75], 'color': '#ffffcc'},
            {'range': [75, 100], 'color': '#ccffcc'}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 90
        }
    }
))
fig_progress.update_layout(
    height=300,
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    font=dict(color=plotly_font_color)
)

categoria_counts = df_filtrado['Categoria_Analise'].value_counts().reset_index()
categoria_counts.columns = ['Categoria', 'Quantidade']

fig_categoria = px.bar(
    categoria_counts,
    x='Categoria',
    y='Quantidade',
    color='Quantidade',
    color_continuous_scale='Blues'
)
fig_categoria.update_layout(
    height=300,
    showlegend=False,
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    plot_bgcolor=plotly_plot_bgcolor,
    font=dict(color=plotly_font_color),
    xaxis=dict(**plotly_axis_style),
    yaxis=dict(**plotly_axis_style),
    coloraxis_colorbar=dict(tickfont=dict(color=plotly_font_color), title=dict(font=dict(color=plotly_font_color)))
)

data_lake_counts = df_filtrado['Data-Lake'].value_counts().reset_index()
data_lake_counts.columns = ['Data-Lake', 'Quantidade']

fig_data_lake = px.bar(
    data_lake_counts,
    x='Data-Lake',
    y='Quantidade',
    color='Quantidade',
    color_continuous_scale='Teal'
)
fig_data_lake.update_layout(
    height=300,
    showlegend=False,
    template=plotly_template,
    paper_bgcolor=plotly_paper_bgcolor,
    plot_bgcolor=plotly_plot_bgcolor,
    font=dict(color=plotly_font_color),
    xaxis=dict(**plotly_axis_style),
    yaxis=dict(**plotly_axis_style),
    coloraxis_colorbar=dict(tickfont=dict(color=plotly_font_color), title=dict(font=dict(color=plotly_font_color)))
)

# Cálculos para críticos (fora das abas)
if issues_abertos_1_semana > 0 and not df_criticos.empty:
    df_criticos_exibir = df_criticos[df_criticos['Dias_Aberto'] > 7].copy()
    df_criticos_exibir = df_criticos_exibir.sort_values('Dias_Aberto', ascending=False)
    categoria_critica_counts = df_criticos_exibir['Categoria_Analise'].value_counts().reset_index()
    categoria_critica_counts.columns = ['Categoria', 'Quantidade']
    fig_critico = px.bar(
        categoria_critica_counts,
        x='Categoria',
        y='Quantidade',
        color='Quantidade',
        color_continuous_scale='Reds',
        text='Quantidade'
    )
    fig_critico.update_layout(
        height=250,
        showlegend=False,
        template=plotly_template,
        paper_bgcolor=plotly_paper_bgcolor,
        plot_bgcolor=plotly_plot_bgcolor,
        font=dict(color=plotly_font_color),
        xaxis=dict(**plotly_axis_style),
        yaxis=dict(**plotly_axis_style)
    )
    fig_critico.update_traces(textposition='outside')
else:
    df_criticos_exibir = pd.DataFrame()
    fig_critico = None

story_bugs = len(df_filtrado[df_filtrado['Categoria_Analise'] == 'Story Bug'])
rn_total = len(df_filtrado[df_filtrado['Categoria_Analise'].str.contains('RN', na=False)])

# ── VISÃO EXECUTIVA ───────────────────────────────────────────────────────────
if aba_selecionada == "📊 Executivo":
    _render_indicadores(df_filtrado)
    st.markdown(hr_style, unsafe_allow_html=True)
    # KPIs do burnup por storypoint
    col_bp1, col_bp2, col_bp3, col_bp4 = st.columns(4)
    with col_bp1:
        st.metric("Total de Story-Points", int(total_pontos))
    with col_bp2:
        st.metric("Story-Points Entregues", int(pontos_entregues), delta=f"{(pontos_entregues/total_pontos*100):.1f}%" if total_pontos > 0 else None)
    with col_bp3:
        st.metric("Data entrega desenvolvimento", prazo_burnup.strftime('%d/%m/%Y') if pd.notna(prazo_burnup) else 'N/A')
    with col_bp4:
        if datas_proj_bp_melhor and datas_proj_bp_pior:
            _prev_melhor = datas_proj_bp_melhor[-1].strftime('%d/%m')
            _prev_pior = datas_proj_bp_pior[-1].strftime('%d/%m/%y')
            st.metric("Previsão (Melhor/Pior)", f"{_prev_melhor} a {_prev_pior}")
        else:
            st.metric("Previsão (Melhor/Pior)", 'N/A')

    # KPIs do burnup por histórias
    col_burn1, col_burn2, col_burn3, col_burn4 = st.columns(4)
    with col_burn1:
        st.metric(label="Total de Histórias", value=total_historias)
    with col_burn2:
        st.metric(label="Histórias Concluídas", value=historias_concluidas, delta=f"{percentual_concluido_hist:.1f}%")
    with col_burn3:
        prazo_planejado_txt = prazo_final_planejado.strftime('%d/%m/%Y') if pd.notna(prazo_final_planejado) else 'N/A'
        st.metric(label="Data entrega desenvolvimento", value=prazo_planejado_txt)
    with col_burn4:
        if pd.notna(previsao_melhor) and pd.notna(previsao_pior):
            previsao_melhor_txt = previsao_melhor.strftime('%d/%m')
            previsao_pior_txt = previsao_pior.strftime('%d/%m/%y')
            previsao_txt = f"{previsao_melhor_txt} a {previsao_pior_txt}"
        else:
            previsao_txt = 'N/A'
        if pd.notna(previsao_conclusao) and pd.notna(prazo_final_planejado):
            delta_dias = (previsao_conclusao - prazo_final_planejado).days
            delta_txt = f"{delta_dias:+d} dias"
            delta_color = "normal" if delta_dias >= 0 else "inverse"
        else:
            delta_txt = None
            delta_color = "off"
        st.metric(label="Previsão (Melhor/Pior)", value=previsao_txt, delta=delta_txt, delta_color=delta_color)

    st.markdown(hr_style, unsafe_allow_html=True)

    # Indicadores Principais Subtarefas
    st.subheader("Indicadores Principais Subtarefas")
    col1, col1b, col2, col3, col4, col5 = st.columns(6)
    with col1:
        st.metric(
            label="Total Subtarefas",
            value=total_subtarefas
        )
    with col1b:
        st.metric(
            label="In Progress",
            value=in_progress
        )
    with col2:
        st.metric(
            label="Concluidas",
            value=concluidas,
            delta=f"{percentual_concluido:.1f}%"
        )
    with col3:
        st.metric(
            label="Pendentes",
            value=pendentes,
            delta=f"-{percentual_pendente:.1f}%",
            delta_color="red"
        )
    with col4:
        st.metric(
            label="% Falta",
            value=f"{percentual_pendente:.1f}%"
        )
    with col5:
        st.metric(
            label="Criticos >1 Sem",
            value=issues_abertos_1_semana,
            delta="Bug/RN",
            delta_color="off"
        )

    st.markdown(hr_style, unsafe_allow_html=True)

    # Adicionais
    st.subheader("Adicionais")
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric(
            label="Story Bugs",
            value=story_bugs
        )
    with col_stat2:
        st.metric(
            label="Regras de Negocio",
            value=rn_total
        )

    st.markdown(hr_style, unsafe_allow_html=True)

    # Ciclo de Desenvolvimento de Histórias
    st.subheader("📊 Ciclo de Desenvolvimento de Histórias")
    
    ciclo_medio, num_historias = calcular_ciclo_desenvolvimento(data_lake_selecionado)
    ciclo_ideal, num_historias_ideal = calcular_ciclo_ideal(data_lake_selecionado)
    
    # Calcular total de histórias (planejadas) no projeto filtrado
    if data_lake_selecionado != 'Todos':
        df_lake_filtrado = df[df['Data-Lake'] == data_lake_selecionado]
    else:
        df_lake_filtrado = df
    total_historias_planejadas = df_lake_filtrado['Titulo Historia'].nunique()
    
    if ciclo_medio is not None and num_historias is not None:
        col_ciclo1, col_ciclo2, col_ciclo3, col_ciclo4, col_ciclo5 = st.columns([1, 1, 1, 1, 2])
        with col_ciclo1:
            st.metric(
                label="Ciclo Real (dias úteis)",
                value=f"{ciclo_medio:.1f}",
                help="Tempo médio (em dias úteis) que as histórias passam nos status de desenvolvimento"
            )
        with col_ciclo2:
            st.metric(
                label="Ciclo Real (semanas)",
                value=f"{ciclo_medio/5:.1f}",
                help="Tempo médio em semanas úteis (5 dias/semana)"
            )
        with col_ciclo3:
            if ciclo_ideal is not None:
                st.metric(
                    label="Ciclo Ideal (dias úteis)",
                    value=f"{ciclo_ideal:.1f}",
                    help="Tempo planejado médio entre data_inicio e data_fim das histórias"
                )
            else:
                st.metric(
                    label="Ciclo Ideal (dias úteis)",
                    value="N/A",
                    help="Não foi possível calcular o ciclo ideal"
                )
        with col_ciclo4:
            if ciclo_ideal is not None:
                variacao = ((ciclo_medio - ciclo_ideal) / ciclo_ideal * 100) if ciclo_ideal > 0 else 0
                st.metric(
                    label="Variação Real vs Ideal",
                    value=f"{variacao:+.1f}%",
                    delta=f"{ciclo_medio - ciclo_ideal:+.1f} dias",
                    delta_color="normal" if variacao >= 0 else "inverse",
                    help="Diferença percentual entre ciclo real e ideal"
                )
            else:
                st.metric(
                    label="Variação Real vs Ideal",
                    value="N/A"
                )
        with col_ciclo5:
            st.info("⏱️ **Real**: IN DEVELOPMENT, WAITING CODE REVIEW, IN CODE REVIEW, WAITING TEST, TEST\n\n📅 **Ideal**: data_inicio → data_fim (planejado)")
        
        # Segunda linha com histórias analisadas
        col_hist1, col_hist2, col_hist3 = st.columns([1, 1, 2])
        with col_hist1:
            st.metric(
                label="Histórias Analisadas (Real)",
                value=num_historias,
                help="Histórias que passaram por desenvolvimento"
            )
        with col_hist2:
            st.metric(
                label="Histórias Planejadas (Ideal)",
                value=total_historias_planejadas,
                help="Total de histórias únicas no projeto"
            )
        
        with st.expander("ℹ️ Como são calculados os Ciclos?"):
            st.markdown("""
**Ciclo Real de Desenvolvimento**
Mede o tempo que cada história passa nos seguintes status (apenas dias úteis - seg a sex):
- `IN DEVELOPMENT`
- `WAITING CODE REVIEW`
- `IN CODE REVIEW`
- `WAITING TEST`
- `TEST`

**Cálculo do Ciclo Real**
1. Para cada história, soma-se o tempo total (dias úteis) em qualquer um dos status acima
2. Se a história ainda está em um desses status, conta-se até a data atual
3. A média é calculada sobre todas as histórias que passaram por pelo menos um desses status
4. **Apenas dias úteis são contados** (exclui sábados e domingos)

**Ciclo Ideal (Planejado)**
Baseado nas datas planejadas do arquivo `datas_esperadas_por_lake.csv`:
- Calcula dias úteis entre `data_inicio` e `data_fim` de cada história
- Média de todas as histórias planejadas
- Representa o tempo ideal/esperado para completar uma história

**Variação Real vs Ideal**
- Percentual de diferença entre o ciclo real e o ideal
- **Positivo**: Ciclo real está maior que o planejado (atraso)
- **Negativo**: Ciclo real está menor que o planejado (adiantado)

**Fonte de Dados**
- **Ciclo Real**: Arquivos de histórico em `app/historico/` (mudanças de status do Jira)
- **Ciclo Ideal**: Arquivo `datas_esperadas_por_lake.csv`

**Exemplo**
- História X em desenvolvimento de 01/03 (seg) a 10/03 (qua) = 8 dias úteis
- História Y planejada de 05/03 (sex) a 15/03 (seg) = 9 dias úteis
- Se Real = 8.0 e Ideal = 9.0, Variação = -11.1% (11% mais rápido que o planejado)
""")
    else:
        st.info("ℹ️ **Ainda não há histórias abertas com ciclo de desenvolvimento registrado para este Data-Lake.**\n\nO ciclo será calculado quando as histórias passarem pelos status de desenvolvimento (IN DEVELOPMENT, WAITING CODE REVIEW, IN CODE REVIEW, WAITING TEST, TEST).")

    st.markdown(hr_style, unsafe_allow_html=True)

    # ── Gantt: Linha do Tempo por Lake ────────────────────────────────────────
    st.subheader("📅 Linha do Tempo por Data-Lake")

    _arquivo_proc = os.path.join(DADOS_DIR, "processos_seguintes.csv")
    if os.path.exists(_arquivo_proc):
        _df_proc = pd.read_csv(_arquivo_proc, encoding="utf-8-sig")
        _df_proc["Start Date"] = pd.to_datetime(_df_proc["Start Date"], errors="coerce")
        _df_proc["Deadline"]   = pd.to_datetime(_df_proc["Deadline"],   errors="coerce")

        # Extrai lake e fase do título
        _df_proc["Lake"] = _df_proc["Titulo"].str.extract(r'\[([^\]]+)\]', expand=False).str.strip().str.upper()
        _df_proc["Fase"] = _df_proc["Titulo"].apply(lambda t: (
            "Desenvolvimento"    if "Desenvolvimento" in str(t) or "desenvolvimento" in str(t) else
            "Homologação"        if "Homologa" in str(t) else
            "Preparo Produção"   if "Preparo" in str(t) else
            "Produção Assistida" if "Produção Assistida" in str(t) or "Assis" in str(t) else
            None
        ))

        # Filtra pelo lake selecionado no filtro principal
        _lakes_gantt = _df_proc["Lake"].dropna().unique()
        if data_lake_selecionado != 'Todos':
            _df_proc = _df_proc[_df_proc["Lake"] == data_lake_selecionado]

        # Desenvolvimento: start = menor Start Date das histórias do lake, end = maior Deadline das histórias
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

        # Monta linhas dos processos seguintes (sem Desenvolvimento)
        _proc_fases = _df_proc[_df_proc["Fase"].isin(["Homologação", "Preparo Produção", "Produção Assistida"])].copy()
        _proc_fases = _proc_fases.rename(columns={"Start Date": "start", "Deadline": "end"})
        _proc_fases = _proc_fases[["Lake", "Fase", "start", "end"]].dropna(subset=["start", "end", "Lake"])

        # Une desenvolvimento + processos seguintes
        _df_gantt = pd.concat([
            _dev_por_lake[["Lake", "Fase", "start", "end"]],
            _proc_fases
        ], ignore_index=True).dropna(subset=["start", "end", "Lake"])

        # Filtra lake selecionado
        if data_lake_selecionado != 'Todos':
            _df_gantt = _df_gantt[_df_gantt["Lake"] == data_lake_selecionado]

        _cores_fase = {
            "Desenvolvimento":    "#1f77b4",
            "Homologação":        "#ff7f0e",
            "Preparo Produção":   "#2ca02c",
            "Produção Assistida": "#9467bd",
        }
        _ordem_fase = ["Desenvolvimento", "Homologação", "Preparo Produção", "Produção Assistida"]
        _lakes_ordem = sorted(_df_gantt["Lake"].unique())

        if not _df_gantt.empty:
            _fig_gantt = go.Figure()
            _data_ref = _df_gantt["start"].min()

            _legendas_adicionadas = set()
            for _lake in _lakes_ordem:
                for _fase in _ordem_fase:
                    _row = _df_gantt[(_df_gantt["Lake"] == _lake) & (_df_gantt["Fase"] == _fase)]
                    if _row.empty:
                        continue
                    _r = _row.iloc[0]
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

            # Linha de hoje
            _hoje_off = (pd.Timestamp.now().normalize() - _data_ref).days
            _fig_gantt.add_vline(
                x=_hoje_off, line_dash="dash", line_color="#e8edf2" if tema_selecionado != "☀️ Claro" else "#333",
                annotation_text="Hoje", annotation_position="top right",
                annotation_font_color="#e8edf2" if tema_selecionado != "☀️ Claro" else "#333",
            )

            # Eixo X em datas reais
            _data_fim_gantt = _df_gantt["end"].max()
            _ticks_gantt = pd.date_range(start=_data_ref, end=_data_fim_gantt, freq="2W")
            _tick_offs   = [int((d - _data_ref).days) for d in _ticks_gantt]
            _tick_labels = [d.strftime("%d/%m/%Y") for d in _ticks_gantt]

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

# ── GRÁFICOS ──────────────────────────────────────────────────────────────────
elif aba_selecionada == "📈 Gráficos":
    _render_indicadores(df_filtrado)
    st.markdown(hr_style, unsafe_allow_html=True)
    # Burnup por Storypoint
    st.subheader('Burnup por Storypoint (Planejado x Real)')
    st.plotly_chart(fig_burnup, use_container_width=True)
    with st.expander("ℹ️ Como são calculadas as linhas deste gráfico?"):
        st.markdown("""
**Planejado**
Acumulado de pontos por `data_fim` de cada história no arquivo de datas esperadas.
Pontuação: P = 3 pts · M = 5 pts · G = 8 pts (extraído do título da história).
Cada história é contada apenas uma vez (sem duplicar por subtarefa).

**Realizado**
Uma história é considerada entregue somente quando **todas** as suas subtarefas estão com status `Done` ou `Canceled`.
Os pontos são creditados na data da última atualização da história.

**Entrega Esperada** *(curva roxa tracejada)*
Curva sigmoide que simula a curva de aprendizado do time:
```
f(t) = total_pontos / (1 + e^(-k × (t − t_meio)))   normalizada para [0, total_pontos]
```
- `t` = posição no período (0 = início, 1 = fim)
- `t_meio = 0.60` → o time atinge ritmo pleno em ~60% do período (fica abaixo do planejado no início e recupera na segunda metade)
- `k = 8` → transição moderadamente abrupta

**Projeção (Melhor / Atual / Pior)**
Regressão linear sobre os pontos acumulados entregues. A partir do último ponto entregue:
- **Melhor:** ritmo histórico × 1.3 (30% mais rápido)
- **Atual:** ritmo histórico (coeficiente angular da regressão linear)
- **Pior:** ritmo histórico × 0.7 (30% mais lento)

Todas as projeções são limitadas à data final planejada.
""")

    # Burnup por Histórias
    st.subheader('Burnup por Histórias (Planejado x Real)')
    st.plotly_chart(fig_burn, use_container_width=True)
    with st.expander("ℹ️ Como são calculadas as linhas deste gráfico?"):
        st.markdown("""
**Planejado**
Soma cumulativa de histórias por `data_fim` prevista no arquivo de datas esperadas por lake.

**Realizado**
Cada subtarefa concluída (`Done`, `Canceled`, etc.) contribui com uma fração da sua história (1 / total de subtarefas da história). A linha representa o progresso parcial acumulado dia a dia.

**Entrega Esperada** *(curva roxa tracejada)*
Curva sigmoide que simula a curva de aprendizado do time:
```
f(t) = total / (1 + e^(-k × (t − t_meio)))   normalizada para [0, total]
```
- `t` = posição no período (0 = início, 1 = fim)
- `t_meio = 0.60` → o time atinge ritmo pleno em ~60% do período (fica abaixo do planejado no início e recupera na segunda metade)
- `k = 8` → transição moderadamente abrupta

**Projeção (Melhor / Atual / Pior)**
Regressão linear sobre o realizado parcial acumulado. A partir do último ponto entregue:
- **Melhor:** ritmo histórico × 1.3 (30% mais rápido)
- **Atual:** ritmo histórico (coeficiente angular da regressão)
- **Pior:** ritmo histórico × 0.7 (30% mais lento)

Todas as projeções são limitadas à data final planejada.
""")

    # Distribuição por Status e Progresso de Conclusão
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.subheader("Distribuicao por Status")
        st.plotly_chart(fig_status, use_container_width=True)
    with col_graf2:
        st.subheader("Progresso de Conclusao")
        st.plotly_chart(fig_progress, use_container_width=True)

    # Distribuição por Categoria e Subtarefas por Data-Lake
    col_graf3, col_graf4 = st.columns(2)
    with col_graf3:
        st.subheader("Distribuicao por Categoria")
        st.plotly_chart(fig_categoria, use_container_width=True)
    with col_graf4:
        st.subheader("Subtarefas por Data-Lake")
        st.plotly_chart(fig_data_lake, use_container_width=True)

# ── DETALHES ──────────────────────────────────────────────────────────────────
elif aba_selecionada == "📋 Detalhes":
    # Críticos Abertos > 1 Semana
    st.subheader("Criticos Abertos > 1 Semana")
    if issues_abertos_1_semana > 0 and not df_criticos.empty:
        st.info(f"Encontrados {issues_abertos_1_semana} issues criticos (Story Bug, RN e RN-FMK) abertos ha mais de 7 dias")
        col_crit1, col_crit2 = st.columns([1, 2])
        with col_crit1:
            st.write("**Distribuicao por Categoria**")
            st.plotly_chart(fig_critico, use_container_width=True)
        with col_crit2:
            st.write("**Detalhes dos Issues**")
            colunas_criticos = ['Chave', 'Titulo Historia', 'Data-Lake', 'Titulo', 'Status', 'Categoria_Analise', 'Dias_Aberto']
            if tema_selecionado == "☀️ Claro":
                df_crit_show = df_criticos_exibir[colunas_criticos]
                html = '<div style="overflow-x:auto; overflow-y:auto; max-height:250px;">'
                html += '<table style="width:100%; border-collapse:collapse; font-size:13px; background:#fff; color:#1f1f1f;">'
                html += '<thead><tr style="background:#e8e8e8; position:sticky; top:0;">'
                for col in df_crit_show.columns:
                    html += f'<th style="padding:6px 8px; text-align:left; border-bottom:1px solid #ccc; white-space:nowrap; color:#1f1f1f;">{col}</th>'
                html += '</tr></thead><tbody>'
                for idx_c, (_, row) in enumerate(df_crit_show.iterrows()):
                    bg_row = '#ffffff' if idx_c % 2 == 0 else '#f9f9f9'
                    html += f'<tr style="background:{bg_row};">'
                    for col in df_crit_show.columns:
                        val = str(row[col]) if pd.notna(row[col]) else ''
                        html += f'<td style="padding:5px 8px; border-bottom:1px solid #eee; color:#1f1f1f; white-space:nowrap;">{val}</td>'
                    html += '</tr>'
                html += '</tbody></table></div>'
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.dataframe(
                    df_criticos_exibir[colunas_criticos],
                    use_container_width=True,
                    height=250
                )
    else:
        st.success("Nenhum issue critico aberto ha mais de 1 semana!")

    st.markdown(hr_style, unsafe_allow_html=True)

    # Tabela de detalhes
    st.subheader("Detalhes")
    exibir_todas = st.checkbox("Exibir todas as colunas", value=False)
    if exibir_todas:
        colunas_todas = [c for c in ['Data-Lake', 'Historia'] if c in df_filtrado.columns] +                         [c for c in df_filtrado.columns if c not in ['Data-Lake', 'Historia']]
        renderizar_tabela(df_filtrado[colunas_todas].sort_index(ascending=False), tema_selecionado)
    else:
        colunas_resumo_base = ['Data-Lake', 'Historia', 'Titulo Historia', 'Chave', 'Titulo', 'Status', 'Categoria_Analise']
        colunas_resumo = [c for c in colunas_resumo_base if c in df_filtrado.columns]
        renderizar_tabela(df_filtrado[colunas_resumo].sort_index(ascending=False), tema_selecionado)


# ── PENDÊNCIAS ────────────────────────────────────────────────────────────────
elif aba_selecionada == "⚠️ Pendências":
    arquivo_pendencias  = os.path.join(DADOS_DIR, "pendencias_BF3E4-293.csv")
    arquivo_hist_pend   = os.path.join(DADOS_DIR, "historico_BF3E4-293.csv")

    if not os.path.exists(arquivo_pendencias):
        st.warning("Arquivo de pendências não encontrado. Execute o script `script_pendencias.py` primeiro.")
        st.stop()

    df_pend = pd.read_csv(arquivo_pendencias, encoding="utf-8-sig")
    df_hist_pend = pd.read_csv(arquivo_hist_pend, encoding="utf-8-sig") if os.path.exists(arquivo_hist_pend) else pd.DataFrame()

    # ── Normalizar status ──────────────────────────────────────────────────
    df_pend["Status"] = df_pend["Status"].astype(str).str.strip()
    status_done_pend      = {"Done", "Closed", "Resolved"}
    status_canceled_pend  = {"Canceled", "Cancelled", "Cancelado"}

    total_pend    = len(df_pend)
    qtd_done      = df_pend["Status"].isin(status_done_pend).sum()
    qtd_canceled  = df_pend["Status"].isin(status_canceled_pend).sum()
    qtd_aberta    = total_pend - qtd_done - qtd_canceled
    pct_resolucao = ((qtd_done + qtd_canceled) / total_pend * 100) if total_pend > 0 else 0

    st.subheader("⚠️ Pendências")
    st.markdown(hr_style, unsafe_allow_html=True)

    # ── Métricas principais ────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de Pendências",  total_pend)
    c2.metric("Em Aberto",            int(qtd_aberta))
    c3.metric("Concluídas (Done)",    int(qtd_done))
    c4.metric("Canceladas",           int(qtd_canceled))
    c5.metric("% Resolução",          f"{pct_resolucao:.1f}%")

    st.markdown(hr_style, unsafe_allow_html=True)

    # ── Ciclo de tempo: Start Date → Done ─────────────────────────────────
    st.subheader("⏱️ Ciclo de Tempo (Start Date → Done)")

    df_ciclo = df_pend.copy()
    df_ciclo["Start Date"] = pd.to_datetime(df_ciclo["Start Date"], errors="coerce")

    # Busca data de conclusão no histórico
    if not df_hist_pend.empty:
        df_hist_pend["Data Mudanca"] = pd.to_datetime(df_hist_pend["Data Mudanca"], errors="coerce")
        datas_done = (
            df_hist_pend[df_hist_pend["Status Novo"].isin(status_done_pend)]
            .sort_values("Data Mudanca")
            .groupby("Chave")["Data Mudanca"]
            .last()
            .reset_index()
            .rename(columns={"Data Mudanca": "Data Done"})
        )
        df_ciclo = df_ciclo.merge(datas_done, on="Chave", how="left")
    else:
        df_ciclo["Data Done"] = pd.NaT

    # Normaliza ambas as colunas para tz-naive (remove timezone se houver)
    df_ciclo["Start Date"] = pd.to_datetime(df_ciclo["Start Date"], errors="coerce").dt.tz_localize(None)
    df_ciclo["Data Done"]  = pd.to_datetime(df_ciclo["Data Done"],  errors="coerce").dt.tz_localize(None)

    df_ciclo["Ciclo (dias)"] = (df_ciclo["Data Done"] - df_ciclo["Start Date"]).dt.days
    df_ciclo_valido = df_ciclo[df_ciclo["Ciclo (dias)"].notna() & (df_ciclo["Ciclo (dias)"] >= 0)]

    if not df_ciclo_valido.empty:
        ciclo_medio = df_ciclo_valido["Ciclo (dias)"].mean()
        ciclo_max   = df_ciclo_valido["Ciclo (dias)"].max()
        ciclo_min   = df_ciclo_valido["Ciclo (dias)"].min()

        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Ciclo Médio (dias)", f"{ciclo_medio:.1f}")
        cc2.metric("Maior Ciclo (dias)", f"{ciclo_max:.0f}")
        cc3.metric("Menor Ciclo (dias)", f"{ciclo_min:.0f}")

        fig_ciclo = px.bar(
            df_ciclo_valido.sort_values("Ciclo (dias)", ascending=False),
            x="Chave", y="Ciclo (dias)", text="Ciclo (dias)",
            title="Ciclo de Tempo por Pendência (dias corridos)",
            color="Ciclo (dias)",
            color_continuous_scale="Blues",
            template=plotly_template,
        )
        fig_ciclo.update_traces(textposition="outside")
        fig_ciclo.update_layout(
            paper_bgcolor=plotly_paper_bgcolor,
            plot_bgcolor=plotly_plot_bgcolor,
            font=dict(color=plotly_font_color),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_ciclo, use_container_width=True)
    else:
        st.info("Nenhuma pendência com Start Date e data de conclusão disponíveis para calcular ciclo.")

    st.markdown(hr_style, unsafe_allow_html=True)

    # ── Gráficos ───────────────────────────────────────────────────────────
    st.subheader("📊 Distribuição das Pendências")
    gc1, gc2 = st.columns(2)

    # Donut: distribuição por status
    contagem_status = df_pend["Status"].value_counts().reset_index()
    contagem_status.columns = ["Status", "Quantidade"]
    fig_donut = px.pie(
        contagem_status, names="Status", values="Quantidade",
        hole=0.5,
        title="Distribuição por Status",
        template=plotly_template,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_donut.update_layout(
        paper_bgcolor=plotly_paper_bgcolor,
        font=dict(color=plotly_font_color),
        legend=plotly_legend_style,
    )
    gc1.plotly_chart(fig_donut, use_container_width=True)

    # Barras: distribuição por prioridade
    contagem_prior = df_pend["Prioridade"].fillna("Não definida").value_counts().reset_index()
    contagem_prior.columns = ["Prioridade", "Quantidade"]
    cores_prior = {"Highest": "#d62728", "High": "#ff7f0e", "Medium": "#1f77b4",
                   "Low": "#2ca02c", "Lowest": "#9467bd", "Não definida": "#7f7f7f"}
    fig_prior = px.bar(
        contagem_prior, x="Prioridade", y="Quantidade", text="Quantidade",
        title="Distribuição por Prioridade",
        color="Prioridade",
        color_discrete_map=cores_prior,
        template=plotly_template,
    )
    fig_prior.update_traces(textposition="outside")
    fig_prior.update_layout(
        paper_bgcolor=plotly_paper_bgcolor,
        plot_bgcolor=plotly_plot_bgcolor,
        font=dict(color=plotly_font_color),
        showlegend=False,
    )
    gc2.plotly_chart(fig_prior, use_container_width=True)

    # Barras: tasks abertas por dia
    st.subheader("📅 Tasks Abertas por Dia")

    # Conta tasks por Start Date (quantas foram abertas em cada dia)
    df_abertura = df_pend[["Chave", "Start Date"]].copy()
    df_abertura["Start Date"] = pd.to_datetime(df_abertura["Start Date"], errors="coerce").dt.tz_localize(None)
    df_abertura = df_abertura.dropna(subset=["Start Date"])
    df_abertura["Data"] = df_abertura["Start Date"].dt.strftime("%d/%m/%Y")

    df_abertos_por_dia = (
        df_abertura.groupby("Data")["Chave"]
        .nunique()
        .reset_index(name="Tasks Abertas")
    )

    fig_abertas = px.bar(
        df_abertos_por_dia, x="Data", y="Tasks Abertas", text="Tasks Abertas",
        title="Quantidade de Tasks em Aberto por Dia",
        template=plotly_template,
        color_discrete_sequence=["#1f77b4"],
    )
    fig_abertas.update_traces(textposition="outside")
    fig_abertas.update_layout(
        paper_bgcolor=plotly_paper_bgcolor,
        plot_bgcolor=plotly_plot_bgcolor,
        font=dict(color=plotly_font_color),
        xaxis=dict(**plotly_axis_style, tickangle=-45),
        yaxis=plotly_axis_style,
        showlegend=False,
    )
    st.plotly_chart(fig_abertas, use_container_width=True)

    st.markdown(hr_style, unsafe_allow_html=True)

    # ── Alerta: pendências abertas há mais de 5 dias ───────────────────────
    st.subheader("🚨 Alertas — Pendências Abertas há mais de 5 dias")

    df_pend["Start Date"] = pd.to_datetime(df_pend["Start Date"], errors="coerce").dt.tz_localize(None)
    hoje_pend = pd.Timestamp.now().normalize()

    # Sobrescreve o status com o mais recente do histórico (fonte mais atualizada)
    if not df_hist_pend.empty:
        df_hist_pend["Data Mudanca"] = pd.to_datetime(df_hist_pend["Data Mudanca"], errors="coerce")
        status_recente = (
            df_hist_pend.sort_values("Data Mudanca")
            .groupby("Chave")["Status Novo"]
            .last()
            .reset_index()
            .rename(columns={"Status Novo": "Status Historico"})
        )
        df_pend = df_pend.merge(status_recente, on="Chave", how="left")
        df_pend["Status"] = df_pend["Status Historico"].combine_first(df_pend["Status"])
        df_pend.drop(columns=["Status Historico"], inplace=True)

    mask_aberta = ~df_pend["Status"].isin(status_done_pend | status_canceled_pend)
    df_alerta = df_pend[mask_aberta].copy()
    df_alerta["Dias Aberto"] = (hoje_pend - df_alerta["Start Date"]).dt.days
    df_alerta = df_alerta[df_alerta["Dias Aberto"] > 5].sort_values("Dias Aberto", ascending=False)

    if df_alerta.empty:
        st.success("Nenhuma pendência em aberto há mais de 5 dias.")
    else:
        st.error(f"⚠️ {len(df_alerta)} pendência(s) em aberto há mais de 5 dias!")

        for _, row in df_alerta.iterrows():
            dias = int(row["Dias Aberto"]) if pd.notna(row["Dias Aberto"]) else "?"
            prior = row.get("Prioridade", "-") or "-"
            desc  = row.get("Descricao", "") or ""
            desc_curta = desc[:300] + "..." if len(str(desc)) > 300 else desc

            cor_borda = "#d62728" if dias > 15 else "#ff7f0e"
            bg_card   = "#2a1a1a" if tema_selecionado != "☀️ Claro" else "#fff5f5"
            txt_color = "#e8edf2" if tema_selecionado != "☀️ Claro" else "#0d1b2a"

            st.markdown(f"""
            <div style="border-left: 5px solid {cor_borda}; background:{bg_card}; padding:14px 18px;
                        border-radius:6px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; font-size:15px; color:{cor_borda};">{row['Chave']} — {row['Titulo']}</span>
                    <span style="background:{cor_borda}; color:#fff; padding:2px 10px;
                                 border-radius:12px; font-size:12px; font-weight:600;">
                        {dias} dias em aberto
                    </span>
                </div>
                <div style="font-size:12px; color:#888; margin-bottom:8px;">
                    Status: <b>{row['Status']}</b> &nbsp;|&nbsp; Prioridade: <b>{prior}</b>
                </div>
                <div style="font-size:13px; color:{txt_color}; white-space:pre-wrap; opacity:0.85;">
                    {desc_curta if desc_curta else '<i>Sem descrição.</i>'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(hr_style, unsafe_allow_html=True)

    # ── SLA de Escalonamento de Dependências ───────────────────────────────
    st.subheader("🚦 SLA de Escalonamento de Dependências")

    # Configuração dos níveis SLA
    # Pré-impedimento: baseado em dias úteis até o Deadline
    # Impedimento: baseado em dias corridos desde a Start Date (task ainda aberta)

    def dias_uteis_restantes(deadline):
        """Conta dias úteis entre hoje e o deadline."""
        if pd.isna(deadline):
            return None
        hoje_d = pd.Timestamp.now().normalize()
        if deadline < hoje_d:
            return -int((hoje_d - deadline).days)  # negativo = já passou
        # np.busday_count(d1, d2) counts [d1, d2) — inclusive start.
        # The original while-loop excluded hoje_d, so shift both bounds by +1 day
        # to reproduce (hoje_d, deadline] semantics exactly.
        d1 = (hoje_d + pd.Timedelta(days=1)).date()
        d2 = (pd.Timestamp(deadline) + pd.Timedelta(days=1)).date()
        return int(np.busday_count(d1, d2))

    df_sla = df_pend[~df_pend["Status"].isin(status_done_pend | status_canceled_pend)].copy()
    df_sla["Start Date"] = pd.to_datetime(df_sla["Start Date"], errors="coerce").dt.tz_localize(None)
    df_sla["Deadline"]   = pd.to_datetime(df_sla["Deadline"],   errors="coerce").dt.tz_localize(None)
    hoje_sla = pd.Timestamp.now().normalize()

    # Dias corridos desde Start Date (impedimento)
    df_sla["Dias Impedimento"] = (hoje_sla - df_sla["Start Date"]).dt.days

    # Dias úteis até Deadline
    df_sla["DU Restantes"] = df_sla["Deadline"].apply(dias_uteis_restantes)

    def classificar_sla(row):
        du = row["DU Restantes"]
        di = row["Dias Impedimento"]

        # Sem deadline: classifica só por dias de impedimento
        if pd.isna(du):
            if pd.isna(di) or di < 0:
                return "normal", "✅ Normal", "#2ca02c", "L1", "Acompanhamento regular"
            elif di >= 5:
                return "impedimento_5", "🔴 Impedimento Crítico", "#7b0000", "L5", "Avaliação de impacto no programa — decisão executiva"
            elif di >= 2:
                return "impedimento_2", "🟣 Impedimento Grave", "#7b2d8b", "L3", "Priorização executiva — plano imediato de desbloqueio"
            elif di >= 0:
                return "impedimento_0", "🔴 Impedimento", "#d62728", "L2", "Comunicação formal de impedimento — avaliação de impacto"
            return "normal", "✅ Normal", "#2ca02c", "L1", "Acompanhamento regular"

        # Com deadline: usa dias úteis restantes (pré-impedimento)
        if du <= 0:
            # Passou do deadline → impedimento
            dias_imp = abs(du)
            if dias_imp >= 5:
                return "impedimento_5", "🔴 Impedimento Crítico", "#7b0000", "L5", "Avaliação de impacto no programa — decisão executiva"
            elif dias_imp >= 2:
                return "impedimento_2", "🟣 Impedimento Grave", "#7b2d8b", "L3", "Priorização executiva — plano imediato de desbloqueio"
            else:
                return "impedimento_0", "🔴 Impedimento", "#d62728", "L2", "Comunicação formal de impedimento — avaliação de impacto"
        elif du <= 1:
            return "d1", "🟠 D-1 Escalonamento L3", "#e05c00", "L3", "Alinhamento de urgência — definição de ação imediata"
        elif du <= 3:
            return "d3", "🟡 D-3 Escalonamento L2", "#d4a000", "L2", "Revisão do bloqueio — validação de alternativas"
        elif du <= 5:
            return "d5", "🔵 D-5 Atenção L1", "#1f77b4", "L1", "Reforço de comunicação — confirmação de plano e data"
        else:
            return "normal", "✅ Normal", "#2ca02c", "L1", "Acompanhamento regular"

    df_sla[["_nivel", "Nível SLA", "Cor", "Escalonamento", "Ação"]] = df_sla.apply(
        lambda r: pd.Series(classificar_sla(r)), axis=1
    )

    # Ordem de exibição por criticidade
    ordem_nivel = ["impedimento_5", "impedimento_2", "impedimento_0", "d1", "d3", "d5", "normal"]
    df_sla["_ordem"] = df_sla["_nivel"].map({v: i for i, v in enumerate(ordem_nivel)})
    df_sla = df_sla.sort_values("_ordem")

    # ── Resumo visual (contadores por nível) ──
    niveis_resumo = df_sla.groupby(["Nível SLA", "Cor", "Escalonamento"]).size().reset_index(name="Qtd")
    niveis_resumo["_ordem"] = niveis_resumo["Nível SLA"].map(
        {row["Nível SLA"]: row["_ordem"] for _, row in df_sla.drop_duplicates("Nível SLA").iterrows()}
    )
    niveis_resumo = niveis_resumo.sort_values("_ordem")

    _bg   = "#1b2a3b" if tema_selecionado != "☀️ Claro" else "#f8fafc"
    _txt  = "#e8edf2" if tema_selecionado != "☀️ Claro" else "#0d1b2a"
    _brd  = "#1f3a5c" if tema_selecionado != "☀️ Claro" else "#d0dff0"
    _bg2  = "#0d1b2a" if tema_selecionado != "☀️ Claro" else "#e8f0f8"

    cols_resumo = st.columns(max(len(niveis_resumo), 1))
    for i, (_, nr) in enumerate(niveis_resumo.iterrows()):
        with cols_resumo[i]:
            st.markdown(f"""
            <div style="background:{_bg}; border:2px solid {nr['Cor']}; border-radius:10px;
                        padding:14px 12px; text-align:center;">
                <div style="font-size:11px; color:{nr['Cor']}; font-weight:700; margin-bottom:4px;">
                    {nr['Nível SLA']}
                </div>
                <div style="font-size:32px; font-weight:800; color:{_txt};">{nr['Qtd']}</div>
                <div style="font-size:11px; color:#888; margin-top:4px;">Escal. {nr['Escalonamento']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gantt de pendências abertas ──
    df_gantt = df_sla[df_sla["Start Date"].notna() & df_sla["Deadline"].notna()].copy()
    if not df_gantt.empty:
        fig_gantt = go.Figure()

        for _, row in df_gantt.iterrows():
            fig_gantt.add_trace(go.Bar(
                x=[(row["Deadline"] - row["Start Date"]).days],
                y=[f"{row['Chave']}"],
                base=[(row["Start Date"] - df_gantt["Start Date"].min()).days],
                orientation="h",
                marker_color=row["Cor"],
                name=row["Nível SLA"],
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['Chave']}</b><br>"
                    f"{row['Titulo']}<br>"
                    f"Start: {row['Start Date'].strftime('%d/%m/%Y')}<br>"
                    f"Deadline: {row['Deadline'].strftime('%d/%m/%Y')}<br>"
                    f"Nível: {row['Nível SLA']}<br>"
                    f"Escalonamento: {row['Escalonamento']}<br>"
                    f"Ação: {row['Ação']}<extra></extra>"
                ),
            ))

        # Linha de hoje
        hoje_offset = (hoje_sla - df_gantt["Start Date"].min()).days
        fig_gantt.add_vline(
            x=hoje_offset, line_dash="dash", line_color="#ff7f0e",
            annotation_text="Hoje", annotation_position="top",
        )

        fig_gantt.update_layout(
            title="Linha do Tempo das Pendências Abertas",
            barmode="overlay",
            template=plotly_template,
            paper_bgcolor=plotly_paper_bgcolor,
            plot_bgcolor=plotly_plot_bgcolor,
            font=dict(color=plotly_font_color),
            xaxis=dict(title="Dias desde a 1ª Start Date", **plotly_axis_style),
            yaxis=dict(title="", autorange="reversed", **plotly_axis_style),
            height=max(200, len(df_gantt) * 40 + 80),
            margin=dict(l=120, r=20, t=50, b=40),
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cards por pendência com nível SLA ──
    st.markdown("**Detalhamento por Pendência**")
    for _, row in df_sla.iterrows():
        du      = row["DU Restantes"]
        di      = int(row["Dias Impedimento"]) if pd.notna(row["Dias Impedimento"]) else None
        prior   = row.get("Prioridade", "-") or "-"
        desc    = str(row.get("Descricao", "") or "")
        desc_c  = desc[:250] + "..." if len(desc) > 250 else desc
        cor     = row["Cor"]
        nivel   = row["Nível SLA"]
        escal   = row["Escalonamento"]
        acao    = row["Ação"]
        bg_card = "#1b2a3b" if tema_selecionado != "☀️ Claro" else "#f8fafc"
        txt_c   = "#e8edf2" if tema_selecionado != "☀️ Claro" else "#0d1b2a"

        du_txt = f"{du} dias úteis restantes" if du is not None and du > 0 else (
            f"{abs(du)} dias úteis em atraso" if du is not None and du < 0 else "Sem deadline"
        )
        deadline_str = row["Deadline"].strftime("%d/%m/%Y") if pd.notna(row["Deadline"]) else "—"

        st.markdown(f"""
        <div style="border-left:5px solid {cor}; background:{bg_card}; padding:14px 18px;
                    border-radius:8px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:6px;">
                <span style="font-weight:700; font-size:15px; color:{cor};">{row['Chave']} — {row['Titulo']}</span>
                <span style="background:{cor}; color:#fff; padding:3px 12px;
                             border-radius:12px; font-size:12px; font-weight:700; white-space:nowrap;">
                    {nivel}
                </span>
            </div>
            <div style="display:flex; gap:20px; margin:8px 0 4px 0; flex-wrap:wrap;">
                <span style="font-size:12px; color:#888;">Prioridade: <b style="color:{txt_c};">{prior}</b></span>
                <span style="font-size:12px; color:#888;">Deadline: <b style="color:{txt_c};">{deadline_str}</b></span>
                <span style="font-size:12px; color:#888;">⏳ <b style="color:{cor};">{du_txt}</b></span>
                <span style="font-size:12px; color:#888;">📅 {di} dias desde abertura</span>
            </div>
            <div style="background:{_bg2}; border-radius:6px; padding:8px 12px; margin:6px 0;">
                <span style="font-size:12px; color:#888;">🔺 Escalonamento: </span>
                <span style="font-size:12px; font-weight:700; color:{cor};">{escal}</span>
                <span style="font-size:12px; color:#888;"> &nbsp;|&nbsp; Ação: </span>
                <span style="font-size:12px; color:{txt_c};">{acao}</span>
            </div>
            <div style="font-size:13px; color:{txt_c}; opacity:0.85; white-space:pre-wrap; margin-top:4px;">
                {desc_c if desc_c else '<i>Sem descrição.</i>'}
            </div>
        </div>
        """, unsafe_allow_html=True)

