import os

import streamlit as st
from supabase import Client, create_client


def _setting(name: str) -> str | None:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


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
    return create_client(url, key)
