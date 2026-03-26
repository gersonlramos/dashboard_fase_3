"""
Unit tests for app/scripts/script_atualizacao.py ETL helpers.
Covers TEST-08 (extrair_data_lake, classificar_subtarefa) and
TEST-09 (buscar_com_paginacao — single-page, multi-page, 401).
"""
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'scripts'))

import script_atualizacao


# ── TEST-08: extrair_data_lake ───────────────────────────────────────────────

class TestExtrairDataLake:
    def test_none_returns_na(self):
        assert script_atualizacao.extrair_data_lake(None) == 'N/A'

    def test_na_string_returns_na(self):
        assert script_atualizacao.extrair_data_lake('N/A') == 'N/A'

    def test_empty_string_returns_na(self):
        assert script_atualizacao.extrair_data_lake('') == 'N/A'

    def test_bracket_with_hyphen_returns_prefix(self):
        assert script_atualizacao.extrair_data_lake('[COMPRAS-123]') == 'COMPRAS'

    def test_bracket_with_hyphen_in_title(self):
        assert script_atualizacao.extrair_data_lake('[RH-10] Some story title') == 'RH'

    def test_bracket_without_hyphen_returns_full(self):
        # No hyphen inside brackets: return content as-is
        assert script_atualizacao.extrair_data_lake('[NO-HYPHEN]') == 'NO'

    def test_no_brackets_returns_na(self):
        assert script_atualizacao.extrair_data_lake('title without brackets') == 'N/A'

    def test_bracket_strips_whitespace(self):
        result = script_atualizacao.extrair_data_lake('[ COMPRAS - 123 ]')
        assert result == 'COMPRAS'


# ── TEST-08: classificar_subtarefa (from script_atualizacao) ────────────────

class TestClassificarSubtarefaEtl:
    """Parallel to TestClassificarSubtarefa in test_calculations.py.
    Verifies the ETL copy stayed in sync with calculations.py.
    """

    def test_story_bug_pattern(self):
        assert script_atualizacao.classificar_subtarefa('implementar Story Bug correção') == 'Story Bug'

    def test_story_bug_case_insensitive(self):
        assert script_atualizacao.classificar_subtarefa('STORY BUG fix') == 'Story Bug'

    def test_story_bug_no_space(self):
        assert script_atualizacao.classificar_subtarefa('storybug') == 'Story Bug'

    def test_rn_fmk_pattern(self):
        assert script_atualizacao.classificar_subtarefa('regra RN-FMK validacao') == 'RN-FMK'

    def test_rn_pattern(self):
        assert script_atualizacao.classificar_subtarefa('implementar RN negocio') == 'RN'

    def test_rn_word_boundary(self):
        # 'CRNT' contains 'RN' but \bRN\b does NOT match inside a word
        assert script_atualizacao.classificar_subtarefa('CRNT implementation') == 'Desenvolvimento/Outros'

    def test_default_classification(self):
        assert script_atualizacao.classificar_subtarefa('desenvolvimento tela login') == 'Desenvolvimento/Outros'

    def test_none_returns_default(self):
        assert script_atualizacao.classificar_subtarefa(None) == 'Desenvolvimento/Outros'

    def test_rn_fmk_takes_priority_over_rn(self):
        assert script_atualizacao.classificar_subtarefa('RN-FMK rule') == 'RN-FMK'


# ── TEST-09: buscar_com_paginacao ────────────────────────────────────────────

def _make_response(status_code, json_data):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.text = str(json_data)
    return r


class TestBuscarComPaginacao:
    def test_single_page_returns_all_issues(self):
        issue = {'key': 'BF3E4-1', 'fields': {}}
        resp = _make_response(200, {'issues': [issue], 'isLast': True})

        with patch('script_atualizacao.requests.get', return_value=resp) as mock_get:
            result = script_atualizacao.buscar_com_paginacao(
                jql='project=BF3E4', fields='key', auth='dummy'
            )

        assert len(result) == 1
        assert result[0]['key'] == 'BF3E4-1'
        assert mock_get.call_count == 1

    def test_multi_page_accumulates_all_issues(self):
        issue1 = {'key': 'BF3E4-1', 'fields': {}}
        issue2 = {'key': 'BF3E4-2', 'fields': {}}
        resp1 = _make_response(200, {'issues': [issue1], 'isLast': False, 'nextPageToken': 'tok1'})
        resp2 = _make_response(200, {'issues': [issue2], 'isLast': True})

        with patch('script_atualizacao.requests.get', side_effect=[resp1, resp2]) as mock_get:
            result = script_atualizacao.buscar_com_paginacao(
                jql='project=BF3E4', fields='key', auth='dummy'
            )

        assert len(result) == 2
        assert result[0]['key'] == 'BF3E4-1'
        assert result[1]['key'] == 'BF3E4-2'
        assert mock_get.call_count == 2

    def test_multi_page_second_call_includes_token(self):
        issue1 = {'key': 'BF3E4-1', 'fields': {}}
        issue2 = {'key': 'BF3E4-2', 'fields': {}}
        resp1 = _make_response(200, {'issues': [issue1], 'isLast': False, 'nextPageToken': 'my-token'})
        resp2 = _make_response(200, {'issues': [issue2], 'isLast': True})

        with patch('script_atualizacao.requests.get', side_effect=[resp1, resp2]) as mock_get:
            script_atualizacao.buscar_com_paginacao(
                jql='project=BF3E4', fields='key', auth='dummy'
            )

        # Second call must include nextPageToken in params
        second_call_kwargs = mock_get.call_args_list[1]
        params = second_call_kwargs[1]['params'] if second_call_kwargs[1] else second_call_kwargs[0][1]
        assert params.get('nextPageToken') == 'my-token'

    def test_401_returns_empty_list(self):
        resp = _make_response(401, {})

        with patch('script_atualizacao.requests.get', return_value=resp) as mock_get:
            result = script_atualizacao.buscar_com_paginacao(
                jql='project=BF3E4', fields='key', auth='dummy'
            )

        assert result == []
        assert mock_get.call_count == 1

    def test_no_issues_in_response_returns_empty(self):
        resp = _make_response(200, {'issues': [], 'isLast': True})

        with patch('script_atualizacao.requests.get', return_value=resp):
            result = script_atualizacao.buscar_com_paginacao(
                jql='project=BF3E4', fields='key', auth='dummy'
            )

        assert result == []

    def test_missing_next_page_token_stops_pagination(self):
        """isLast=False but nextPageToken absent — defensively stops."""
        issue1 = {'key': 'BF3E4-1', 'fields': {}}
        resp = _make_response(200, {'issues': [issue1], 'isLast': False})
        # No 'nextPageToken' key in the response

        with patch('script_atualizacao.requests.get', return_value=resp) as mock_get:
            result = script_atualizacao.buscar_com_paginacao(
                jql='project=BF3E4', fields='key', auth='dummy'
            )

        assert len(result) == 1
        assert mock_get.call_count == 1
