"""Módulo de autenticação via Supabase."""
import base64
import hashlib
import hmac
import secrets
import streamlit as st

from supabase_client import get_supabase

try:
    import bcrypt as _bcrypt
except ModuleNotFoundError:
    _bcrypt = None


# ── Helpers de senha ──────────────────────────────────────────────────────────

_PBKDF2_PREFIX = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 390000


def _hash_senha_pbkdf2(senha: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt, _PBKDF2_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode()
    digest_b64 = base64.b64encode(digest).decode()
    return f"{_PBKDF2_PREFIX}${_PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def _verificar_senha_pbkdf2(senha: str, hash_: str) -> bool:
    try:
        prefix, iterations, salt_b64, digest_b64 = hash_.split('$', 3)
        if prefix != _PBKDF2_PREFIX:
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        current = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt, int(iterations))
        return hmac.compare_digest(current, expected)
    except Exception:
        return False


def hash_senha(senha: str) -> str:
    if _bcrypt is not None:
        return _bcrypt.hashpw(senha.encode(), _bcrypt.gensalt()).decode()
    return _hash_senha_pbkdf2(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    try:
        if str(hash_).startswith(f"{_PBKDF2_PREFIX}$"):
            return _verificar_senha_pbkdf2(senha, hash_)
        if _bcrypt is None:
            return False
        return _bcrypt.checkpw(senha.encode(), hash_.encode())
    except Exception:
        return False


# ── Operações no banco ────────────────────────────────────────────────────────

def buscar_usuario(username: str) -> dict | None:
    sb = get_supabase()
    res = sb.table("usuarios").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None


def cadastrar_usuario(nome: str, username: str, email: str, senha: str) -> tuple[bool, str]:
    sb = get_supabase()
    # Verifica duplicidade
    if buscar_usuario(username):
        return False, "Nome de usuário já cadastrado."
    res_email = sb.table("usuarios").select("id").eq("email", email).execute()
    if res_email.data:
        return False, "E-mail já cadastrado."
    sb.table("usuarios").insert({
        "nome":     nome,
        "username": username,
        "email":    email,
        "senha":    hash_senha(senha),
        "status":   "pendente",
        "paginas":  [],
    }).execute()
    return True, "Cadastro realizado! Aguarde aprovação do administrador."


def alterar_senha(username: str, senha_atual: str, nova_senha: str) -> tuple[bool, str]:
    usuario = buscar_usuario(username)
    if not usuario:
        return False, "Usuário não encontrado."
    if not verificar_senha(senha_atual, usuario["senha"]):
        return False, "Senha atual incorreta."
    sb = get_supabase()
    sb.table("usuarios").update({"senha": hash_senha(nova_senha)}).eq("username", username).execute()
    return True, "Senha alterada com sucesso!"


def listar_pendentes() -> list[dict]:
    sb = get_supabase()
    res = sb.table("usuarios").select("*").eq("status", "pendente").order("created_at").execute()
    return res.data or []


def listar_aprovados() -> list[dict]:
    sb = get_supabase()
    res = sb.table("usuarios").select("*").eq("status", "aprovado").order("nome").execute()
    return res.data or []


def aprovar_usuario(user_id: int, paginas: list[str]) -> None:
    sb = get_supabase()
    sb.table("usuarios").update({"status": "aprovado", "paginas": paginas}).eq("id", user_id).execute()


def rejeitar_usuario(user_id: int) -> None:
    sb = get_supabase()
    sb.table("usuarios").update({"status": "rejeitado"}).eq("id", user_id).execute()


def atualizar_paginas(user_id: int, paginas: list[str]) -> None:
    sb = get_supabase()
    sb.table("usuarios").update({"paginas": paginas}).eq("id", user_id).execute()


# ── Login / sessão ────────────────────────────────────────────────────────────

def fazer_login(username: str, senha: str) -> tuple[bool, str]:
    usuario = buscar_usuario(username)
    if not usuario:
        return False, "Usuário ou senha incorretos."
    if usuario["status"] == "pendente":
        return False, "Seu cadastro ainda está pendente de aprovação."
    if usuario["status"] == "rejeitado":
        return False, "Seu acesso foi negado. Entre em contato com o administrador."
    if not verificar_senha(senha, usuario["senha"]):
        return False, "Usuário ou senha incorretos."
    # Grava na session_state
    st.session_state["autenticado"]  = True
    st.session_state["username"]     = usuario["username"]
    st.session_state["name"]         = usuario["nome"]
    st.session_state["paginas"]      = usuario["paginas"] or []
    st.session_state["is_admin"]     = usuario.get("is_admin", False)
    return True, "Login realizado com sucesso!"


def fazer_logout() -> None:
    for k in ["autenticado", "username", "name", "paginas", "is_admin"]:
        st.session_state.pop(k, None)


# ── Guard de página ───────────────────────────────────────────────────────────

def _logo_sidebar():
    import os
    # Tenta encontrar o logo subindo a árvore de diretórios
    base = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        candidate = os.path.join(os.path.dirname(base), "assets", "AIR_logo.png")
        if os.path.exists(candidate):
            st.logo(candidate, size="large")
            st.markdown("""
            <style>
                [data-testid="stLogo"] { height: 4rem !important; max-width: 100% !important; }
                [data-testid="stLogo"] img { height: 4rem !important; width: auto !important; }
            </style>
            """, unsafe_allow_html=True)
            return
        base = os.path.dirname(base)


def exigir_login(pagina: str):
    """
    Exibe formulário de login e bloqueia a página se não autenticado
    ou sem permissão. Retorna (name, username) quando liberado.
    """
    _logo_sidebar()

    if not st.session_state.get("autenticado"):
        _mostrar_formulario_login()
        st.stop()

    paginas = st.session_state.get("paginas", [])
    if pagina not in paginas:
        st.error("Você não tem permissão para acessar esta página.")
        if st.button("Sair"):
            fazer_logout()
            st.rerun()
        st.stop()

    # Sidebar: logout + nome
    with st.sidebar:
        if st.button("Sair", key="logout_sidebar"):
            fazer_logout()
            st.rerun()
        st.markdown(f"👤 **{st.session_state['name']}**")

    return st.session_state["name"], st.session_state["username"]


def _mostrar_formulario_login():
    import os

    # Banner
    _base = os.path.dirname(os.path.abspath(__file__))
    _banner = os.path.join(os.path.dirname(_base), "assets", "cover LD_profissionais_01.png")
    if os.path.exists(_banner):
        st.image(_banner, use_container_width=True)

    # Formulário centralizado
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("## 🔐 Login")

        with st.form("form_login"):
            username = st.text_input("Usuário")
            senha    = st.text_input("Senha", type="password")
            entrar   = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            ok, msg = fazer_login(username.strip(), senha)
            if ok:
                st.rerun()
            else:
                st.error(msg)

        st.markdown("---")
        st.markdown("Não tem acesso? [Solicite aqui](./cadastro)", unsafe_allow_html=True)

        # Rodapé — versão + autor
        st.markdown(
            """
            <div style="text-align:center; margin-top: 32px; font-size: 12px; opacity: 0.6;">
                v1.0 &nbsp;|&nbsp;
                Desenvolvido por <a href="https://www.linkedin.com/in/gersonlramos/" target="_blank"
                style="color: inherit; text-decoration: underline;">Gerson Ramos</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
