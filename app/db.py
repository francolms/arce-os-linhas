import os

import streamlit as st
from supabase import Client, create_client


def _setting(name: str) -> str | None:
    value = None
    try:
        if name in st.secrets:
            value = st.secrets[name]
    except Exception:
        pass
    if value is None:
        value = os.environ.get(name)
    return value.strip() if isinstance(value, str) else value


@st.cache_resource
def get_supabase() -> Client:
    url = _setting("SUPABASE_URL")
    key = _setting("SUPABASE_KEY")
    if not url or not key:
        st.error(
            "Configuração ausente: defina SUPABASE_URL e SUPABASE_KEY "
            "(em Settings > Secrets no Streamlit Cloud, ou em um .env local)."
        )
        st.stop()
    if not url.startswith("http"):
        st.error(
            f"SUPABASE_URL inválida: começa com '{url[:12]}...', mas precisa "
            "começar com https://. Copie o valor exato em Supabase > "
            "Settings > API > Project URL e cole entre aspas nos Secrets."
        )
        st.stop()
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Falha ao conectar ao Supabase: {e}")
        st.stop()
