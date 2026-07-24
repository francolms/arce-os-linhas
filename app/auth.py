import streamlit as st

from db import get_supabase


def _sync_usuario(sb, user) -> str:
    existing = sb.table("usuarios").select("id, perfil").eq("email", user.email).execute()
    if existing.data:
        return existing.data[0]["perfil"]
    sb.table("usuarios").insert(
        {"nome": user.email.split("@")[0], "email": user.email}
    ).execute()
    return "editor"


def is_admin() -> bool:
    return st.session_state.get("perfil") == "administrador"


def require_login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user:
        with st.sidebar:
            st.caption(f"Logado como {st.session_state.user.email} ({st.session_state.perfil})")
            if st.button("Sair"):
                get_supabase().auth.sign_out()
                st.session_state.user = None
                st.rerun()
        return st.session_state.user

    st.title("Sistema de Controle de OS de Linhas — ARCE")
    with st.form("login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        sb = get_supabase()
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": senha})
            st.session_state.perfil = _sync_usuario(sb, res.user)
            st.session_state.user = res.user
            st.rerun()
        except Exception:
            st.error("E-mail ou senha inválidos.")

    st.stop()
