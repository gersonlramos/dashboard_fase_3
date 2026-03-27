"""Cliente Supabase compartilhado."""
import os
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas. "
            "Adicione em .streamlit/secrets.toml ou nas variáveis de ambiente."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)
