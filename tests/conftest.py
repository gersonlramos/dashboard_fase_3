import pytest
import pandas as pd

COLUMNS = [
    'Epico', 'Historia', 'Titulo Historia', 'Data-Lake', 'Chave',
    'Titulo', 'Status', 'Data Criacao', 'Data Atualizacao',
    'Quantidade Subtarefas', 'Categoria_Analise', 'Start Date Historia',
    'Deadline Historia',
]


@pytest.fixture
def sample_df():
    """Minimal DataFrame matching FASE_3.csv schema for unit tests."""
    rows = [
        {
            'Epico': 'PROJ-1', 'Historia': 'PROJ-10', 'Titulo Historia': 'Historia TAMANHO: M',
            'Data-Lake': 'COMPRAS', 'Chave': 'PROJ-100', 'Titulo': 'Subtarefa 1',
            'Status': 'Done', 'Data Criacao': '2026-01-10T09:00:00',
            'Data Atualizacao': '2026-03-01T10:00:00', 'Quantidade Subtarefas': 3,
            'Categoria_Analise': 'Desenvolvimento/Outros',
            'Start Date Historia': '2026-01-10', 'Deadline Historia': '2026-04-30',
        },
        {
            'Epico': 'PROJ-1', 'Historia': 'PROJ-11', 'Titulo Historia': 'Historia TAMANHO: P',
            'Data-Lake': 'COMPRAS', 'Chave': 'PROJ-101', 'Titulo': 'Subtarefa 2 Story Bug',
            'Status': 'In Progress', 'Data Criacao': '2026-01-15T09:00:00',
            'Data Atualizacao': '2026-03-15T10:00:00', 'Quantidade Subtarefas': 2,
            'Categoria_Analise': 'Story Bug',
            'Start Date Historia': '2026-01-15', 'Deadline Historia': '2026-04-30',
        },
        {
            'Epico': 'PROJ-2', 'Historia': 'PROJ-20', 'Titulo Historia': 'Historia TAMANHO: G',
            'Data-Lake': 'RH', 'Chave': 'PROJ-200', 'Titulo': 'Subtarefa 3 RN-001',
            'Status': 'To Do', 'Data Criacao': '2026-02-01T09:00:00',
            'Data Atualizacao': '2026-02-01T09:00:00', 'Quantidade Subtarefas': 5,
            'Categoria_Analise': 'RN',
            'Start Date Historia': '2026-02-01', 'Deadline Historia': '2026-05-31',
        },
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df['Data Criacao'] = pd.to_datetime(df['Data Criacao'])
    df['Data Atualizacao'] = pd.to_datetime(df['Data Atualizacao'])
    return df
