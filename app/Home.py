import pandas as pd
import streamlit as st
from auth import is_admin, require_login
from db import get_supabase

st.set_page_config(page_title="Controle de OS de Linhas - ARCE", layout="wide")

user = require_login()
sb = get_supabase()
admin = is_admin()

st.title("Controle de OS de Linhas — ARCE")


def listar(tabela: str, order: str = "id") -> pd.DataFrame:
    res = sb.table(tabela).select("*").order(order).execute()
    return pd.DataFrame(res.data)


def tabela_simples(tabela: str, titulo: str):
    """CRUD genérico para tabelas de 1 coluna (nome), gerenciável só por admin."""
    st.subheader(titulo)
    df = listar(tabela, order="nome")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not admin:
        st.caption("Apenas administradores podem incluir, editar ou excluir.")
        return

    col_novo, col_editar = st.columns(2)

    with col_novo:
        st.markdown("**Adicionar**")
        with st.form(f"novo_{tabela}", clear_on_submit=True):
            nome = st.text_input("Nome", key=f"novo_nome_{tabela}")
            if st.form_submit_button("Adicionar") and nome.strip():
                sb.table(tabela).insert({"nome": nome.strip()}).execute()
                st.rerun()

    with col_editar:
        st.markdown("**Editar / excluir**")
        if df.empty:
            st.caption("Nada cadastrado ainda.")
            return
        item = st.selectbox("Item", df["nome"], key=f"sel_{tabela}")
        item_id = int(df.loc[df["nome"] == item, "id"].iloc[0])
        novo_nome = st.text_input("Novo nome", value=item, key=f"edit_nome_{tabela}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Salvar", key=f"salvar_{tabela}"):
                sb.table(tabela).update({"nome": novo_nome.strip()}).eq("id", item_id).execute()
                st.rerun()
        with c2:
            confirmar = st.checkbox("Confirmo exclusão", key=f"conf_{tabela}")
            if st.button("Excluir", key=f"excluir_{tabela}", disabled=not confirmar):
                sb.table(tabela).delete().eq("id", item_id).execute()
                st.rerun()


(
    tab_sistemas, tab_lotes, tab_operadores, tab_tipos, tab_especies,
    tab_normas, tab_linhas,
) = st.tabs(
    ["Sistemas", "Lotes", "Operadores", "Tipos de Linha", "Espécies de Serviço",
     "Normas", "Linhas"]
)

with tab_sistemas:
    tabela_simples("sistemas", "Sistemas")

with tab_operadores:
    tabela_simples("operadores", "Operadores")

with tab_tipos:
    tabela_simples("tipos_linha", "Tipos de Linha")

with tab_especies:
    tabela_simples("especies_servico", "Espécies de Serviço")

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

    if not admin:
        st.caption("Apenas administradores podem incluir, editar ou excluir.")
    elif sistemas_df.empty:
        st.warning("Cadastre um sistema primeiro.")
    else:
        col_novo, col_editar = st.columns(2)

        with col_novo:
            st.markdown("**Adicionar**")
            sistema_escolhido = st.selectbox("Sistema", sistemas_df["nome"], key="lote_novo_sistema")
            with st.form("novo_lote", clear_on_submit=True):
                nome = st.text_input("Nome do lote")
                if st.form_submit_button("Adicionar") and nome.strip():
                    sistema_id = int(sistemas_df.loc[sistemas_df["nome"] == sistema_escolhido, "id"].iloc[0])
                    sb.table("lotes").insert({"sistema_id": sistema_id, "nome": nome.strip()}).execute()
                    st.rerun()

        with col_editar:
            st.markdown("**Editar / excluir**")
            if lotes_df.empty:
                st.caption("Nada cadastrado ainda.")
            else:
                item = st.selectbox("Lote", lotes_df["nome"], key="lote_sel")
                item_id = int(lotes_df.loc[lotes_df["nome"] == item, "id"].iloc[0])
                novo_nome = st.text_input("Novo nome", value=item, key="lote_edit_nome")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Salvar", key="lote_salvar"):
                        sb.table("lotes").update({"nome": novo_nome.strip()}).eq("id", item_id).execute()
                        st.rerun()
                with c2:
                    confirmar = st.checkbox("Confirmo exclusão", key="lote_conf")
                    if st.button("Excluir", key="lote_excluir", disabled=not confirmar):
                        sb.table("lotes").delete().eq("id", item_id).execute()
                        st.rerun()

with tab_normas:
    st.subheader("Normas")
    normas_df = listar("normas")
    st.dataframe(normas_df, use_container_width=True, hide_index=True)

    st.markdown("**Adicionar**")
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

    if admin and not normas_df.empty:
        st.markdown("**Excluir**")
        rotulo = normas_df.apply(lambda r: f"{r['tipo']} nº {r['numero']}", axis=1)
        escolha = st.selectbox("Norma", rotulo, key="norma_sel")
        item_id = int(normas_df.loc[rotulo == escolha, "id"].iloc[0])
        confirmar = st.checkbox("Confirmo exclusão", key="norma_conf")
        if st.button("Excluir", key="norma_excluir", disabled=not confirmar):
            sb.table("normas").delete().eq("id", item_id).execute()
            st.rerun()
    elif not admin:
        st.caption("Apenas administradores podem excluir normas.")

with tab_linhas:
    st.subheader("Linhas")
    sistemas_df = listar("sistemas")
    lotes_df = listar("lotes")
    operadores_df = listar("operadores")
    tipos_df = listar("tipos_linha", order="nome")
    especies_df = listar("especies_servico", order="nome")
    linhas_df = listar("linhas", order="codigo")
    st.dataframe(linhas_df, use_container_width=True, hide_index=True)

    def _id_por_nome(df: pd.DataFrame, nome_escolhido):
        if df.empty or not nome_escolhido:
            return None
        return int(df.loc[df["nome"] == nome_escolhido, "id"].iloc[0])

    if admin:
        st.markdown("**Adicionar linha** (inclusão é restrita a administradores)")
        # Fora do form: precisa recalcular os Lotes assim que o Sistema muda.
        sistema_escolhido = st.selectbox(
            "Sistema", sistemas_df["nome"] if not sistemas_df.empty else [], key="linha_novo_sistema"
        )
        sistema_id = _id_por_nome(sistemas_df, sistema_escolhido)
        lotes_do_sistema = (
            lotes_df[lotes_df["sistema_id"] == sistema_id] if sistema_id and not lotes_df.empty else pd.DataFrame()
        )

        with st.form("nova_linha", clear_on_submit=True):
            codigo = st.text_input("Código")
            nome = st.text_input("Nome da linha")
            tipo_escolhido = st.selectbox("Tipo da linha", tipos_df["nome"] if not tipos_df.empty else [])
            especie_escolhida = st.selectbox("Espécie de serviço", especies_df["nome"] if not especies_df.empty else [])
            lote_escolhido = st.selectbox("Lote", lotes_do_sistema["nome"] if not lotes_do_sistema.empty else [])
            operador_escolhido = st.selectbox("Operador", operadores_df["nome"] if not operadores_df.empty else [])

            if st.form_submit_button("Adicionar") and codigo.strip() and nome.strip():
                sb.table("linhas").insert(
                    {
                        "codigo": codigo.strip(),
                        "nome": nome.strip(),
                        "tipo_linha_id": _id_por_nome(tipos_df, tipo_escolhido),
                        "especie_servico_id": _id_por_nome(especies_df, especie_escolhida),
                        "sistema_id": sistema_id,
                        "lote_id": _id_por_nome(lotes_do_sistema, lote_escolhido),
                        "operador_id": _id_por_nome(operadores_df, operador_escolhido),
                    }
                ).execute()
                st.rerun()
    else:
        st.caption("Inclusão de linhas é restrita a administradores.")

    st.divider()
    st.markdown("**Editar características de uma linha**")
    if linhas_df.empty:
        st.caption("Nenhuma linha cadastrada ainda.")
    else:
        codigo_escolhido = st.selectbox("Código da linha", linhas_df["codigo"], key="linha_edit_sel")
        linha_atual = linhas_df.loc[linhas_df["codigo"] == codigo_escolhido].iloc[0]

        sistema_edit = st.selectbox(
            "Sistema", sistemas_df["nome"] if not sistemas_df.empty else [],
            index=int(sistemas_df.index[sistemas_df["id"] == linha_atual["sistema_id"]][0])
            if not sistemas_df.empty and (sistemas_df["id"] == linha_atual["sistema_id"]).any() else 0,
            key="linha_edit_sistema",
        )
        sistema_edit_id = _id_por_nome(sistemas_df, sistema_edit)
        lotes_do_sistema_edit = (
            lotes_df[lotes_df["sistema_id"] == sistema_edit_id]
            if sistema_edit_id and not lotes_df.empty else pd.DataFrame()
        )

        with st.form("editar_linha"):
            nome_edit = st.text_input("Nome da linha", value=linha_atual["nome"])
            tipo_edit = st.selectbox(
                "Tipo da linha", tipos_df["nome"] if not tipos_df.empty else [],
                index=int(tipos_df.index[tipos_df["id"] == linha_atual["tipo_linha_id"]][0])
                if not tipos_df.empty and (tipos_df["id"] == linha_atual["tipo_linha_id"]).any() else 0,
            )
            especie_edit = st.selectbox(
                "Espécie de serviço", especies_df["nome"] if not especies_df.empty else [],
                index=int(especies_df.index[especies_df["id"] == linha_atual["especie_servico_id"]][0])
                if not especies_df.empty and (especies_df["id"] == linha_atual["especie_servico_id"]).any() else 0,
            )
            lote_edit = st.selectbox("Lote", lotes_do_sistema_edit["nome"] if not lotes_do_sistema_edit.empty else [])
            operador_edit = st.selectbox(
                "Operador", operadores_df["nome"] if not operadores_df.empty else [],
                index=int(operadores_df.index[operadores_df["id"] == linha_atual["operador_id"]][0])
                if not operadores_df.empty and (operadores_df["id"] == linha_atual["operador_id"]).any() else 0,
            )

            if st.form_submit_button("Salvar alterações"):
                sb.table("linhas").update(
                    {
                        "nome": nome_edit.strip(),
                        "tipo_linha_id": _id_por_nome(tipos_df, tipo_edit),
                        "especie_servico_id": _id_por_nome(especies_df, especie_edit),
                        "sistema_id": sistema_edit_id,
                        "lote_id": _id_por_nome(lotes_do_sistema_edit, lote_edit),
                        "operador_id": _id_por_nome(operadores_df, operador_edit),
                    }
                ).eq("codigo", codigo_escolhido).execute()
                st.rerun()

        if admin:
            confirmar = st.checkbox("Confirmo exclusão desta linha", key="linha_conf_exclusao")
            if st.button("Excluir linha", disabled=not confirmar):
                sb.table("linhas").delete().eq("codigo", codigo_escolhido).execute()
                st.rerun()
