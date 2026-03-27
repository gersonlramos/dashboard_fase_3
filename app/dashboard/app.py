"""Ponto de entrada do dashboard — controla navegação por permissão."""
import os
import sys
import streamlit as st

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from auth import _mostrar_formulario_login, fazer_logout, _logo_sidebar

st.set_page_config(
    page_title="Dashboard Stellantis",
    page_icon="📊",
    layout="wide",
)

PAGES_DIR = os.path.join(SCRIPT_DIR, "pages")

# Página de cadastro sempre acessível (sem login)
pg_cadastro = st.Page(os.path.join(PAGES_DIR, "cadastro.py"), title="Solicitar Acesso", icon="📝")

# Logo
_logo_sidebar()

# ── Se não estiver logado: navegação só com login + cadastro ──────────────────
if not st.session_state.get("autenticado"):
    pg_login = st.Page(_mostrar_formulario_login, title="Login", icon="🔐")
    pg = st.navigation([pg_login, pg_cadastro], position="hidden")
    pg.run()
    st.stop()

# ── Monta lista de páginas conforme permissões ────────────────────────────────
paginas_usuario = st.session_state.get("paginas", [])
is_admin        = st.session_state.get("is_admin", False)

todas_as_paginas = {
    "estrategico":  st.Page(os.path.join(PAGES_DIR, "dashboard_estrategico.py"), title="Dashboard Estratégico", icon="📊"),
    "executivo":    st.Page(os.path.join(PAGES_DIR, "dashboard_executivo.py"),   title="Dashboard Executivo",   icon="📈"),
    "admin":        st.Page(os.path.join(PAGES_DIR, "admin.py"),                 title="Administração",         icon="🛡️"),
    "perfil":       st.Page(os.path.join(PAGES_DIR, "perfil.py"),                title="Meu Perfil",            icon="👤"),
}

# Páginas sempre visíveis para usuários logados
paginas_visiveis = []

# Páginas controladas por permissão
for key in ["estrategico", "executivo"]:
    if key in paginas_usuario:
        paginas_visiveis.append(todas_as_paginas[key])

# Admin só aparece para admins
if is_admin:
    paginas_visiveis.append(todas_as_paginas["admin"])

# Perfil sempre disponível para logados
paginas_visiveis.append(todas_as_paginas["perfil"])

if not paginas_visiveis:
    st.error("Você não tem acesso a nenhuma página. Entre em contato com o administrador.")
    if st.button("Sair"):
        fazer_logout()
        st.rerun()
    st.stop()

pg = st.navigation(paginas_visiveis)
pg.run()

# Sidebar: logout + nome — ao final, após os links de navegação
with st.sidebar:
    st.markdown("---")
    st.markdown(f"👤 **{st.session_state['name']}**")
    if st.button("Sair", key="logout_main"):
        fazer_logout()
        st.rerun()
