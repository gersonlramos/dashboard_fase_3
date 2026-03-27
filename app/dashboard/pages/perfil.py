import os
import sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from auth import alterar_senha

st.title("👤 Meu Perfil")
st.markdown(f"**Usuário:** `{st.session_state['username']}`")
st.markdown(f"**Nome:** {st.session_state['name']}")
st.markdown("---")
st.subheader("🔑 Alterar Senha")

with st.form("form_alterar_senha"):
    senha_atual = st.text_input("Senha atual", type="password")
    nova_senha  = st.text_input("Nova senha", type="password")
    confirma    = st.text_input("Confirmar nova senha", type="password")
    salvar      = st.form_submit_button("Salvar", use_container_width=True)

if salvar:
    if not all([senha_atual, nova_senha, confirma]):
        st.error("Preencha todos os campos.")
    elif nova_senha != confirma:
        st.error("A nova senha e a confirmação não coincidem.")
    elif len(nova_senha) < 6:
        st.error("A nova senha deve ter pelo menos 6 caracteres.")
    else:
        ok, msg = alterar_senha(st.session_state["username"], senha_atual, nova_senha)
        if ok:
            st.success(f"✅ {msg}")
        else:
            st.error(msg)
