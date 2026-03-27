import os
import sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from auth import cadastrar_usuario

st.title("📝 Solicitar Acesso")
st.markdown("Preencha o formulário abaixo. Seu acesso será liberado após aprovação do administrador.")
st.markdown("---")

with st.form("form_cadastro"):
    nome     = st.text_input("Nome completo")
    username = st.text_input("Nome de usuário (sem espaços)")
    email    = st.text_input("E-mail")
    senha    = st.text_input("Senha", type="password")
    confirma = st.text_input("Confirmar senha", type="password")
    enviar   = st.form_submit_button("Solicitar acesso", use_container_width=True)

if enviar:
    if not all([nome, username, email, senha, confirma]):
        st.error("Preencha todos os campos.")
    elif senha != confirma:
        st.error("As senhas não coincidem.")
    elif len(senha) < 6:
        st.error("A senha deve ter pelo menos 6 caracteres.")
    elif " " in username:
        st.error("O nome de usuário não pode ter espaços.")
    else:
        ok, msg = cadastrar_usuario(nome.strip(), username.strip().lower(), email.strip().lower(), senha)
        if ok:
            st.success(msg)
        else:
            st.error(msg)
