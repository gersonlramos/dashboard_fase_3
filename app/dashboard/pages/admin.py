import os
import sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from auth import (
    listar_pendentes, listar_aprovados,
    aprovar_usuario, rejeitar_usuario, atualizar_paginas,
)

PAGINAS_DISPONIVEIS = ["estrategico", "executivo"]

st.title("🛡️ Administração de Usuários")

# ── Pendentes ─────────────────────────────────────────────────────────────────
st.subheader("⏳ Solicitações Pendentes")
pendentes = listar_pendentes()

if not pendentes:
    st.info("Nenhuma solicitação pendente.")
else:
    for u in pendentes:
        with st.expander(f"👤 {u['nome']}  —  @{u['username']}  |  {u['email']}"):
            paginas_sel = st.multiselect(
                "Páginas permitidas",
                PAGINAS_DISPONIVEIS,
                key=f"pag_{u['id']}"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Aprovar", key=f"apr_{u['id']}", use_container_width=True):
                    aprovar_usuario(u["id"], paginas_sel)
                    st.success(f"{u['nome']} aprovado!")
                    st.rerun()
            with col2:
                if st.button("❌ Rejeitar", key=f"rej_{u['id']}", use_container_width=True):
                    rejeitar_usuario(u["id"])
                    st.warning(f"{u['nome']} rejeitado.")
                    st.rerun()

st.markdown("---")

# ── Aprovados ─────────────────────────────────────────────────────────────────
st.subheader("✅ Usuários Aprovados")
aprovados = listar_aprovados()

if not aprovados:
    st.info("Nenhum usuário aprovado ainda.")
else:
    for u in aprovados:
        with st.expander(f"👤 {u['nome']}  —  @{u['username']}  |  {u['email']}"):
            paginas_atuais = u.get("paginas") or []
            paginas_sel = st.multiselect(
                "Páginas permitidas",
                PAGINAS_DISPONIVEIS,
                default=[p for p in paginas_atuais if p in PAGINAS_DISPONIVEIS],
                key=f"edit_pag_{u['id']}"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Salvar permissões", key=f"save_{u['id']}", use_container_width=True):
                    atualizar_paginas(u["id"], paginas_sel)
                    st.success("Permissões atualizadas!")
                    st.rerun()
            with col2:
                if st.button("🚫 Revogar acesso", key=f"rev_{u['id']}", use_container_width=True):
                    rejeitar_usuario(u["id"])
                    st.warning(f"Acesso de {u['nome']} revogado.")
                    st.rerun()
