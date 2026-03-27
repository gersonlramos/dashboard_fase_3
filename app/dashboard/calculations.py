"""
calculations.py - Pure calculation functions extracted from dashboard.py.
These functions have no Streamlit dependency and can be imported in tests.
"""
import re
import numpy as np
import pandas as pd
import os
import glob


def calcular_curva_aprendizado(data_inicio, data_fim, total, inflexao=0.6, inclinacao=9, datas_planejado=None, valores_planejado=None):
    """
    Gera pontos de uma curva sigmoide representando a curva de aprendizado do time.
    - inflexao: fracao do periodo onde o ritmo acelera (0.6 = 60% do periodo)
    Valor > 0.5 garante que a curva fica abaixo do planejado no inicio e
    cruza/supera apos a metade, refletindo atraso inicial e aceleracao posterior.
    - inclinacao: quao abrupta e a transicao (k=8 gera curva suave mas perceptivel)
    - datas_planejado, valores_planejado: se fornecidos, aplica a sigmoide sobre o Planejado

    Quando recebe o Planejado como referencia, a sigmoide modula os valores planejados
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
        # Caso padrao: aplica a sigmoide diretamente sobre o total
        valores_finais = [total * v for v in valores_sigmoide_norm]

    return list(datas), valores_finais


def calcular_dias_uteis(data_inicio, data_fim):
    """
    Calcula quantidade de dias uteis entre duas datas (exclui sabados e domingos).
    """
    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0

    # Converte para datetime64
    d1 = pd.Timestamp(data_inicio).date()
    d2 = pd.Timestamp(data_fim).date()

    # Se data_fim < data_inicio, retorna 0
    if d2 < d1:
        return 0

    # busday_count conta dias uteis (seg-sex)
    return np.busday_count(d1, d2)


def colorir_status(val):
    cores_status = {
        'Done': 'background-color: #90EE90; color: black',
        'Closed': 'background-color: #90EE90; color: black',
        'Resolved': 'background-color: #90EE90; color: black',
        'Concluído': 'background-color: #90EE90; color: black',
        'Concluido': 'background-color: #90EE90; color: black',
        'Concluida': 'background-color: #90EE90; color: black',
        'In Progress': 'background-color: #87CEEB; color: black',
        'To Do': 'background-color: #FFE4B5; color: black',
        'Backlog': 'background-color: #D3D3D3; color: black',
        'Canceled': 'background-color: #FFD700; color: black',
        'Cancelled': 'background-color: #FFD700; color: black',
        'Cancelado': 'background-color: #FFD700; color: black'
    }
    return cores_status.get(val, '')


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


def parse_data_criacao(data_str):
    if pd.isna(data_str) or data_str == '':
        return pd.NaT

    # Converte para string e remove espacos
    data_str = str(data_str).strip()

    # Tenta parsing com diferentes formatos
    formatos = [
        '%Y-%m-%dT%H:%M:%S.%f%z',  # ISO com microsegundos e timezone
        '%Y-%m-%dT%H:%M:%S%z',      # ISO sem microsegundos com timezone
        '%Y-%m-%d %H:%M:%S',        # Formato padrao sem timezone
        '%d/%m/%Y',                  # Formato BR
    ]

    for fmt in formatos:
        try:
            # Remove o timezone manualmente se existir (substitui por Z para UTC)
            if '+' in data_str or data_str.count('-') > 2:
                # Remove timezone (tudo apos o ultimo ':' seguido de digitos)
                if 'T' in data_str:
                    data_str_sem_tz = data_str[:data_str.rfind('+' if '+' in data_str else '-')] if ('+' in data_str or data_str.rfind('-') > 10) else data_str
                    return pd.to_datetime(data_str_sem_tz)
            return pd.to_datetime(data_str, format=fmt)
        except (ValueError, TypeError):
            continue

    # Se nenhum formato funcionou, tenta o parsing automatico do pandas
    return pd.to_datetime(data_str, errors='coerce')


def classificar_subtarefa(titulo):
    titulo = str(titulo).upper() if pd.notna(titulo) else ""

    # Ordem de prioridade na verificacao:
    # 1. Story Bug
    if re.search(r'STORY\s*BUG', titulo):
        return "Story Bug"

    # 2. Regra de Negocio FMK (Mais especifico)
    if "RN-FMK" in titulo:
        return "RN-FMK"

    # 3. Regra de Negocio (Busca o termo 'RN' isolado)
    if re.search(r'\bRN\b', titulo):
        return "RN"

    return "Desenvolvimento/Outros"


def monte_carlo_forecast(daily_throughput, remaining, n_simulations=5000, seed=42):
    """Retorna offsets de dias P50/P85 para conclusao ou None quando base e insuficiente."""
    if remaining <= 0:
        return {"p50": 0, "p85": 0}

    if daily_throughput is None:
        return None

    arr = np.asarray(daily_throughput, dtype=float)
    arr = arr[np.isfinite(arr)]
    arr = arr[arr > 0]

    if len(arr) < 3:
        return None

    rng = np.random.default_rng(seed)
    days = []
    for _ in range(int(n_simulations)):
        done = 0.0
        d = 0
        while done < remaining and d < 3650:
            done += float(rng.choice(arr))
            d += 1
        days.append(d)

    if not days:
        return None

    p50 = int(np.percentile(days, 50))
    p85 = int(np.percentile(days, 85))
    return {"p50": max(p50, 1), "p85": max(p85, max(p50, 1))}


def forecast_linear_range(ritmo, remaining):
    """Retorna dias de projecao linear para cenarios melhor/atual/pior."""
    if remaining <= 0:
        return {"melhor": 0, "atual": 0, "pior": 0}

    ritmo = float(ritmo) if ritmo is not None else 0.0
    if ritmo <= 0:
        return {"melhor": None, "atual": None, "pior": None}

    atual = int(np.ceil(remaining / ritmo))
    melhor = int(np.ceil(remaining / (ritmo * 1.3)))
    pior = int(np.ceil(remaining / max(ritmo * 0.7, 1e-9)))
    return {"melhor": max(melhor, 1), "atual": max(atual, 1), "pior": max(pior, 1)}


def projetar_burndown(ritmo, prazo_limite, historias_faltantes, total_planejado, realizado_atual, ultima_data_real_bh):
    """Projeta datas e valores de burndown dado um ritmo diario."""
    datas, valores = [], []
    if ritmo <= 0:
        return datas, valores
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


def get_completion_dates(df_fase3, dados_dir):
    historico_dir = os.path.join(dados_dir, 'historico')
    history_files = glob.glob(os.path.join(historico_dir, 'historico_completo-*.csv'))
    history_dfs = []
    for f in history_files:
        try:
            df_hist = pd.read_csv(f, encoding='utf-8-sig')
            if not df_hist.empty:
                history_dfs.append(df_hist)
        except Exception:
            continue
    if not history_dfs:
        df_hist_all = pd.DataFrame(columns=['Chave', 'Status Novo', 'Data Mudanca'])
    else:
        df_hist_all = pd.concat(history_dfs, ignore_index=True)
    df_hist_all['Status Novo'] = df_hist_all['Status Novo'].astype(str).str.strip().str.lower()
    done_statuses = {'done', 'closed', 'resolved', 'concluído', 'concluida', 'canceled', 'cancelled'}
    df_hist_all['Data Mudanca'] = pd.to_datetime(df_hist_all['Data Mudanca'], errors='coerce')
    df_hist_all = df_hist_all.dropna(subset=['Data Mudanca'])
    done_dates = (
        df_hist_all[df_hist_all['Status Novo'].isin(done_statuses)]
        .sort_values('Data Mudanca')
        .groupby('Chave')
        .first()['Data Mudanca']
        .rename('Done Date')
    )
    df_fase3 = df_fase3.set_index('Chave').join(done_dates).reset_index()
    done_col = pd.to_datetime(df_fase3['Done Date'], errors='coerce').dt.tz_localize(None)
    deadline_col = pd.to_datetime(df_fase3['Deadline Historia'], errors='coerce').dt.tz_localize(None)
    df_fase3['Completion Date'] = done_col.combine_first(deadline_col)
    return df_fase3


def get_delta_velocity(df, today=None):
    if today is None:
        today = pd.Timestamp('today').normalize()
    df_valid = df.dropna(subset=['Completion Date']).copy()
    df_valid['Completion Date'] = pd.to_datetime(df_valid['Completion Date'], errors='coerce').dt.tz_localize(None)
    df_valid = df_valid.dropna(subset=['Completion Date'])
    last_7d = df_valid[(df_valid['Completion Date'] > today - pd.Timedelta(days=7)) & (df_valid['Completion Date'] <= today)]
    prev_14d = df_valid[(df_valid['Completion Date'] > today - pd.Timedelta(days=21)) & (df_valid['Completion Date'] <= today - pd.Timedelta(days=7))]
    return len(last_7d) - len(prev_14d)
