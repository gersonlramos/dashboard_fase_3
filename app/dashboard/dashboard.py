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
        valores_plan_interp = df_interpolado['valor'].fillna(method='ffill').fillna(0).tolist()
        
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

# ── Indicadores de % Planejada e Realizada ──────────────────────────────────
_df_lake_pct = pd.read_csv(os.path.join(DADOS_DIR, 'datas_esperadas_por_lake.csv'), encoding='utf-8-sig')
_df_lake_pct['data_fim'] = pd.to_datetime(_df_lake_pct['data_fim'], dayfirst=True, errors='coerce')
_total_hist_pct = _df_lake_pct['id_historia'].nunique()

# % planejada: histórias com data_fim <= hoje / total de histórias
_hoje = pd.Timestamp(brt_time.date())
_hist_planejadas_ate_hoje = (_df_lake_pct['data_fim'] <= _hoje).sum()
_pct_planejada = (_hist_planejadas_ate_hoje / _total_hist_pct * 100) if _total_hist_pct > 0 else 0.0

# % realizada: subtarefas Done / total subtarefas (dados já carregados após filtro)
_df_pct = pd.read_csv(os.path.join(DADOS_DIR, 'FASE_3.csv'), encoding='utf-8-sig')
_status_done = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled'}
_total_sub = len(_df_pct)
_done_sub = _df_pct['Status'].astype(str).str.strip().str.lower().isin(_status_done).sum()
_pct_realizada = (_done_sub / _total_sub * 100) if _total_sub > 0 else 0.0

_col_p, _col_r = st.columns(2)
with _col_p:
    st.metric("📊 Porcentagem Planejada", f"{_pct_planejada:.1f}%",
              help="Percentual esperado de conclusão hoje segundo a curva de aprendizado (sigmoide)")
with _col_r:
    _delta_pct = _pct_realizada - _pct_planejada
    st.metric("✅ Porcentagem Realizada", f"{_pct_realizada:.1f}%",
              delta=f"{_delta_pct:+.1f}% vs planejado",
              delta_color="normal" if _delta_pct <= 0 else "inverse",
              help="Percentual de subtarefas concluídas (Done/Canceled) sobre o total")

st.markdown(hr_style, unsafe_allow_html=True)


# Função para carregar dados
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

# Filtros na sidebar
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros")

# Filtro por Data-Lake
# Normalizar para uppercase para evitar duplicatas (ex: COMPRAS vs Compras)
df['Data-Lake'] = df['Data-Lake'].astype(str).str.strip().str.upper()
data_lakes_unicos = ['Todas'] + sorted([str(d) for d in df['Data-Lake'].unique() if pd.notna(d) and str(d) not in ['N/A', 'NAN']])
data_lake_selecionado = st.sidebar.selectbox("Data-Lake:", data_lakes_unicos, index=0)

# Aplicar filtro de Data-Lake primeiro
df_filtrado = df.copy()
if data_lake_selecionado != 'Todas':
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
    ["📊 Executivo", "📈 Gráficos", "📋 Detalhes"],
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
            except:
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
df_lake = pd.read_csv(os.path.join(DADOS_DIR, 'datas_esperadas_por_lake.csv'), encoding='utf-8-sig', sep=',')
# Normalizar lake para uppercase e remover sufixos " A", " B", etc.
df_lake['lake'] = df_lake['lake'].astype(str).str.strip().str.upper()
# Remove sufixos como " A", " B" que separam squads mas não aparecem no Jira
df_lake['lake'] = df_lake['lake'].str.replace(r'\s+[A-Z]$', '', regex=True)

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

def calcular_ciclo_desenvolvimento(data_lake_filtro='Todas'):
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
    if data_lake_filtro == 'Todas':
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

def calcular_ciclo_ideal(data_lake_filtro='Todas'):
    """
    Calcula o ciclo ideal médio baseado nas datas planejadas (data_inicio e data_fim) 
    do arquivo datas_esperadas_por_lake.csv.
    Retorna: (ciclo_ideal_dias_uteis, num_historias) ou (None, None) se não houver dados
    """
    df_lake_ideal = pd.read_csv(os.path.join(DADOS_DIR, 'datas_esperadas_por_lake.csv'), encoding='utf-8-sig')
    
    # Normalizar lake
    df_lake_ideal['lake'] = df_lake_ideal['lake'].astype(str).str.strip().str.upper()
    df_lake_ideal['lake'] = df_lake_ideal['lake'].str.replace(r'\s+[A-Z]$', '', regex=True)
    
    # Filtrar por lake
    if data_lake_filtro != 'Todas':
        df_lake_ideal = df_lake_ideal[df_lake_ideal['lake'] == data_lake_filtro]
    
    if df_lake_ideal.empty:
        return None, None
    
    # Converter datas
    df_lake_ideal['data_inicio'] = pd.to_datetime(df_lake_ideal['data_inicio'], dayfirst=True, errors='coerce')
    df_lake_ideal['data_fim'] = pd.to_datetime(df_lake_ideal['data_fim'], dayfirst=True, errors='coerce')
    
    # Remover linhas sem datas válidas
    df_lake_ideal = df_lake_ideal.dropna(subset=['data_inicio', 'data_fim'])
    
    if df_lake_ideal.empty:
        return None, None
    
    # Calcular dias úteis para cada história
    ciclos_planejados = []
    for _, row in df_lake_ideal.iterrows():
        dias_uteis = calcular_dias_uteis(row['data_inicio'], row['data_fim'])
        if dias_uteis > 0:
            ciclos_planejados.append(dias_uteis)
    
    if not ciclos_planejados:
        return None, None
    
    ciclo_ideal_medio = sum(ciclos_planejados) / len(ciclos_planejados)
    num_historias = len(ciclos_planejados)
    
    return ciclo_ideal_medio, num_historias

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

# Carregar fases pós-desenvolvimento diretamente do FASE_3.csv (tasks de Homologação/Preparo)
# e preencher datas faltantes das subtarefas com datas_esperadas_por_lake.csv
_df_fase3_completo = df.copy()
_df_fase3_completo['Data Inicio'] = pd.to_datetime(_df_fase3_completo.get('Data Inicio', pd.NaT), errors='coerce')
_df_fase3_completo['Data Fim']    = pd.to_datetime(_df_fase3_completo.get('Data Fim', pd.NaT), errors='coerce')

# Preencher datas faltantes com datas_esperadas_por_lake.csv via id_historia
_df_lake_datas = df_lake[['id_historia', 'data_inicio', 'data_fim']].copy()
_df_lake_datas['data_inicio'] = pd.to_datetime(_df_lake_datas['data_inicio'], dayfirst=True, errors='coerce')
_df_lake_datas['data_fim']    = pd.to_datetime(_df_lake_datas['data_fim'],    dayfirst=True, errors='coerce')
_df_lake_datas['id_historia_norm'] = _df_lake_datas['id_historia'].apply(normalizar_id_historia)
_df_lake_datas = _df_lake_datas.drop_duplicates('id_historia_norm').set_index('id_historia_norm')

def _preencher_data(row, col_fase3, col_lake):
    val = row.get(col_fase3)
    if pd.notna(val):
        return val
    hist_norm = normalizar_id_historia(row.get('Historia'))
    if hist_norm and hist_norm in _df_lake_datas.index:
        return _df_lake_datas.loc[hist_norm, col_lake]
    return pd.NaT

_df_fase3_completo['Data Inicio'] = _df_fase3_completo.apply(
    lambda r: _preencher_data(r, 'Data Inicio', 'data_inicio'), axis=1)
_df_fase3_completo['Data Fim'] = _df_fase3_completo.apply(
    lambda r: _preencher_data(r, 'Data Fim', 'data_fim'), axis=1)

# Filtrar pelo lake selecionado (já normalizado para uppercase)
if data_lake_selecionado != 'Todas':
    _fases_filtradas = _df_fase3_completo[
        _df_fase3_completo['Data-Lake'] == data_lake_selecionado
    ]
else:
    _fases_filtradas = _df_fase3_completo

# Datas de Homologação e Preparo Produção
_homolog_rows = _fases_filtradas[_fases_filtradas['Categoria_Analise'] == 'Homologação']
_preparo_rows = _fases_filtradas[_fases_filtradas['Categoria_Analise'] == 'Preparo Produção']
data_inicio_homologacao = _homolog_rows['Data Inicio'].min() if not _homolog_rows.empty else pd.NaT
data_fim_homologacao    = _homolog_rows['Data Fim'].max()    if not _homolog_rows.empty else pd.NaT
data_inicio_preparo     = _preparo_rows['Data Inicio'].min() if not _preparo_rows.empty else pd.NaT
data_fim_preparo        = _preparo_rows['Data Fim'].max()    if not _preparo_rows.empty else pd.NaT

# Planejado: sempre baseado no datas_esperadas_por_lake.csv (data_fim por história)
if data_lake_selecionado == 'Todas':
    lakes_fase = df_lake.copy()
else:
    lakes_fase = df_lake[df_lake['lake'] == data_lake_selecionado].copy()

lakes_fase['data_fim'] = pd.to_datetime(lakes_fase['data_fim'], dayfirst=True, errors='coerce')
lakes_fase['id_historia_norm'] = lakes_fase['id_historia'].apply(normalizar_id_historia)

# Planejado agrupado por DIA (data_fim exata)
burn_planejado = (
    lakes_fase.dropna(subset=['data_fim'])
    .groupby('data_fim')
    .size()
    .reset_index(name='planejado')
)
burn_planejado.rename(columns={'data_fim': 'data'}, inplace=True)
# Garantir que 'data' seja datetime64[ns]
burn_planejado['data'] = pd.to_datetime(burn_planejado['data'])

# Real: história concluída quando todas as subtarefas estiverem concluídas
df_real_base = df.copy()
if data_lake_selecionado != 'Todas':
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

# Junta planejado, realizado total e realizado parcial
burn = pd.merge(burn_planejado, burn_real, on='data', how='outer')
burn = pd.merge(burn, burn_real_parcial, on='data', how='outer').fillna(0)
burn = burn.sort_values('data')
burn['planejado_acum'] = burn['planejado'].cumsum()
burn['realizado_acum'] = burn['realizado'].cumsum()
burn['realizado_parcial_acum'] = burn['realizado_parcial'].cumsum()

# Limita a linha do realizado até a última data de entrega
if not burn_real_parcial.empty:
    ultima_data_real_parcial = burn_real_parcial['data'].max()
    burn_real_parcial_mask = burn['data'] <= ultima_data_real_parcial
else:
    burn_real_parcial_mask = burn['data'] == False

# Projeção: extrapola o ritmo real até as datas finais esperadas
dados_real = burn.loc[burn_real_parcial_mask, ['data', 'realizado_parcial_acum']].copy()
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

if not dados_real.empty and dados_real['realizado_parcial_acum'].iloc[-1] > 0 and pd.notna(prazo_final_planejado):
    x = np.arange(len(dados_real))
    y = dados_real['realizado_parcial_acum'].values

    if len(x) > 1:
        coef = np.polyfit(x, y, 1)
        ritmo_hist_dia = float(coef[0])
    else:
        ritmo_hist_dia = float(y[-1])

    realizado_atual = float(y[-1])
    
    if ritmo_hist_dia > 0 and total_planejado > 0 and realizado_atual < total_planejado:
        ultima_data_real = dados_real['data'].iloc[-1]
        historias_faltantes = total_planejado - realizado_atual
        
        # Cenários de projeção
        ritmo_melhor = ritmo_hist_dia * 1.3  # 30% mais rápido
        ritmo_pior = ritmo_hist_dia * 0.7     # 30% mais lento
        
        # Função auxiliar para gerar projeção
        def gerar_projecao(ritmo, prazo_limite):
            datas = []
            valores = []
            dias_necessarios = int(np.ceil(historias_faltantes / ritmo))
            
            for i in range(dias_necessarios + 1):
                data_proj = ultima_data_real + pd.Timedelta(days=i)
                
                # Se passar da data final planejada, para
                if pd.notna(prazo_limite) and data_proj > prazo_limite:
                    break
                
                valor_proj = realizado_atual + ritmo * i
                if valor_proj >= total_planejado:
                    datas.append(data_proj)
                    valores.append(total_planejado)
                    break
                datas.append(data_proj)
                valores.append(valor_proj)
            
            return datas, valores
        
        # Gera as três projeções
        datas_proj, valores_proj = gerar_projecao(ritmo_hist_dia, prazo_final_planejado)
        datas_proj_melhor, valores_proj_melhor = gerar_projecao(ritmo_melhor, prazo_final_planejado)
        datas_proj_pior, valores_proj_pior = gerar_projecao(ritmo_pior, prazo_final_planejado)

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
_data_ini_burnout = burn['data'].min() if not burn.empty else pd.NaT
# Extrair datas e valores do planejado acumulado para a curva de aprendizado
_datas_plan_hist = list(burn['data']) if not burn.empty else []
_valores_plan_hist = list(burn['planejado_acum']) if not burn.empty else []
_datas_sig, _valores_sig = calcular_curva_aprendizado(
    _data_ini_burnout, prazo_final_planejado, total_planejado,
    datas_planejado=_datas_plan_hist, valores_planejado=_valores_plan_hist
)

total_historias = int(total_planejado)
historias_concluidas = int(burn['realizado_acum'].max()) if not burn.empty else 0
percentual_concluido_hist = (historias_concluidas / total_historias * 100) if total_historias > 0 else 0

if not dados_real.empty and ritmo_hist_dia > 0 and realizado_atual < total_planejado:
    historias_faltantes = total_planejado - realizado_atual
    dias_faltantes = int(np.ceil(historias_faltantes / ritmo_hist_dia))
    previsao_conclusao = dados_real['data'].iloc[-1] + pd.Timedelta(days=dias_faltantes)
    ritmo_melhor = ritmo_hist_dia * 1.3
    dias_faltantes_melhor = int(np.ceil(historias_faltantes / ritmo_melhor))
    previsao_melhor = dados_real['data'].iloc[-1] + pd.Timedelta(days=dias_faltantes_melhor)
    ritmo_pior = ritmo_hist_dia * 0.7
    dias_faltantes_pior = int(np.ceil(historias_faltantes / ritmo_pior))
    previsao_pior = dados_real['data'].iloc[-1] + pd.Timedelta(days=dias_faltantes_pior)
elif historias_concluidas >= total_historias:
    previsao_conclusao = burn.loc[burn['realizado_acum'] >= total_historias, 'data'].min() if not burn.empty else pd.NaT
    previsao_melhor = previsao_conclusao
    previsao_pior = previsao_conclusao
else:
    previsao_conclusao = pd.NaT
    previsao_melhor = pd.NaT
    previsao_pior = pd.NaT

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
            df_render.style.applymap(colorir_status, subset=['Status']),
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
fig_burn.add_trace(go.Scatter(
    x=burn.loc[burn_real_parcial_mask, 'data'],
    y=burn.loc[burn_real_parcial_mask, 'realizado_parcial_acum'],
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
    data_inicio_grafico = burn['data'].min() if not burn.empty else prazo_final_planejado
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
    if data_lake_selecionado != 'Todas':
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

# ── GRÁFICOS ──────────────────────────────────────────────────────────────────
elif aba_selecionada == "📈 Gráficos":
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
        colunas_todas = ['Data-Lake', 'Historia'] + [c for c in df_filtrado.columns if c not in ['Data-Lake', 'Historia']]
        renderizar_tabela(df_filtrado[colunas_todas].sort_index(ascending=False), tema_selecionado)
    else:
        colunas_resumo = ['Data-Lake', 'Historia', 'Titulo Historia', 'Chave', 'Titulo', 'Status', 'Categoria_Analise']
        renderizar_tabela(df_filtrado[colunas_resumo].sort_index(ascending=False), tema_selecionado)


