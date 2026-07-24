import pandas as pd
import streamlit as st
from auth import require_login
from db import get_supabase

st.set_page_config(page_title="Controle de OS de Linhas - ARCE", layout="wide")

user = require_login()
sb = get_supabase()

st.title("Controle de OS de Linhas — ARCE")


def listar(tabela: str, order: str = "id") -> pd.DataFrame:
    res = sb.table(tabela).select("*").order(order).execute()
    return pd.DataFrame(res.data)


tab_sistemas, tab_lotes, tab_operadores, tab_normas, tab_linhas = st.tabs(
    ["Sistemas", "Lotes", "Operadores", "Normas", "Linhas"]
)

with tab_sistemas:
    st.subheader("Sistemas")
    st.dataframe(listar("sistemas"), use_container_width=True, hide_index=True)
    with st.form("novo_sistema", clear_on_submit=True):
        nome = st.text_input("Nome do sistema")
        if st.form_submit_button("Adicionar") and nome.strip():
            sb.table("sistemas").insert({"nome": nome.strip()}).execute()
            st.rerun()

with tab_lotes:
    st.subheader("Lotes")
    sistemas_df = listar("sistemas")
    lotes_df = listar("lotes")
    if not lotes_df.empty and not sistemas_df.empty:
        exibicao = lotes_df.merge(
            sistemas_df[["id", "nome"]].rename(columns={"nome": "sistema"}),
            left_on="sistema_id", right_on="id", suffixes=("", "_sis"),
        )[["id", "nome", "sistema"]]
    else:
        exibicao = lotes_df
    st.dataframe(exibicao, use_container_width=True, hide_index=True)

    with st.form("novo_lote", clear_on_submit=True):
        if sistemas_df.empty:
            st.warning("Cadastre um sistema primeiro.")
            st.form_submit_button("Adicionar", disabled=True)
        else:
            sistema_escolhido = st.selectbox("Sistema", sistemas_df["nome"])
            nome = st.text_input("Nome do lote")
            if st.form_submit_button("Adicionar") and nome.strip():
                sistema_id = int(
                    sistemas_df.loc[sistemas_df["nome"] == sistema_escolhido, "id"].iloc[0]
                )
                sb.table("lotes").insert({"sistema_id": sistema_id, "nome": nome.strip()}).execute()
                st.rerun()

with tab_operadores:
    st.subheader("Operadores")
    st.dataframe(listar("operadores"), use_container_width=True, hide_index=True)
    with st.form("novo_operador", clear_on_submit=True):
        nome = st.text_input("Nome do operador")
        cnpj = st.text_input("CNPJ (opcional)")
        if st.form_submit_button("Adicionar") and nome.strip():
            sb.table("operadores").insert(
                {"nome": nome.strip(), "cnpj": cnpj.strip() or None}
            ).execute()
            st.rerun()

with tab_normas:
    st.subheader("Normas")
    st.dataframe(listar("normas"), use_container_width=True, hide_index=True)
    with st.form("nova_norma", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["OS", "Portaria", "Resolução", "Outro"])
        numero = st.text_input("Número")
        data_publicacao = st.date_input("Data de publicação", value=None)
        descricao = st.text_area("Descrição")
        if st.form_submit_button("Adicionar") and numero.strip():
            sb.table("normas").insert(
                {
                    "tipo": tipo,
                    "numero": numero.strip(),
                    "data_publicacao": str(data_publicacao) if data_publicacao else None,
                    "descricao": descricao.strip() or None,
                }
            ).execute()
            st.rerun()

with tab_linhas:
    st.subheader("Linhas")
    sistemas_df = listar("sistemas")
    lotes_df = listar("lotes")
    operadores_df = listar("operadores")
    st.dataframe(listar("linhas", order="codigo"), use_container_width=True, hide_index=True)

    with st.form("nova_linha", clear_on_submit=True):
        codigo = st.text_input("Código")
        nome = st.text_input("Nome da linha")
        especie = st.text_input("Espécie de serviço")
        tipo_linha = st.selectbox("Tipo da linha", ["Radial", "Regional", "Outro"])

        sistema_escolhido = st.selectbox(
            "Sistema", sistemas_df["nome"] if not sistemas_df.empty else []
        )
        sistema_id = None
        lotes_do_sistema = pd.DataFrame()
        if sistema_escolhido:
            sistema_id = int(sistemas_df.loc[sistemas_df["nome"] == sistema_escolhido, "id"].iloc[0])
            if not lotes_df.empty:
                lotes_do_sistema = lotes_df[lotes_df["sistema_id"] == sistema_id]

        lote_escolhido = st.selectbox(
            "Lote", lotes_do_sistema["nome"] if not lotes_do_sistema.empty else []
        )
        operador_escolhido = st.selectbox(
            "Operador", operadores_df["nome"] if not operadores_df.empty else []
        )

        if st.form_submit_button("Adicionar") and codigo.strip() and nome.strip():
            lote_id = (
                int(lotes_do_sistema.loc[lotes_do_sistema["nome"] == lote_escolhido, "id"].iloc[0])
                if lote_escolhido else None
            )
            operador_id = (
                int(operadores_df.loc[operadores_df["nome"] == operador_escolhido, "id"].iloc[0])
                if operador_escolhido else None
            )
            sb.table("linhas").insert(
                {
                    "codigo": codigo.strip(),
                    "nome": nome.strip(),
                    "especie_servico": especie.strip() or None,
                    "tipo_linha": tipo_linha,
                    "sistema_id": sistema_id,
                    "lote_id": lote_id,
                    "operador_id": operador_id,
                }
            ).execute()
            st.rerun()
