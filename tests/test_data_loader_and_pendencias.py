"""
Unit tests for:
  - app/dashboard/data_loader.py :: carregar_dados_csv  (TEST-10)
  - app/scripts/script_pendencias.py :: adf_para_texto  (TEST-11)
"""
import sys
import os
import pytest
import pandas as pd

# ── data_loader path ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'dashboard'))
from data_loader import carregar_dados_csv

# ── script_pendencias path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'scripts'))
from script_pendencias import adf_para_texto


COLUMNS = [
    'Epico', 'Historia', 'Titulo Historia', 'Data-Lake', 'Chave', 'Titulo',
    'Status', 'Data Criacao', 'Data Atualizacao', 'Quantidade Subtarefas',
    'Categoria_Analise', 'Start Date Historia', 'Deadline Historia',
]

CSV_HEADER = ','.join(COLUMNS)
CSV_ROW1 = 'BF3E4-100,BF3E4-200,[COMPRAS-1] Story A,COMPRAS,BF3E4-300,Task 1,Done,2026-01-01,2026-01-10,3,RN,2026-01-01,2026-03-31'
CSV_ROW2 = 'BF3E4-101,BF3E4-201,[RH-2] Story B,RH,BF3E4-301,Task 2,In Progress,2026-01-05,2026-01-15,2,Story Bug,2026-01-05,2026-06-30'
CSV_ROW3 = 'BF3E4-102,BF3E4-202,[FIN-3] Story C,FIN,BF3E4-302,Task 3,To Do,2026-01-10,2026-01-20,1,Desenvolvimento/Outros,2026-01-10,2026-09-30'


# ── TEST-10: carregar_dados_csv ──────────────────────────────────────────────

class TestCarregarDadosCsv:
    def _write_csv(self, tmp_path, rows):
        p = tmp_path / 'test_fase3.csv'
        content = '\n'.join([CSV_HEADER] + rows)
        p.write_text(content, encoding='utf-8-sig')
        return str(p)

    def test_valid_csv_returns_dataframe(self, tmp_path):
        path = self._write_csv(tmp_path, [CSV_ROW1, CSV_ROW2, CSV_ROW3])
        df = carregar_dados_csv(path)
        assert isinstance(df, pd.DataFrame)

    def test_valid_csv_row_count(self, tmp_path):
        path = self._write_csv(tmp_path, [CSV_ROW1, CSV_ROW2, CSV_ROW3])
        df = carregar_dados_csv(path)
        assert len(df) == 3

    def test_valid_csv_correct_columns(self, tmp_path):
        path = self._write_csv(tmp_path, [CSV_ROW1, CSV_ROW2, CSV_ROW3])
        df = carregar_dados_csv(path)
        assert list(df.columns) == COLUMNS

    def test_first_column_no_bom_prefix(self, tmp_path):
        """utf-8-sig BOM should not appear in column name."""
        path = self._write_csv(tmp_path, [CSV_ROW1])
        df = carregar_dados_csv(path)
        assert df.columns[0] == 'Epico'
        assert '\ufeff' not in df.columns[0]

    def test_file_not_found_returns_none(self, tmp_path):
        result = carregar_dados_csv(str(tmp_path / 'nonexistent.csv'))
        assert result is None

    def test_empty_csv_header_only_returns_empty_dataframe(self, tmp_path):
        path = self._write_csv(tmp_path, [])  # header only, no rows
        df = carregar_dados_csv(path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == COLUMNS

    def test_single_row_csv(self, tmp_path):
        path = self._write_csv(tmp_path, [CSV_ROW1])
        df = carregar_dados_csv(path)
        assert len(df) == 1
        assert df.iloc[0]['Status'] == 'Done'
        assert df.iloc[0]['Data-Lake'] == 'COMPRAS'


# ── TEST-11: adf_para_texto ──────────────────────────────────────────────────

class TestAdfParaTexto:
    def test_none_returns_empty(self):
        assert adf_para_texto(None) == ''

    def test_plain_string_returned_as_is(self):
        assert adf_para_texto('plain string') == 'plain string'

    def test_empty_list_returns_empty(self):
        assert adf_para_texto([]) == ''

    def test_list_of_text_nodes_joined(self):
        nodes = [
            {'type': 'text', 'text': 'hello'},
            {'type': 'text', 'text': ' world'},
        ]
        assert adf_para_texto(nodes) == 'hello world'

    def test_text_node(self):
        assert adf_para_texto({'type': 'text', 'text': 'hello'}) == 'hello'

    def test_hard_break_returns_newline(self):
        assert adf_para_texto({'type': 'hardBreak'}) == '\n'

    def test_paragraph_appends_newline(self):
        node = {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'line'}]}
        assert adf_para_texto(node) == 'line\n'

    def test_heading_appends_newline(self):
        node = {'type': 'heading', 'content': [{'type': 'text', 'text': 'Title'}]}
        assert adf_para_texto(node) == 'Title\n'

    def test_bullet_list(self):
        node = {
            'type': 'bulletList',
            'content': [
                {'type': 'listItem', 'content': [{'type': 'text', 'text': 'item A'}]},
                {'type': 'listItem', 'content': [{'type': 'text', 'text': 'item B'}]},
            ]
        }
        result = adf_para_texto(node)
        assert '• item A' in result
        assert '• item B' in result

    def test_ordered_list(self):
        node = {
            'type': 'orderedList',
            'content': [
                {'type': 'listItem', 'content': [{'type': 'text', 'text': 'first'}]},
                {'type': 'listItem', 'content': [{'type': 'text', 'text': 'second'}]},
            ]
        }
        result = adf_para_texto(node)
        assert '1.' in result
        assert '2.' in result
        assert 'first' in result
        assert 'second' in result

    def test_unknown_type_falls_back_to_joined_children(self):
        node = {'type': 'customBlock', 'content': [{'type': 'text', 'text': 'raw'}]}
        assert adf_para_texto(node) == 'raw'

    def test_non_dict_non_str_non_list_returns_empty(self):
        assert adf_para_texto(42) == ''
        assert adf_para_texto(3.14) == ''

    def test_nested_doc_flattened(self):
        doc = {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Antes'},
                        {'type': 'hardBreak'},
                        {'type': 'text', 'text': 'Depois'},
                    ]
                }
            ]
        }
        result = adf_para_texto(doc)
        assert 'Antes' in result
        assert 'Depois' in result
        assert '\n' in result

    def test_empty_text_node_returns_empty(self):
        assert adf_para_texto({'type': 'text', 'text': ''}) == ''
