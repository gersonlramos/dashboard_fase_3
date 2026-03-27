"""
Testes de autenticação — cobre funções puras de auth.py sem depender de
Supabase nem de Streamlit (ambos são mockados via pytest-mock / unittest.mock).
"""
import sys
import types
import pytest
from unittest.mock import MagicMock, patch


# ── Stubs para imports que não existem no ambiente de testes ──────────────────

# Stub de streamlit
_st_stub = types.ModuleType("streamlit")
_st_stub.session_state = {}
_st_stub.error = lambda *a, **k: None
_st_stub.stop  = lambda: None
sys.modules.setdefault("streamlit", _st_stub)

# Stub de supabase_client (evita conexão real)
_sb_stub = types.ModuleType("supabase_client")
_sb_stub.get_supabase = MagicMock()
sys.modules.setdefault("supabase_client", _sb_stub)

# Carrega auth diretamente pelo caminho para evitar importar app.py via __init__
import importlib.util, os as _os

_auth_path = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "app", "dashboard", "auth.py"
)
_spec = importlib.util.spec_from_file_location("auth", _auth_path)
auth = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auth)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_session_state():
    """Limpa session_state antes de cada teste."""
    _st_stub.session_state.clear()
    yield
    _st_stub.session_state.clear()


def _usuario(status="aprovado", paginas=None, is_admin=False, senha=None):
    """Constrói um dict de usuário para usar nos mocks."""
    return {
        "id":       1,
        "nome":     "Fulano",
        "username": "fulano",
        "email":    "fulano@example.com",
        "senha":    senha or auth.hash_senha("senha123"),
        "status":   status,
        "paginas":  paginas or ["estrategico"],
        "is_admin": is_admin,
    }


# ── hash_senha / verificar_senha ──────────────────────────────────────────────

class TestHashSenha:
    def test_hash_nao_e_texto_plano(self):
        h = auth.hash_senha("minhasenha")
        assert h != "minhasenha"

    def test_verificar_senha_correta(self):
        h = auth.hash_senha("abc123")
        assert auth.verificar_senha("abc123", h) is True

    def test_verificar_senha_errada(self):
        h = auth.hash_senha("abc123")
        assert auth.verificar_senha("errada", h) is False

    def test_hashes_diferentes_para_mesma_senha(self):
        h1 = auth.hash_senha("igual")
        h2 = auth.hash_senha("igual")
        # bcrypt usa salt aleatório — hashes devem ser distintos
        assert h1 != h2

    def test_verificar_hash_invalido(self):
        assert auth.verificar_senha("senha", "hash_invalido") is False

    def test_verificar_string_vazia(self):
        h = auth.hash_senha("")
        assert auth.verificar_senha("", h) is True
        assert auth.verificar_senha("nao_vazia", h) is False


class TestPbkdf2Fallback:
    """Garante que o fallback PBKDF2 funciona mesmo sem bcrypt."""

    def test_pbkdf2_hash_e_verifica(self):
        h = auth._hash_senha_pbkdf2("teste")
        assert auth._verificar_senha_pbkdf2("teste", h) is True

    def test_pbkdf2_rejeita_senha_errada(self):
        h = auth._hash_senha_pbkdf2("teste")
        assert auth._verificar_senha_pbkdf2("outra", h) is False

    def test_pbkdf2_rejeita_hash_malformado(self):
        assert auth._verificar_senha_pbkdf2("senha", "nao$e$pbkdf2") is False

    def test_verificar_senha_usa_pbkdf2_quando_prefixo_presente(self):
        h = auth._hash_senha_pbkdf2("senha")
        assert auth.verificar_senha("senha", h) is True


# ── fazer_login ───────────────────────────────────────────────────────────────

class TestFazerLogin:
    def test_login_bem_sucedido(self):
        usuario = _usuario()
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, msg = auth.fazer_login("fulano", "senha123")
        assert ok is True
        assert _st_stub.session_state["autenticado"] is True
        assert _st_stub.session_state["username"] == "fulano"
        assert _st_stub.session_state["name"] == "Fulano"
        assert _st_stub.session_state["paginas"] == ["estrategico"]
        assert _st_stub.session_state["is_admin"] is False

    def test_login_usuario_inexistente(self):
        with patch.object(auth, "buscar_usuario", return_value=None):
            ok, msg = auth.fazer_login("ninguem", "senha")
        assert ok is False
        assert "incorretos" in msg.lower()

    def test_login_senha_errada(self):
        usuario = _usuario()
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, msg = auth.fazer_login("fulano", "senha_errada")
        assert ok is False
        assert "incorretos" in msg.lower()

    def test_login_status_pendente(self):
        usuario = _usuario(status="pendente")
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, msg = auth.fazer_login("fulano", "senha123")
        assert ok is False
        assert "pendente" in msg.lower()

    def test_login_status_rejeitado(self):
        usuario = _usuario(status="rejeitado")
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, msg = auth.fazer_login("fulano", "senha123")
        assert ok is False
        assert "negado" in msg.lower()

    def test_login_admin_seta_is_admin(self):
        usuario = _usuario(is_admin=True)
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, _ = auth.fazer_login("fulano", "senha123")
        assert ok is True
        assert _st_stub.session_state["is_admin"] is True

    def test_login_sem_paginas(self):
        usuario = _usuario(paginas=None)
        usuario["paginas"] = None
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, _ = auth.fazer_login("fulano", "senha123")
        assert ok is True
        assert _st_stub.session_state["paginas"] == []


# ── fazer_logout ──────────────────────────────────────────────────────────────

class TestFazerLogout:
    def test_logout_limpa_session(self):
        _st_stub.session_state.update({
            "autenticado": True,
            "username": "fulano",
            "name": "Fulano",
            "paginas": ["estrategico"],
            "is_admin": False,
        })
        auth.fazer_logout()
        for k in ["autenticado", "username", "name", "paginas", "is_admin"]:
            assert k not in _st_stub.session_state

    def test_logout_sem_sessao_nao_falha(self):
        _st_stub.session_state.clear()
        auth.fazer_logout()  # não deve lançar exceção


# ── cadastrar_usuario ─────────────────────────────────────────────────────────

class TestCadastrarUsuario:
    def _mock_supabase(self, usuario_existente=None, email_existente=False):
        sb = MagicMock()
        # buscar_usuario via tabela
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
            [usuario_existente] if usuario_existente else []
        )
        # verificação de email
        email_res = MagicMock()
        email_res.data = [{"id": 99}] if email_existente else []
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = None
        return sb

    def test_cadastro_duplicidade_username(self):
        with patch.object(auth, "buscar_usuario", return_value=_usuario()):
            ok, msg = auth.cadastrar_usuario("Novo", "fulano", "novo@x.com", "senha")
        assert ok is False
        assert "usuário" in msg.lower() or "username" in msg.lower() or "cadastrado" in msg.lower()

    def test_cadastro_duplicidade_email(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": 2}]
        with patch.object(auth, "buscar_usuario", return_value=None), \
             patch.object(auth, "get_supabase", return_value=sb):
            ok, msg = auth.cadastrar_usuario("Novo", "novo", "fulano@example.com", "senha")
        assert ok is False
        assert "e-mail" in msg.lower() or "email" in msg.lower()

    def test_cadastro_bem_sucedido(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch.object(auth, "buscar_usuario", return_value=None), \
             patch.object(auth, "get_supabase", return_value=sb):
            ok, msg = auth.cadastrar_usuario("Novo", "novo", "novo@x.com", "senha")
        assert ok is True
        assert "aprovação" in msg.lower() or "sucesso" in msg.lower() or "aguarde" in msg.lower()


# ── alterar_senha ─────────────────────────────────────────────────────────────

class TestAlterarSenha:
    def test_usuario_nao_encontrado(self):
        with patch.object(auth, "buscar_usuario", return_value=None):
            ok, msg = auth.alterar_senha("ninguem", "atual", "nova")
        assert ok is False
        assert "não encontrado" in msg.lower()

    def test_senha_atual_incorreta(self):
        usuario = _usuario()
        with patch.object(auth, "buscar_usuario", return_value=usuario):
            ok, msg = auth.alterar_senha("fulano", "errada", "nova123")
        assert ok is False
        assert "incorreta" in msg.lower()

    def test_alterar_senha_sucesso(self):
        usuario = _usuario()
        sb = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        with patch.object(auth, "buscar_usuario", return_value=usuario), \
             patch.object(auth, "get_supabase", return_value=sb):
            ok, msg = auth.alterar_senha("fulano", "senha123", "nova_senha")
        assert ok is True
        assert "sucesso" in msg.lower()
