"""
calculations.py — Pure calculation functions extracted from dashboard.py.
These functions have no Streamlit dependency and can be imported in tests.
"""
import re
import numpy as np
import pandas as pd


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


def classificar_subtarefa(titulo):
    titulo = str(titulo).upper() if pd.notna(titulo) else ""

    # Ordem de prioridade na verificação:
    # 1. Story Bug
    if re.search(r'STORY\s*BUG', titulo):
        return "Story Bug"

    # 2. Regra de Negócio FMK (Mais específico)
    if "RN-FMK" in titulo:
        return "RN-FMK"

    # 3. Regra de Negócio (Busca o termo 'RN' isolado)
    if re.search(r'\bRN\b', titulo):
        return "RN"

    return "Desenvolvimento/Outros"


def projetar_burndown(ritmo, prazo_limite, historias_faltantes, total_planejado, realizado_atual, ultima_data_real_bh):
    """Projeta datas e valores de burndown dado um ritmo diário."""
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
