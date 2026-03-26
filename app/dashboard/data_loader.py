import os
import pandas as pd
from pandas.errors import ParserError


def carregar_dados_csv(arquivo):
    """Raw CSV loader — no Streamlit cache. Called by dashboard.carregar_dados()."""
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
