from datetime import datetime, timezone

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


@st.cache_data(ttl=300, show_spinner=False)
def listar_por_linha(tabela: str, linha_codigo: str, order: str = "id") -> pd.DataFrame:
    res = (
        get_supabase().table(tabela).select("*")
        .eq("linha_codigo", linha_codigo).order(order).execute()
    )
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


def executar(fn, msg_erro: str | None = None, msg_duplicado: str | None = None) -> bool:
    try:
        fn()
        return True
    except APIError as e:
        codigo_erro = getattr(e, "code", None)
        if codigo_erro == "23503":
            st.error(msg_erro or FK_MSG)
        elif codigo_erro == "23505":
            st.error(msg_duplicado or "Já existe um registro com esses dados.")
        else:
            st.error(f"Erro ao salvar: {getattr(e, 'message', e)}")
        return False


def usuario_atual_id() -> int:
    usuarios_df = listar("usuarios")
    achado = usuarios_df.loc[usuarios_df["email"] == user.email, "id"]
    return int(achado.iloc[0])


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


TIPOS_NORMA = ["OS", "Portaria", "Resolução", "Outro"]


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


@st.dialog("Estrutura da Linha")
def dlg_ver_estrutura_linha(row):
    codigo_linha = row["codigo"]
    st.write(f"**{codigo_linha} — {row['nome']}**")

    secoes_df = listar_por_linha("secoes", codigo_linha, order="ordem")
    st.subheader("Seções")
    if secoes_df.empty:
        st.caption("Nenhuma seção cadastrada ainda (crie uma OS de Seccionamento).")
    else:
        exibicao = secoes_df[["ordem", "nome", "tipo_ponto", "km_acumulado"]].rename(
            columns={"ordem": "Ordem", "nome": "Nome", "tipo_ponto": "Tipo", "km_acumulado": "Km acumulado"}
        )
        st.dataframe(exibicao, hide_index=True, use_container_width=True)
        extensao = _extensao_total(secoes_df)
        st.caption(f"Extensão total: {extensao} km" if extensao is not None else "Extensão: —")

    st.subheader("Tarifas")
    tarifas_df = listar_por_linha("tarifas", codigo_linha)
    if tarifas_df.empty or secoes_df.empty:
        st.caption("Nenhuma tarifa cadastrada ainda (crie uma OS de Tarifa).")
    else:
        mapa_nome = secoes_df.set_index("id")["nome"]
        tarifas_df = tarifas_df.copy()
        tarifas_df["Origem"] = tarifas_df["secao_origem_id"].map(mapa_nome)
        tarifas_df["Destino"] = tarifas_df["secao_destino_id"].map(mapa_nome)
        pivot = tarifas_df.pivot(index="Origem", columns="Destino", values="valor")
        ordem_nomes = secoes_df.sort_values("ordem")["nome"].tolist()
        pivot = pivot.reindex(
            index=[n for n in ordem_nomes if n in pivot.index],
            columns=[n for n in ordem_nomes if n in pivot.columns],
        )
        st.dataframe(pivot, use_container_width=True)

    st.subheader("Horários")
    horarios_df = listar_por_linha("horarios", codigo_linha)
    if horarios_df.empty:
        st.caption("Nenhum horário cadastrado ainda (crie uma OS de Horário).")
    else:
        for sentido, titulo in [("ida", "Ida"), ("volta", "Volta")]:
            sub = horarios_df[horarios_df["sentido"] == sentido]
            if sub.empty:
                continue
            st.markdown(f"**{titulo}**")
            exibicao = sub[["horario_saida"] + DIAS_SEMANA].rename(
                columns={"horario_saida": "Saída", **DIAS_SEMANA_LABEL}
            ).sort_values("Saída")
            st.dataframe(exibicao, hide_index=True, use_container_width=True)
            st.caption(f"Frequência semanal ({titulo}): {_frequencia_semanal(horarios_df, sentido=sentido)} viagens")
        st.caption(f"**Frequência semanal total: {_frequencia_semanal(horarios_df)} viagens**")

    if st.button("Fechar", key=f"fechar_estrutura_{codigo_linha}"):
        st.rerun()


# ============================================================================
# Alterações (fluxo de aprovação)
# ============================================================================

STATUS_LABEL = {
    "rascunho": "Rascunho",
    "enviada_aprovacao": "Enviada para aprovação",
    "aprovada_aguardando_norma": "Aprovada (aguardando norma)",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
TIPO_ALTERACAO_LABEL = {
    "inclusao": "Inclusão de linha",
    "exclusao": "Exclusão de linha",
    "cadastral": "Alteração cadastral",
    "seccionamento": "Seccionamento (pontos/extensão)",
    "tarifa": "Tarifa",
    "horario": "Horário (e frequência)",
    "itinerario": "Itinerário",
}
CAMPOS_CADASTRAIS = {
    "Nome": "nome",
    "Tipo de Linha": "tipo_linha_id",
    "Espécie de Serviço": "especie_servico_id",
    "Sistema": "sistema_id",
    "Lote": "lote_id",
    "Operador": "operador_id",
}


def _linha_tem_alteracao_aberta(linha_codigo: str) -> bool:
    alteracoes_df = listar("alteracoes")
    if alteracoes_df.empty:
        return False
    abertas = alteracoes_df[
        (alteracoes_df["linha_codigo"] == linha_codigo)
        & (~alteracoes_df["status"].isin(["concluida", "cancelada"]))
    ]
    return not abertas.empty


def _extensao_total(secoes_df: pd.DataFrame):
    if secoes_df.empty:
        return None
    ultima = secoes_df.sort_values("ordem").iloc[-1]
    return ultima.get("km_acumulado")


DIAS_SEMANA = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
DIAS_SEMANA_LABEL = {
    "segunda": "SEG", "terca": "TER", "quarta": "QUA", "quinta": "QUI",
    "sexta": "SEX", "sabado": "SAB", "domingo": "DOM",
}


def _frequencia_por_dia(horarios_df: pd.DataFrame, sentido: str | None = None) -> dict:
    df = horarios_df if sentido is None else horarios_df[horarios_df["sentido"] == sentido]
    if df.empty:
        return {dia: 0 for dia in DIAS_SEMANA}
    return {dia: int(df[dia].sum()) for dia in DIAS_SEMANA}


def _frequencia_semanal(horarios_df: pd.DataFrame, sentido: str | None = None) -> int:
    por_dia = _frequencia_por_dia(horarios_df, sentido)
    return sum(por_dia.values())


@st.dialog("Abrir OS")
def dlg_nova_alteracao():
    linhas_df = listar("linhas", order="codigo")
    if linhas_df.empty:
        st.warning("Nenhuma linha cadastrada.")
        return

    opcoes_linha = (linhas_df["codigo"] + " — " + linhas_df["nome"]).tolist()
    escolha_linha = st.selectbox("Linha", opcoes_linha)
    codigo_linha = escolha_linha.split(" — ")[0]
    linha_row = linhas_df.loc[linhas_df["codigo"] == codigo_linha].iloc[0]

    if _linha_tem_alteracao_aberta(codigo_linha):
        st.error(
            "Essa linha já tem uma alteração em andamento (não concluída/cancelada). "
            "Finalize ou cancele a anterior antes de abrir uma nova."
        )
        return

    tipo_label = st.selectbox("Tipo de alteração", list(TIPO_ALTERACAO_LABEL.values()))
    tipo_db = [k for k, v in TIPO_ALTERACAO_LABEL.items() if v == tipo_label][0]

    campo_db = None
    valor_anterior = None
    valor_novo = None

    if tipo_db == "cadastral":
        sistemas_df = listar("sistemas")
        lotes_df = listar("lotes")
        operadores_df = listar("operadores", order="nome")
        tipos_df = listar("tipos_linha", order="nome")
        especies_df = listar("especies_servico", order="nome")

        campo_label = st.selectbox("Campo a alterar", list(CAMPOS_CADASTRAIS.keys()))
        campo_db = CAMPOS_CADASTRAIS[campo_label]

        if campo_db == "nome":
            valor_anterior = linha_row["nome"]
            st.caption(f"Valor atual: {valor_anterior}")
            novo_texto = st.text_input("Novo nome")
            valor_novo = novo_texto.strip()
        else:
            opcoes_df = {
                "tipo_linha_id": tipos_df, "especie_servico_id": especies_df,
                "sistema_id": sistemas_df, "lote_id": lotes_df, "operador_id": operadores_df,
            }[campo_db]
            id_anterior = linha_row.get(campo_db)
            label_anterior = _nome_por_id(opcoes_df, id_anterior)
            st.caption(f"Valor atual: {label_anterior}")
            valor_anterior = {
                "id": int(id_anterior) if pd.notna(id_anterior) else None,
                "label": label_anterior,
            }
            escolha = st.selectbox("Novo valor", opcoes_df["nome"] if not opcoes_df.empty else [])
            valor_novo = {"id": _id_por_nome(opcoes_df, escolha), "label": escolha}
    elif tipo_db == "seccionamento":
        atuais = listar_por_linha("secoes", codigo_linha, order="ordem")
        st.caption(
            "Pontos da linha, na ordem do itinerário. Extensão = km acumulado do último ponto."
        )
        base_editor = (
            atuais[["nome", "tipo_ponto", "km_acumulado"]].reset_index(drop=True)
            if not atuais.empty
            else pd.DataFrame(columns=["nome", "tipo_ponto", "km_acumulado"])
        )
        editado = st.data_editor(
            base_editor,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "nome": st.column_config.TextColumn("Ponto"),
                "tipo_ponto": st.column_config.SelectboxColumn("Tipo", options=["parada", "passagem"]),
                "km_acumulado": st.column_config.NumberColumn("Km acumulado", min_value=0.0, step=0.1),
            },
            key=f"editor_secoes_{codigo_linha}",
        )
        valor_anterior = (
            atuais[["ordem", "nome", "tipo_ponto", "km_acumulado"]].to_dict("records")
            if not atuais.empty else []
        )

    elif tipo_db == "horario":
        atuais = listar_por_linha("horarios", codigo_linha)
        st.caption("Uma linha por horário de saída. Marque os dias em que ele roda.")
        colunas = ["sentido", "horario_saida"] + DIAS_SEMANA
        if not atuais.empty:
            base_editor = atuais[colunas].copy().reset_index(drop=True)
            base_editor["horario_saida"] = pd.to_datetime(
                base_editor["horario_saida"], format="%H:%M:%S"
            ).dt.time
        else:
            base_editor = pd.DataFrame(columns=colunas)
        column_config = {
            "sentido": st.column_config.SelectboxColumn("Sentido", options=["ida", "volta"]),
            "horario_saida": st.column_config.TimeColumn("Saída", format="HH:mm"),
        }
        for dia in DIAS_SEMANA:
            column_config[dia] = st.column_config.CheckboxColumn(DIAS_SEMANA_LABEL[dia])
        editado = st.data_editor(
            base_editor, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config=column_config, key=f"editor_horarios_{codigo_linha}",
        )
        valor_anterior = atuais[colunas].astype(str).to_dict("records") if not atuais.empty else []

    elif tipo_db == "tarifa":
        secoes_df = listar_por_linha("secoes", codigo_linha, order="ordem")
        paradas_df = (
            secoes_df[secoes_df["tipo_ponto"] == "parada"].reset_index(drop=True)
            if not secoes_df.empty else secoes_df
        )
        if len(paradas_df) < 2:
            st.warning(
                "Defina ao menos 2 pontos do tipo 'parada' através de uma OS de "
                "Seccionamento antes de cadastrar tarifas."
            )
            return
        atuais = listar_por_linha("tarifas", codigo_linha)
        pares = []
        for i in range(len(paradas_df)):
            for j in range(i + 1, len(paradas_df)):
                origem = paradas_df.iloc[i]
                destino = paradas_df.iloc[j]
                existente = (
                    atuais[
                        (atuais["secao_origem_id"] == origem["id"])
                        & (atuais["secao_destino_id"] == destino["id"])
                    ] if not atuais.empty else pd.DataFrame()
                )
                pares.append({
                    "origem_id": int(origem["id"]), "Origem": origem["nome"],
                    "destino_id": int(destino["id"]), "Destino": destino["nome"],
                    "Tarifa": float(existente["valor"].iloc[0]) if not existente.empty else 0.0,
                })
        base_editor = pd.DataFrame(pares)
        st.caption("Tarifa entre cada par de paradas da linha.")
        editado = st.data_editor(
            base_editor,
            disabled=["origem_id", "Origem", "destino_id", "Destino"],
            use_container_width=True,
            hide_index=True,
            key=f"editor_tarifas_{codigo_linha}",
        )
        valor_anterior = (
            atuais[["secao_origem_id", "secao_destino_id", "valor"]].to_dict("records")
            if not atuais.empty else []
        )

    else:
        valor_anterior = st.text_input("Valor/situação anterior (opcional)")
        valor_novo = st.text_area("O que está mudando")

    observacao = st.text_area("Observação (opcional)")

    if st.button("Criar alteração", key="cf_nova_alteracao"):
        if tipo_db == "seccionamento":
            validas = editado[editado["nome"].astype(str).str.strip() != ""]
            if validas.empty:
                st.warning("Adicione ao menos um ponto.")
                return
            valor_novo = [
                {
                    "ordem": i,
                    "nome": str(r.nome).strip(),
                    "tipo_ponto": r.tipo_ponto or "parada",
                    "km_acumulado": float(r.km_acumulado) if pd.notna(r.km_acumulado) else None,
                }
                for i, r in enumerate(validas.itertuples(), start=1)
            ]
        elif tipo_db == "horario":
            validas = editado.dropna(subset=["sentido", "horario_saida"])
            if validas.empty:
                st.warning("Adicione ao menos um horário.")
                return
            valor_novo = []
            for r in validas.itertuples():
                hs = r.horario_saida
                registro = {
                    "sentido": r.sentido,
                    "horario_saida": hs.strftime("%H:%M:%S") if hasattr(hs, "strftime") else str(hs),
                }
                for dia in DIAS_SEMANA:
                    registro[dia] = bool(getattr(r, dia))
                valor_novo.append(registro)
        elif tipo_db == "tarifa":
            valor_novo = [
                {
                    "secao_origem_id": int(r.origem_id),
                    "secao_destino_id": int(r.destino_id),
                    "valor": float(r.Tarifa) if pd.notna(r.Tarifa) else 0.0,
                }
                for r in editado.itertuples()
            ]

        novo_vazio = (
            (isinstance(valor_novo, dict) and not valor_novo.get("id"))
            or (
                not isinstance(valor_novo, (dict, list))
                and not str(valor_novo or "").strip()
            )
        )
        if tipo_db == "cadastral" and novo_vazio:
            st.warning("Informe o novo valor.")
            return
        if tipo_db not in ("cadastral", "seccionamento", "horario", "tarifa") and not str(valor_novo).strip():
            st.warning("Descreva o que está mudando.")
            return
        dados = {
            "linha_codigo": codigo_linha,
            "tipo_alteracao": tipo_db,
            "campo": campo_db,
            "valor_anterior": valor_anterior,
            "valor_novo": valor_novo,
            "status": "rascunho",
            "usuario_criador_id": usuario_atual_id(),
            "observacao": observacao.strip() or None,
        }
        if executar(
            lambda: sb.table("alteracoes").insert(dados).execute(),
            msg_duplicado="Essa linha já tem uma alteração em andamento.",
        ):
            recarregar()


@st.dialog("Cancelar Alteração")
def dlg_cancelar_alteracao(row):
    st.warning(f"Cancelar a alteração da linha **{row['linha_codigo']}**?")
    motivo = st.text_area("Motivo (opcional)")
    c1, c2 = st.columns(2)
    if c1.button("Confirmar cancelamento", key=f"cf_cancel_{row['id']}"):
        nova_obs = (row.get("observacao") or "")
        if motivo.strip():
            nova_obs = (nova_obs + " | Cancelada: " + motivo.strip()).strip(" |")
        if executar(lambda: sb.table("alteracoes").update(
            {"status": "cancelada", "observacao": nova_obs or None}
        ).eq("id", row["id"]).execute()):
            recarregar()
    if c2.button("Voltar", key=f"cc_cancel_{row['id']}"):
        st.rerun()


@st.dialog("Concluir OS")
def dlg_concluir_alteracao(row):
    st.write(f"Linha **{row['linha_codigo']}** — {TIPO_ALTERACAO_LABEL.get(row['tipo_alteracao'], row['tipo_alteracao'])}")
    st.caption("Informe os dados da aprovação. Os dados da norma são opcionais — preencha se já houver uma publicada.")

    data_vigencia = st.date_input("Data de vigência")
    tem_norma = st.checkbox("Já existe norma publicada para vincular a esta OS")
    norma_tipo = norma_numero = norma_data_publicacao = None
    if tem_norma:
        norma_tipo = st.selectbox("Tipo de norma", TIPOS_NORMA)
        norma_numero = st.text_input("Número da norma")
        norma_data_publicacao = st.date_input("Data de publicação da norma", value=None)

    if st.button("Concluir", key=f"cf_concluir_{row['id']}"):
        def aplicar():
            sb.table("alteracoes").update({
                "status": "concluida",
                "data_vigencia": str(data_vigencia),
                "norma_tipo": norma_tipo,
                "norma_numero": norma_numero.strip() if norma_numero else None,
                "norma_data_publicacao": str(norma_data_publicacao) if norma_data_publicacao else None,
                "usuario_conclusao_id": usuario_atual_id(),
                "concluido_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", row["id"]).execute()
            if row["tipo_alteracao"] == "cadastral" and row.get("campo"):
                novo = row["valor_novo"]
                valor_aplicar = novo.get("id") if isinstance(novo, dict) else novo
                sb.table("linhas").update(
                    {row["campo"]: valor_aplicar}
                ).eq("codigo", row["linha_codigo"]).execute()
            elif row["tipo_alteracao"] == "exclusao":
                sb.table("linhas").update({"status": "excluida"}).eq("codigo", row["linha_codigo"]).execute()
            elif row["tipo_alteracao"] == "seccionamento":
                sb.table("secoes").delete().eq("linha_codigo", row["linha_codigo"]).execute()
                registros = row["valor_novo"] or []
                if registros:
                    sb.table("secoes").insert(
                        [{**r, "linha_codigo": row["linha_codigo"]} for r in registros]
                    ).execute()
            elif row["tipo_alteracao"] == "horario":
                sb.table("horarios").delete().eq("linha_codigo", row["linha_codigo"]).execute()
                registros = row["valor_novo"] or []
                if registros:
                    sb.table("horarios").insert(
                        [{**r, "linha_codigo": row["linha_codigo"]} for r in registros]
                    ).execute()
            elif row["tipo_alteracao"] == "tarifa":
                sb.table("tarifas").delete().eq("linha_codigo", row["linha_codigo"]).execute()
                registros = row["valor_novo"] or []
                if registros:
                    sb.table("tarifas").insert(
                        [{**r, "linha_codigo": row["linha_codigo"]} for r in registros]
                    ).execute()

        if executar(aplicar):
            recarregar()


def _fmt_valor_os(v):
    if isinstance(v, dict):
        return v.get("label") or "—"
    return v if v not in (None, "") else "—"


@st.dialog("Detalhes da OS")
def dlg_ver_detalhes_os(row):
    linhas_df = listar("linhas", order="codigo")
    usuarios_df = listar("usuarios")
    linha_atual = linhas_df.loc[linhas_df["codigo"] == row["linha_codigo"]]
    nome_linha = linha_atual["nome"].iloc[0] if not linha_atual.empty else "—"

    st.markdown(f"**Linha:** {row['linha_codigo']} — {nome_linha}")
    st.markdown(f"**Tipo de OS:** {TIPO_ALTERACAO_LABEL.get(row['tipo_alteracao'], row['tipo_alteracao'])}")
    st.markdown(f"**Status:** {STATUS_LABEL.get(row['status'], row['status'])}")
    if row.get("campo"):
        campo_labels = [k for k, v in CAMPOS_CADASTRAIS.items() if v == row["campo"]]
        st.markdown(f"**Campo alterado:** {campo_labels[0] if campo_labels else row['campo']}")

    if row["tipo_alteracao"] in ("seccionamento", "horario", "tarifa"):
        st.markdown("**Valor anterior:**")
        anterior = row.get("valor_anterior")
        st.dataframe(pd.DataFrame(anterior), hide_index=True, use_container_width=True) if anterior else st.caption("—")
        st.markdown("**Valor novo:**")
        novo = row.get("valor_novo")
        st.dataframe(pd.DataFrame(novo), hide_index=True, use_container_width=True) if novo else st.caption("—")
    else:
        st.markdown(f"**Valor anterior:** {_fmt_valor_os(row.get('valor_anterior'))}")
        st.markdown(f"**Valor novo:** {_fmt_valor_os(row.get('valor_novo'))}")
    st.markdown(f"**Observação:** {row.get('observacao') or '—'}")
    st.markdown(f"**Criado por:** {_nome_por_id(usuarios_df, row.get('usuario_criador_id'))}")
    if pd.notna(row.get("criado_em")):
        st.markdown(f"**Criado em:** {pd.to_datetime(row['criado_em']).strftime('%d/%m/%Y %H:%M')}")

    if row["status"] == "concluida":
        st.divider()
        st.markdown(f"**Data de vigência:** {row.get('data_vigencia') or '—'}")
        if row.get("norma_tipo") or row.get("norma_numero"):
            st.markdown(f"**Norma:** {row.get('norma_tipo') or ''} nº {row.get('norma_numero') or '—'}")
            if row.get("norma_data_publicacao"):
                st.markdown(f"**Publicada em:** {row['norma_data_publicacao']}")
        else:
            st.markdown("**Norma:** não informada")
        st.markdown(f"**Concluído por:** {_nome_por_id(usuarios_df, row.get('usuario_conclusao_id'))}")
        if pd.notna(row.get("concluido_em")):
            st.markdown(f"**Concluído em:** {pd.to_datetime(row['concluido_em']).strftime('%d/%m/%Y %H:%M')}")

    if st.button("Fechar", key=f"fechar_detalhes_{row['id']}"):
        st.rerun()


# ============================================================================
# Abas
# ============================================================================

tab_cadastro, tab_os = st.tabs(["📋 Cadastro", "📝 Abrir OS"])

with tab_cadastro:
    secao = st.radio(
        "Seção do cadastro",
        ["Sistemas", "Lotes", "Operadores", "Tipos de Linha", "Espécies de Serviço",
         "Linhas"],
        horizontal=True,
        key="cadastro_secao",
        label_visibility="collapsed",
    )
    st.divider()

    if secao == "Sistemas":
        tabela_simples("sistemas", "Sistemas")

    elif secao == "Tipos de Linha":
        tabela_simples("tipos_linha", "Tipos de Linha")

    elif secao == "Espécies de Serviço":
        tabela_simples("especies_servico", "Espécies de Serviço")

    elif secao == "Operadores":
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

    elif secao == "Lotes":
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

    elif secao == "Linhas":
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

        c0, c1, c2, c3 = st.columns([1, 1, 1, 1])
        if c0.button("📊 Estrutura", key="abrir_estrutura_linha", disabled=pos is None):
            dlg_ver_estrutura_linha(filtradas.iloc[pos])
        if admin:
            if c1.button("+ Adicionar", key="abrir_add_linha"):
                dlg_add_linha()
        else:
            c1.caption("Inclusão: só administradores.")
        if admin:
            if c2.button("✏️ Editar (direto)", key="abrir_ed_linha", disabled=pos is None):
                dlg_edit_linha(filtradas.iloc[pos])
        else:
            c2.caption("Edição direta: só administradores. Use a aba Abrir OS.")
        if admin:
            if c3.button("❌ Excluir", key="abrir_del_linha", disabled=pos is None):
                dlg_del_linha(filtradas.iloc[pos])
        else:
            c3.caption("Exclusão: só administradores.")
        if pos is None and not linhas_df.empty:
            st.caption("Selecione uma linha da tabela para editar ou excluir (ou ver a estrutura).")

with tab_os:
    st.subheader("OS — Acompanhamento")

    if st.button("+ Abrir OS", key="abrir_add_alteracao"):
        dlg_nova_alteracao()

    alteracoes_df = listar("alteracoes")
    if alteracoes_df.empty:
        st.caption("Nenhuma OS registrada ainda.")
    else:
        usuarios_df = listar("usuarios")
        opcoes_status = ["(Todas em aberto)", "(Todas)"] + list(STATUS_LABEL.values())
        status_filtro = st.selectbox("Status", opcoes_status, key="alt_f_status")

        alteracoes_df = alteracoes_df.copy()
        alteracoes_df["criado_em_dt"] = pd.to_datetime(alteracoes_df["criado_em"])
        alteracoes_df["dias"] = (
            pd.Timestamp.now(tz=alteracoes_df["criado_em_dt"].dt.tz) - alteracoes_df["criado_em_dt"]
        ).dt.days

        filtradas_alt = alteracoes_df
        if status_filtro == "(Todas em aberto)":
            filtradas_alt = filtradas_alt[~filtradas_alt["status"].isin(["concluida", "cancelada"])]
        elif status_filtro != "(Todas)":
            status_db = [k for k, v in STATUS_LABEL.items() if v == status_filtro][0]
            filtradas_alt = filtradas_alt[filtradas_alt["status"] == status_db]
        filtradas_alt = filtradas_alt.sort_values("criado_em", ascending=False).reset_index(drop=True)

        if filtradas_alt.empty:
            st.caption("Nenhuma OS nesse filtro.")
            pos_alt = None
        else:
            exibicao = filtradas_alt.copy()
            exibicao["Tipo"] = exibicao["tipo_alteracao"].map(lambda t: TIPO_ALTERACAO_LABEL.get(t, t))
            exibicao["Status"] = exibicao["status"].map(lambda s: STATUS_LABEL.get(s, s))
            exibicao["Criado por"] = exibicao["usuario_criador_id"].map(lambda i: _nome_por_id(usuarios_df, i))
            exibicao = exibicao[["linha_codigo", "Tipo", "Status", "dias", "Criado por"]].rename(
                columns={"linha_codigo": "Linha", "dias": "Dias em aberto"}
            )
            st.caption(f"{len(filtradas_alt)} OS")
            pos_alt = selecionar_linha_df(exibicao, "df_alteracoes")

        if pos_alt is not None:
            sel = filtradas_alt.iloc[pos_alt]
            c0, c1, c2, c3 = st.columns(4)
            if c0.button("🔍 Ver detalhes", key=f"detalhes_{sel['id']}"):
                dlg_ver_detalhes_os(sel)

            if sel["status"] == "rascunho":
                if c1.button("Enviar para aprovação", key=f"enviar_{sel['id']}"):
                    if executar(lambda: sb.table("alteracoes").update(
                        {"status": "enviada_aprovacao"}
                    ).eq("id", sel["id"]).execute()):
                        recarregar()
                if c3.button("Cancelar OS", key=f"abrir_cancel_{sel['id']}"):
                    dlg_cancelar_alteracao(sel)

            elif sel["status"] == "enviada_aprovacao":
                if c1.button("Marcar como aprovada (aguardando norma)", key=f"aprovar_{sel['id']}"):
                    if executar(lambda: sb.table("alteracoes").update(
                        {"status": "aprovada_aguardando_norma"}
                    ).eq("id", sel["id"]).execute()):
                        recarregar()
                if c3.button("Cancelar OS", key=f"abrir_cancel_{sel['id']}"):
                    dlg_cancelar_alteracao(sel)

            elif sel["status"] == "aprovada_aguardando_norma":
                if c1.button("Concluir (norma publicada)", key=f"abrir_concluir_{sel['id']}"):
                    dlg_concluir_alteracao(sel)
                if c3.button("Cancelar OS", key=f"abrir_cancel_{sel['id']}"):
                    dlg_cancelar_alteracao(sel)

            else:
                st.caption("OS finalizada — sem mais ações disponíveis.")
        elif not filtradas_alt.empty:
            st.caption("Selecione uma OS da tabela para agir sobre ela.")
