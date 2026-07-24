import pandas as pd
import streamlit as st
from auth import is_admin, require_login
from db import get_supabase
from postgrest.exceptions import APIError

st.set_page_config(page_title="Controle de OS de Linhas - ARCE", layout="wide")

user = require_login()
sb = get_supabase()
admin = is_admin()

col_titulo, col_atualizar = st.columns([6, 1])
col_titulo.title("Controle de OS de Linhas — ARCE")
with col_atualizar:
    st.write("")
    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()
        st.rerun()

FK_MSG = (
    "Não é possível concluir: este item está vinculado a outro cadastro "
    "(Lote, Linha ou Norma). Ajuste esses vínculos antes de excluir."
)


# Consultas em cache: o banco só é consultado de novo após uma gravação
# (recarregar() limpa o cache) ou pelo botão "Atualizar dados".
@st.cache_data(ttl=300, show_spinner=False)
def listar(tabela: str, order: str = "id") -> pd.DataFrame:
    res = get_supabase().table(tabela).select("*").order(order).execute()
    return pd.DataFrame(res.data)


def recarregar():
    st.cache_data.clear()
    st.rerun()


def _id_por_nome(df: pd.DataFrame, nome_escolhido):
    if df.empty or not nome_escolhido:
        return None
    achado = df.loc[df["nome"] == nome_escolhido, "id"]
    return int(achado.iloc[0]) if not achado.empty else None


def _nome_por_id(df: pd.DataFrame, id_valor):
    if df.empty or pd.isna(id_valor):
        return "—"
    achado = df.loc[df["id"] == id_valor, "nome"]
    return achado.iloc[0] if not achado.empty else "—"


def _index_atual(df: pd.DataFrame, id_valor) -> int:
    if df.empty or pd.isna(id_valor):
        return 0
    achado = df.index[df["id"] == id_valor]
    return int(achado[0]) if len(achado) else 0


def executar(fn, msg_erro: str | None = None) -> bool:
    try:
        fn()
        return True
    except APIError as e:
        if getattr(e, "code", None) == "23503":
            st.error(msg_erro or FK_MSG)
        else:
            st.error(f"Erro ao salvar: {getattr(e, 'message', e)}")
        return False


def selecionar_linha_df(df_exibicao: pd.DataFrame, key: str):
    """Tabela com seleção de 1 linha; devolve a posição selecionada ou None."""
    evento = st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )
    linhas_sel = evento.selection.rows
    return linhas_sel[0] if linhas_sel else None


# ============================================================================
# Tabelas simples (só "nome"): Sistemas, Tipos de Linha, Espécies de Serviço
# ============================================================================

@st.dialog("Adicionar")
def dlg_add_simples(tabela: str):
    nome = st.text_input("Nome")
    if st.button("Adicionar", key=f"cf_add_{tabela}"):
        if not nome.strip():
            st.warning("Informe um nome.")
        elif executar(lambda: sb.table(tabela).insert({"nome": nome.strip()}).execute()):
            recarregar()


@st.dialog("Editar")
def dlg_edit_simples(tabela: str, row):
    nome = st.text_input("Nome", value=row["nome"])
    c1, c2 = st.columns(2)
    if c1.button("Salvar", key=f"cf_edit_{tabela}_{row['id']}"):
        if executar(lambda: sb.table(tabela).update({"nome": nome.strip()}).eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_edit_{tabela}_{row['id']}"):
        st.rerun()


@st.dialog("Excluir")
def dlg_del_simples(tabela: str, row):
    st.warning(f"Excluir **{row['nome']}**? Essa ação não pode ser desfeita.")
    c1, c2 = st.columns(2)
    if c1.button("Confirmar exclusão", key=f"cf_del_{tabela}_{row['id']}"):
        if executar(lambda: sb.table(tabela).delete().eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_del_{tabela}_{row['id']}"):
        st.rerun()


def tabela_simples(tabela: str, titulo: str):
    st.subheader(titulo)
    df = listar(tabela, order="nome")

    if df.empty:
        st.caption("Nada cadastrado ainda.")
        pos = None
    else:
        pos = selecionar_linha_df(df[["nome"]].rename(columns={"nome": "Nome"}), f"df_{tabela}")

    if admin:
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("+ Adicionar", key=f"abrir_add_{tabela}"):
            dlg_add_simples(tabela)
        if c2.button("✏️ Editar", key=f"abrir_ed_{tabela}", disabled=pos is None):
            dlg_edit_simples(tabela, df.iloc[pos])
        if c3.button("❌ Excluir", key=f"abrir_del_{tabela}", disabled=pos is None):
            dlg_del_simples(tabela, df.iloc[pos])
        if pos is None and not df.empty:
            st.caption("Selecione uma linha da tabela para editar ou excluir.")
    else:
        st.caption("Apenas administradores podem incluir, editar ou excluir.")


# ============================================================================
# Operadores (nome + CNPJ opcional)
# ============================================================================

@st.dialog("Adicionar Operador")
def dlg_add_operador():
    nome = st.text_input("Nome do operador")
    cnpj = st.text_input("CNPJ (opcional)")
    if st.button("Adicionar", key="cf_add_operador"):
        if not nome.strip():
            st.warning("Informe um nome.")
        elif executar(lambda: sb.table("operadores").insert(
            {"nome": nome.strip(), "cnpj": cnpj.strip() or None}
        ).execute()):
            recarregar()


@st.dialog("Editar Operador")
def dlg_edit_operador(row):
    nome = st.text_input("Nome do operador", value=row["nome"])
    cnpj_atual = row["cnpj"] if pd.notna(row.get("cnpj")) else ""
    cnpj = st.text_input("CNPJ (opcional)", value=cnpj_atual)
    c1, c2 = st.columns(2)
    if c1.button("Salvar", key=f"cf_edit_operador_{row['id']}"):
        if executar(lambda: sb.table("operadores").update(
            {"nome": nome.strip(), "cnpj": cnpj.strip() or None}
        ).eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_edit_operador_{row['id']}"):
        st.rerun()


@st.dialog("Excluir Operador")
def dlg_del_operador(row):
    st.warning(f"Excluir o operador **{row['nome']}**? Essa ação não pode ser desfeita.")
    c1, c2 = st.columns(2)
    if c1.button("Confirmar exclusão", key=f"cf_del_operador_{row['id']}"):
        if executar(lambda: sb.table("operadores").delete().eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_del_operador_{row['id']}"):
        st.rerun()


# ============================================================================
# Lotes (nome + Sistema)
# ============================================================================

@st.dialog("Adicionar Lote")
def dlg_add_lote():
    sistemas_df = listar("sistemas")
    if sistemas_df.empty:
        st.warning("Cadastre um sistema primeiro.")
        return
    sistema = st.selectbox("Sistema", sistemas_df["nome"])
    nome = st.text_input("Nome do lote")
    if st.button("Adicionar", key="cf_add_lote"):
        if not nome.strip():
            st.warning("Informe um nome.")
        elif executar(lambda: sb.table("lotes").insert(
            {"sistema_id": _id_por_nome(sistemas_df, sistema), "nome": nome.strip()}
        ).execute()):
            recarregar()


@st.dialog("Editar Lote")
def dlg_edit_lote(row):
    sistemas_df = listar("sistemas")
    sistema = st.selectbox(
        "Sistema", sistemas_df["nome"] if not sistemas_df.empty else [],
        index=_index_atual(sistemas_df, row.get("sistema_id")),
    )
    nome = st.text_input("Nome do lote", value=row["nome"])
    c1, c2 = st.columns(2)
    if c1.button("Salvar", key=f"cf_edit_lote_{row['id']}"):
        if executar(lambda: sb.table("lotes").update(
            {"sistema_id": _id_por_nome(sistemas_df, sistema), "nome": nome.strip()}
        ).eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_edit_lote_{row['id']}"):
        st.rerun()


@st.dialog("Excluir Lote")
def dlg_del_lote(row):
    st.warning(f"Excluir o lote **{row['nome']}**? Essa ação não pode ser desfeita.")
    c1, c2 = st.columns(2)
    if c1.button("Confirmar exclusão", key=f"cf_del_lote_{row['id']}"):
        if executar(lambda: sb.table("lotes").delete().eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_del_lote_{row['id']}"):
        st.rerun()


# ============================================================================
# Normas
# ============================================================================

TIPOS_NORMA = ["OS", "Portaria", "Resolução", "Outro"]


@st.dialog("Adicionar Norma")
def dlg_add_norma():
    tipo = st.selectbox("Tipo", TIPOS_NORMA)
    numero = st.text_input("Número")
    data_publicacao = st.date_input("Data de publicação", value=None)
    descricao = st.text_area("Descrição")
    if st.button("Adicionar", key="cf_add_norma"):
        if not numero.strip():
            st.warning("Informe o número.")
        elif executar(lambda: sb.table("normas").insert({
            "tipo": tipo,
            "numero": numero.strip(),
            "data_publicacao": str(data_publicacao) if data_publicacao else None,
            "descricao": descricao.strip() or None,
        }).execute()):
            recarregar()


@st.dialog("Editar Norma")
def dlg_edit_norma(row):
    tipo = st.selectbox("Tipo", TIPOS_NORMA, index=TIPOS_NORMA.index(row["tipo"]) if row["tipo"] in TIPOS_NORMA else 0)
    numero = st.text_input("Número", value=row["numero"])
    data_atual = pd.to_datetime(row["data_publicacao"]).date() if pd.notna(row.get("data_publicacao")) else None
    data_publicacao = st.date_input("Data de publicação", value=data_atual)
    descricao_atual = row["descricao"] if pd.notna(row.get("descricao")) else ""
    descricao = st.text_area("Descrição", value=descricao_atual)
    c1, c2 = st.columns(2)
    if c1.button("Salvar", key=f"cf_edit_norma_{row['id']}"):
        if executar(lambda: sb.table("normas").update({
            "tipo": tipo,
            "numero": numero.strip(),
            "data_publicacao": str(data_publicacao) if data_publicacao else None,
            "descricao": descricao.strip() or None,
        }).eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_edit_norma_{row['id']}"):
        st.rerun()


@st.dialog("Excluir Norma")
def dlg_del_norma(row):
    st.warning(f"Excluir a norma **{row['tipo']} nº {row['numero']}**? Essa ação não pode ser desfeita.")
    c1, c2 = st.columns(2)
    if c1.button("Confirmar exclusão", key=f"cf_del_norma_{row['id']}"):
        if executar(lambda: sb.table("normas").delete().eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_del_norma_{row['id']}"):
        st.rerun()


# ============================================================================
# Linhas
# ============================================================================

def _campos_linha(valores=None):
    """Renderiza os campos do formulário de linha; devolve os valores escolhidos."""
    valores = valores or {}
    sistemas_df = listar("sistemas")
    lotes_df = listar("lotes")
    operadores_df = listar("operadores", order="nome")
    tipos_df = listar("tipos_linha", order="nome")
    especies_df = listar("especies_servico", order="nome")

    nome = st.text_input("Nome da linha", value=valores.get("nome", ""))
    tipo = st.selectbox(
        "Tipo da linha", tipos_df["nome"] if not tipos_df.empty else [],
        index=_index_atual(tipos_df, valores.get("tipo_linha_id")),
    )
    especie = st.selectbox(
        "Espécie de serviço", especies_df["nome"] if not especies_df.empty else [],
        index=_index_atual(especies_df, valores.get("especie_servico_id")),
    )
    sistema = st.selectbox(
        "Sistema", sistemas_df["nome"] if not sistemas_df.empty else [],
        index=_index_atual(sistemas_df, valores.get("sistema_id")),
    )
    sistema_id = _id_por_nome(sistemas_df, sistema)
    lotes_do_sistema = (
        lotes_df[lotes_df["sistema_id"] == sistema_id].reset_index(drop=True)
        if sistema_id and not lotes_df.empty else pd.DataFrame()
    )
    lote = st.selectbox(
        "Lote", lotes_do_sistema["nome"] if not lotes_do_sistema.empty else [],
        index=_index_atual(lotes_do_sistema, valores.get("lote_id")),
    )
    operador = st.selectbox(
        "Operador", operadores_df["nome"] if not operadores_df.empty else [],
        index=_index_atual(operadores_df, valores.get("operador_id")),
    )

    return {
        "nome": nome.strip(),
        "tipo_linha_id": _id_por_nome(tipos_df, tipo),
        "especie_servico_id": _id_por_nome(especies_df, especie),
        "sistema_id": sistema_id,
        "lote_id": _id_por_nome(lotes_do_sistema, lote),
        "operador_id": _id_por_nome(operadores_df, operador),
    }


@st.dialog("Adicionar Linha")
def dlg_add_linha():
    codigo = st.text_input("Código")
    dados = _campos_linha()
    if st.button("Adicionar", key="cf_add_linha"):
        if not codigo.strip() or not dados["nome"]:
            st.warning("Informe ao menos código e nome.")
        elif executar(lambda: sb.table("linhas").insert({"codigo": codigo.strip(), **dados}).execute()):
            recarregar()


@st.dialog("Editar Linha")
def dlg_edit_linha(row):
    st.caption(f"Código: {row['codigo']} (não editável)")
    dados = _campos_linha(row)
    c1, c2 = st.columns(2)
    if c1.button("Salvar", key=f"cf_edit_linha_{row['codigo']}"):
        if executar(lambda: sb.table("linhas").update(dados).eq("codigo", row["codigo"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_edit_linha_{row['codigo']}"):
        st.rerun()


@st.dialog("Excluir Linha")
def dlg_del_linha(row):
    st.warning(f"Excluir a linha **{row['codigo']} — {row['nome']}**? Essa ação não pode ser desfeita.")
    c1, c2 = st.columns(2)
    if c1.button("Confirmar exclusão", key=f"cf_del_linha_{row['codigo']}"):
        if executar(lambda: sb.table("linhas").delete().eq("codigo", row["codigo"]).execute()):
            recarregar()
    if c2.button("Cancelar", key=f"cc_del_linha_{row['codigo']}"):
        st.rerun()


# ============================================================================
# Abas
# ============================================================================

(
    tab_sistemas, tab_lotes, tab_operadores, tab_tipos, tab_especies,
    tab_normas, tab_linhas,
) = st.tabs(
    ["Sistemas", "Lotes", "Operadores", "Tipos de Linha", "Espécies de Serviço",
     "Normas", "Linhas"]
)

with tab_sistemas:
    tabela_simples("sistemas", "Sistemas")

with tab_tipos:
    tabela_simples("tipos_linha", "Tipos de Linha")

with tab_especies:
    tabela_simples("especies_servico", "Espécies de Serviço")

with tab_operadores:
    st.subheader("Operadores")
    df = listar("operadores", order="nome")
    if df.empty:
        st.caption("Nada cadastrado ainda.")
        pos = None
    else:
        exibicao = df[["nome", "cnpj"]].rename(columns={"nome": "Nome", "cnpj": "CNPJ"})
        pos = selecionar_linha_df(exibicao, "df_operadores")

    if admin:
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("+ Adicionar", key="abrir_add_operador"):
            dlg_add_operador()
        if c2.button("✏️ Editar", key="abrir_ed_operador", disabled=pos is None):
            dlg_edit_operador(df.iloc[pos])
        if c3.button("❌ Excluir", key="abrir_del_operador", disabled=pos is None):
            dlg_del_operador(df.iloc[pos])
        if pos is None and not df.empty:
            st.caption("Selecione uma linha da tabela para editar ou excluir.")
    else:
        st.caption("Apenas administradores podem incluir, editar ou excluir.")

with tab_lotes:
    st.subheader("Lotes")
    sistemas_df = listar("sistemas")
    lotes_df = listar("lotes")
    if lotes_df.empty:
        st.caption("Nada cadastrado ainda.")
        pos = None
    else:
        exibicao = lotes_df.copy()
        exibicao["Sistema"] = exibicao["sistema_id"].map(
            lambda i: _nome_por_id(sistemas_df, i)
        )
        exibicao = exibicao[["nome", "Sistema"]].rename(columns={"nome": "Nome"})
        pos = selecionar_linha_df(exibicao, "df_lotes")

    if admin:
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("+ Adicionar", key="abrir_add_lote"):
            dlg_add_lote()
        if c2.button("✏️ Editar", key="abrir_ed_lote", disabled=pos is None):
            dlg_edit_lote(lotes_df.iloc[pos])
        if c3.button("❌ Excluir", key="abrir_del_lote", disabled=pos is None):
            dlg_del_lote(lotes_df.iloc[pos])
        if pos is None and not lotes_df.empty:
            st.caption("Selecione uma linha da tabela para editar ou excluir.")
    else:
        st.caption("Apenas administradores podem incluir, editar ou excluir.")

with tab_normas:
    st.subheader("Normas")
    normas_df = listar("normas")
    if normas_df.empty:
        st.caption("Nada cadastrado ainda.")
        pos = None
    else:
        exibicao = normas_df[["tipo", "numero", "data_publicacao", "descricao"]].rename(
            columns={"tipo": "Tipo", "numero": "Número",
                     "data_publicacao": "Data", "descricao": "Descrição"}
        )
        pos = selecionar_linha_df(exibicao, "df_normas")

    c1, c2, c3 = st.columns([1, 1, 1])
    if c1.button("+ Adicionar", key="abrir_add_norma"):
        dlg_add_norma()
    if c2.button("✏️ Editar", key="abrir_ed_norma", disabled=pos is None):
        dlg_edit_norma(normas_df.iloc[pos])
    if admin:
        if c3.button("❌ Excluir", key="abrir_del_norma", disabled=pos is None):
            dlg_del_norma(normas_df.iloc[pos])
    else:
        c3.caption("Exclusão: só administradores.")
    if pos is None and not normas_df.empty:
        st.caption("Selecione uma linha da tabela para editar ou excluir.")

with tab_linhas:
    st.subheader("Linhas")

    sistemas_df = listar("sistemas")
    lotes_df = listar("lotes")
    operadores_df = listar("operadores", order="nome")
    tipos_df = listar("tipos_linha")
    especies_df = listar("especies_servico")
    linhas_df = listar("linhas", order="codigo")

    if linhas_df.empty:
        st.caption("Nenhuma linha cadastrada ainda.")
        pos = None
        filtradas = linhas_df
    else:
        # Filtros para achar a linha sem rolar 650 registros
        f1, f2, f3 = st.columns([2, 2, 2])
        busca = f1.text_input("Buscar por código ou nome", key="linhas_busca")
        sistema_filtro = f2.selectbox(
            "Sistema", ["(Todos)"] + sistemas_df["nome"].tolist(), key="linhas_f_sistema"
        )
        operador_filtro = f3.selectbox(
            "Operador", ["(Todos)"] + operadores_df["nome"].tolist(), key="linhas_f_operador"
        )

        filtradas = linhas_df
        if busca.strip():
            termo = busca.strip().lower()
            filtradas = filtradas[
                filtradas["codigo"].str.lower().str.contains(termo, na=False)
                | filtradas["nome"].str.lower().str.contains(termo, na=False)
            ]
        if sistema_filtro != "(Todos)":
            filtradas = filtradas[filtradas["sistema_id"] == _id_por_nome(sistemas_df, sistema_filtro)]
        if operador_filtro != "(Todos)":
            filtradas = filtradas[filtradas["operador_id"] == _id_por_nome(operadores_df, operador_filtro)]
        filtradas = filtradas.reset_index(drop=True)

        exibicao = filtradas.copy()
        exibicao["Tipo"] = exibicao["tipo_linha_id"].map(lambda i: _nome_por_id(tipos_df, i))
        exibicao["Espécie"] = exibicao["especie_servico_id"].map(lambda i: _nome_por_id(especies_df, i))
        exibicao["Sistema"] = exibicao["sistema_id"].map(lambda i: _nome_por_id(sistemas_df, i))
        exibicao["Lote"] = exibicao["lote_id"].map(lambda i: _nome_por_id(lotes_df, i))
        exibicao["Operador"] = exibicao["operador_id"].map(lambda i: _nome_por_id(operadores_df, i))
        exibicao = exibicao[["codigo", "nome", "Tipo", "Espécie", "Sistema", "Lote", "Operador"]].rename(
            columns={"codigo": "Código", "nome": "Nome"}
        )
        st.caption(f"{len(filtradas)} de {len(linhas_df)} linhas")
        pos = selecionar_linha_df(exibicao, "df_linhas")

    c1, c2, c3 = st.columns([1, 1, 1])
    if admin:
        if c1.button("+ Adicionar", key="abrir_add_linha"):
            dlg_add_linha()
    else:
        c1.caption("Inclusão: só administradores.")
    if c2.button("✏️ Editar", key="abrir_ed_linha", disabled=pos is None):
        dlg_edit_linha(filtradas.iloc[pos])
    if admin:
        if c3.button("❌ Excluir", key="abrir_del_linha", disabled=pos is None):
            dlg_del_linha(filtradas.iloc[pos])
    else:
        c3.caption("Exclusão: só administradores.")
    if pos is None and not linhas_df.empty:
        st.caption("Selecione uma linha da tabela para editar ou excluir.")
