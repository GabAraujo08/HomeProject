"""
App de Comparação de Imóveis
=============================
Sistema CRUD simples em Streamlit para cadastrar, organizar e comparar
anúncios de imóveis (aluguel ou compra), usando o Google Sheets como
banco de dados (persistência gratuita e compatível com o file system
efêmero do Streamlit Community Cloud).

Autor: gerado com Claude para uso pessoal.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --------------------------------------------------------------------------
# Configuração geral
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Comparador de Imóveis",
    page_icon="🏠",
    layout="wide",
)

WORKSHEET_NAME = "Imoveis"

STATUS_OPCOES = [
    "Para Avaliar",
    "Visita Agendada",
    "Visitado",
    "Descartado",
    "Top Opções",
]

# Ordem e nomes das colunas na planilha. Mantenha essa ordem estável:
# se você editar a planilha manualmente, mantenha os cabeçalhos iguais.
COLUNAS = [
    "ID",
    "Link",
    "Bairro",
    "Valor_Base",
    "Valor_Condominio",
    "Valor_IPTU",
    "Custo_Total",
    "Area_m2",
    "Vagas_Garagem",
    "Estacao_Proxima",
    "Tempo_Estacao_min",
    "Status",
    "Notas",
    "Data_Cadastro",
]

COLUNAS_NUMERICAS = [
    "Valor_Base",
    "Valor_Condominio",
    "Valor_IPTU",
    "Custo_Total",
    "Area_m2",
    "Vagas_Garagem",
    "Tempo_Estacao_min",
]


# --------------------------------------------------------------------------
# Camada de dados (Google Sheets)
# --------------------------------------------------------------------------

def get_connection() -> GSheetsConnection:
    """Retorna a conexão com o Google Sheets (cacheada pelo próprio st.connection)."""
    return st.connection("gsheets", type=GSheetsConnection)


def load_data(ttl: int = 0) -> pd.DataFrame:
    """
    Lê todos os imóveis cadastrados na planilha.
    ttl=0 desabilita o cache para sempre trazer os dados mais recentes
    (importante porque duas pessoas -- você e sua namorada -- podem editar
    ao mesmo tempo).
    """
    conn = get_connection()
    try:
        df = conn.read(worksheet=WORKSHEET_NAME, ttl=ttl)
    except Exception:
        # Planilha/aba ainda não existe -> começamos com um dataframe vazio
        df = pd.DataFrame(columns=COLUNAS)

    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS)

    # Garante que todas as colunas esperadas existam (evita erro se a
    # planilha for editada manualmente e perder alguma coluna)
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUNAS]

    # Remove linhas totalmente vazias (comuns em planilhas do Sheets)
    df = df.dropna(how="all")
    df = df[df["ID"].notna() & (df["ID"].astype(str).str.strip() != "")]

    # Conversão de tipos numéricos (o Sheets pode devolver tudo como texto)
    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


def save_data(df: pd.DataFrame) -> None:
    """Sobrescreve a planilha inteira com o dataframe atualizado."""
    conn = get_connection()
    conn.update(worksheet=WORKSHEET_NAME, data=df[COLUNAS])
    st.cache_data.clear()


def add_imovel(novo_registro: dict) -> None:
    """Adiciona um novo imóvel à planilha (append lógico via leitura + concat + update)."""
    df_atual = load_data(ttl=0)
    novo_df = pd.DataFrame([novo_registro])
    df_final = pd.concat([df_atual, novo_df], ignore_index=True)
    save_data(df_final)


def update_imovel(imovel_id: str, novo_status: str, novas_notas: str) -> None:
    """Atualiza Status e Notas de um imóvel existente, identificado pelo ID."""
    df_atual = load_data(ttl=0)
    mask = df_atual["ID"] == imovel_id
    df_atual.loc[mask, "Status"] = novo_status
    df_atual.loc[mask, "Notas"] = novas_notas
    save_data(df_atual)


def delete_imovel(imovel_id: str) -> None:
    """Remove um imóvel da planilha."""
    df_atual = load_data(ttl=0)
    df_atual = df_atual[df_atual["ID"] != imovel_id]
    save_data(df_atual)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def formatar_moeda(valor: float) -> str:
    if pd.isna(valor):
        return "-"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rotulo_imovel(row: pd.Series) -> str:
    """Rótulo amigável para identificar um imóvel em um selectbox."""
    bairro = row.get("Bairro") or "Sem bairro"
    custo = formatar_moeda(row.get("Custo_Total"))
    return f"{bairro} — {custo} — ID {row['ID'][:8]}"


# --------------------------------------------------------------------------
# Tela: Cadastrar Imóvel
# --------------------------------------------------------------------------

def tela_cadastro() -> None:
    st.header("🏠 Cadastrar novo imóvel")
    st.caption("Preencha os dados do anúncio. O custo total é calculado automaticamente.")

    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            link = st.text_input("Link do anúncio (URL)*")
            bairro = st.text_input("Bairro*")
            valor_base = st.number_input(
                "Valor Base (aluguel ou compra) — R$*",
                min_value=0.0, step=50.0, format="%.2f",
            )
            valor_condominio = st.number_input(
                "Valor Condomínio — R$", min_value=0.0, step=10.0, format="%.2f",
            )
            valor_iptu = st.number_input(
                "Valor IPTU — R$", min_value=0.0, step=10.0, format="%.2f",
            )

        with col2:
            area = st.number_input("Área (m²)*", min_value=0.0, step=1.0, format="%.1f")
            vagas = st.number_input("Vagas de Garagem", min_value=0, step=1)
            estacao = st.text_input("Estação/ponto de transporte mais próximo")
            tempo_estacao = st.number_input(
                "Tempo até a estação/transporte (minutos)", min_value=0, step=1,
            )
            status = st.selectbox("Status", STATUS_OPCOES, index=0)

        notas = st.text_area("Notas (impressões, prós e contras, etc.)", height=100)

        custo_total_preview = valor_base + valor_condominio + valor_iptu
        st.metric("Custo Total (calculado)", formatar_moeda(custo_total_preview))

        enviado = st.form_submit_button("Salvar imóvel", type="primary", use_container_width=True)

        if enviado:
            if not link or not bairro or valor_base <= 0 or area <= 0:
                st.error("Preencha ao menos: Link, Bairro, Valor Base e Área.")
            else:
                novo_registro = {
                    "ID": str(uuid.uuid4()),
                    "Link": link,
                    "Bairro": bairro,
                    "Valor_Base": valor_base,
                    "Valor_Condominio": valor_condominio,
                    "Valor_IPTU": valor_iptu,
                    "Custo_Total": valor_base + valor_condominio + valor_iptu,
                    "Area_m2": area,
                    "Vagas_Garagem": int(vagas),
                    "Estacao_Proxima": estacao,
                    "Tempo_Estacao_min": int(tempo_estacao),
                    "Status": status,
                    "Notas": notas,
                    "Data_Cadastro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                with st.spinner("Salvando no Google Sheets..."):
                    add_imovel(novo_registro)
                st.success("Imóvel cadastrado com sucesso!")
                st.balloons()


# --------------------------------------------------------------------------
# Tela: Comparar Imóveis
# --------------------------------------------------------------------------

def tela_comparacao() -> None:
    st.header("📊 Comparar imóveis")

    with st.spinner("Carregando dados..."):
        df = load_data(ttl=0)

    if df.empty:
        st.info("Nenhum imóvel cadastrado ainda. Use o menu lateral para cadastrar o primeiro.")
        return

    # ---------------- Filtros ----------------
    st.subheader("Filtros")
    f1, f2, f3, f4, f5 = st.columns(5)

    bairros_disponiveis = sorted(df["Bairro"].dropna().unique().tolist())
    with f1:
        filtro_bairro = st.multiselect("Bairro", bairros_disponiveis)

    with f2:
        filtro_status = st.multiselect("Status", STATUS_OPCOES)

    custo_max_possivel = float(df["Custo_Total"].max(skipna=True) or 0)
    with f3:
        filtro_custo_max = st.number_input(
            "Custo Total máximo (R$)",
            min_value=0.0,
            value=custo_max_possivel if custo_max_possivel > 0 else 0.0,
            step=100.0,
        )

    with f4:
        filtro_vagas_min = st.number_input("Mínimo de vagas", min_value=0, step=1, value=0)

    tempo_max_possivel = int(df["Tempo_Estacao_min"].max(skipna=True) or 0)
    with f5:
        filtro_tempo_max = st.number_input(
            "Tempo máx. até transporte (min)",
            min_value=0,
            value=tempo_max_possivel if tempo_max_possivel > 0 else 0,
            step=5,
        )

    df_filtrado = df.copy()
    if filtro_bairro:
        df_filtrado = df_filtrado[df_filtrado["Bairro"].isin(filtro_bairro)]
    if filtro_status:
        df_filtrado = df_filtrado[df_filtrado["Status"].isin(filtro_status)]
    if filtro_custo_max > 0:
        df_filtrado = df_filtrado[df_filtrado["Custo_Total"] <= filtro_custo_max]
    if filtro_vagas_min > 0:
        df_filtrado = df_filtrado[df_filtrado["Vagas_Garagem"] >= filtro_vagas_min]
    if filtro_tempo_max > 0:
        df_filtrado = df_filtrado[df_filtrado["Tempo_Estacao_min"] <= filtro_tempo_max]

    st.caption(f"Exibindo {len(df_filtrado)} de {len(df)} imóveis cadastrados.")

    # ---------------- Tabela ----------------
    colunas_exibicao = [
        "Bairro", "Link", "Valor_Base", "Valor_Condominio", "Valor_IPTU",
        "Custo_Total", "Area_m2", "Vagas_Garagem", "Estacao_Proxima",
        "Tempo_Estacao_min", "Status", "Notas",
    ]

    st.dataframe(
        df_filtrado[colunas_exibicao].sort_values("Custo_Total"),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="Abrir anúncio"),
            "Valor_Base": st.column_config.NumberColumn("Valor Base", format="R$ %.2f"),
            "Valor_Condominio": st.column_config.NumberColumn("Condomínio", format="R$ %.2f"),
            "Valor_IPTU": st.column_config.NumberColumn("IPTU", format="R$ %.2f"),
            "Custo_Total": st.column_config.NumberColumn("Custo Total", format="R$ %.2f"),
            "Area_m2": st.column_config.NumberColumn("Área (m²)", format="%.1f m²"),
            "Tempo_Estacao_min": st.column_config.NumberColumn("Tempo transporte", format="%d min"),
        },
    )

    st.divider()

    # ---------------- Edição rápida ----------------
    st.subheader("✏️ Atualizar Status / Notas")

    df_filtrado = df_filtrado.reset_index(drop=True)
    opcoes_rotulo = {rotulo_imovel(row): row["ID"] for _, row in df_filtrado.iterrows()}

    if not opcoes_rotulo:
        st.info("Nenhum imóvel corresponde aos filtros atuais para edição.")
        return

    rotulo_selecionado = st.selectbox("Selecione o imóvel", list(opcoes_rotulo.keys()))
    id_selecionado = opcoes_rotulo[rotulo_selecionado]
    linha_atual = df[df["ID"] == id_selecionado].iloc[0]

    with st.form("form_edicao"):
        col_a, col_b = st.columns(2)
        with col_a:
            novo_status = st.selectbox(
                "Status",
                STATUS_OPCOES,
                index=STATUS_OPCOES.index(linha_atual["Status"])
                if linha_atual["Status"] in STATUS_OPCOES else 0,
            )
        with col_b:
            st.text_input("Bairro (somente leitura)", value=linha_atual["Bairro"], disabled=True)

        novas_notas = st.text_area("Notas", value=linha_atual.get("Notas") or "", height=100)

        col_salvar, col_excluir = st.columns(2)
        salvar = col_salvar.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
        excluir = col_excluir.form_submit_button("🗑️ Excluir imóvel", use_container_width=True)

        if salvar:
            with st.spinner("Atualizando no Google Sheets..."):
                update_imovel(id_selecionado, novo_status, novas_notas)
            st.success("Imóvel atualizado com sucesso!")
            st.rerun()

        if excluir:
            with st.spinner("Excluindo..."):
                delete_imovel(id_selecionado)
            st.success("Imóvel excluído.")
            st.rerun()


# --------------------------------------------------------------------------
# Navegação principal
# --------------------------------------------------------------------------

def main() -> None:
    st.sidebar.title("🏠 Comparador de Imóveis")
    pagina = st.sidebar.radio(
        "Navegação",
        ["Cadastrar Imóvel", "Comparar Imóveis"],
    )
    st.sidebar.divider()
    st.sidebar.caption(
        "Dados salvos automaticamente no Google Sheets. "
        "Basta atualizar a página para ver mudanças feitas por outra pessoa."
    )

    if pagina == "Cadastrar Imóvel":
        tela_cadastro()
    else:
        tela_comparacao()


if __name__ == "__main__":
    main()
