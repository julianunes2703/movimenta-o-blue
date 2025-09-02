import pandas as pd
import streamlit as st
import altair as alt
from datetime import date

# -------------------------------------------------
# CONFIGURE AQUI:
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxA4DyiFFBv-scpSoVShs0udQphFfPA7pmOg47FTxWIQQqY93enCr-razUSo_IvpDi8l-0JfQef7-E/pub?gid=0&single=true&output=csv"
DATA_COL = "Data"
CLIENTE_COL = "Cliente"
MOV_COL = "Teve movimentação"   # exatamente como no cabeçalho da planilha
# -------------------------------------------------

st.set_page_config(page_title="Movimentação por Cliente", layout="wide")
st.title("Movimentação por Cliente × Data")

@st.cache_data(ttl=900)  # cache 15 min
def load_data():
    # Lê CSV publicado (tem que ser pub?output=csv)
    df = pd.read_csv(CSV_URL)

    # Normaliza a
    df.columns = df.columns.str.strip()

    # Checa se as colunas existem
    missing = [c for c in [DATA_COL, CLIENTE_COL, MOV_COL] if c not in df.columns]
    if missing:
        raise ValueError(
            f"Cabeçalhos não encontrados: {missing}. "
            f"Colunas presentes: {list(df.columns)}. "
            "Confirme o nome exato dos cabeçalhos ou ajuste DATA_COL/CLIENTE_COL/MOV_COL."
        )

    # Padroniza nomes
    df = df.rename(columns={
        DATA_COL: "Data",
        CLIENTE_COL: "Cliente",
        MOV_COL: "MovRaw"
    })

    # Converte data (dia primeiro)
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    # Normaliza "Sim/Não" -> 1/0
    df["Mov"] = (
        df["MovRaw"]
        .astype(str).str.strip().str.lower()
        .isin(["sim", "s", "1", "true", "yes", "y"])
        .astype(int)
    )

    # Limpa e consolida (se houver duplicadas no mesmo dia/cliente)
    df = df.dropna(subset=["Data", "Cliente"])
    df = df.groupby([df["Data"].dt.date, "Cliente"], as_index=False)["Mov"].max()
    df["Data"] = pd.to_datetime(df["Data"])

    return df.sort_values(["Data", "Cliente"]).reset_index(drop=True)

# Carrega dados com tratamento de erro amigável
try:
    df = load_data()
except Exception as e:
    st.error("❌ Falha ao carregar os dados.")
    st.code(CSV_URL)
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Sua base está vazia após o processamento.")
    st.stop()

# Intervalo de datas
dmin = df["Data"].min().date()
dmax = df["Data"].max().date()
c1, c2 = st.columns(2)
start = c1.date_input("Data inicial", value=dmin, min_value=dmin, max_value=dmax)
end = c2.date_input("Data final", value=dmax, min_value=dmin, max_value=dmax)

mask = (df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)
dfp = df.loc[mask].copy()

# Filtro de clientes
todos_clientes = sorted(dfp["Cliente"].unique().tolist())
sel_clientes = st.multiselect("Filtrar clientes (opcional)", todos_clientes, default=todos_clientes)
dfp = dfp[dfp["Cliente"].isin(sel_clientes)]

# Garante a grade completa (datas × clientes) para mostrar vazios
all_dates = pd.date_range(start, end, freq="D")
all_clients = sorted(dfp["Cliente"].unique().tolist())
if not all_clients:
    st.info("Nenhum cliente no período/filtro selecionado.")
    st.stop()

grid = pd.MultiIndex.from_product([all_dates, all_clients],
                                  names=["Data", "Cliente"]).to_frame(index=False)
data_final = grid.merge(dfp[["Data", "Cliente", "Mov"]], on=["Data", "Cliente"], how="left")
data_final["Mov"] = data_final["Mov"].fillna(0).astype(int)

# Altura dinâmica
height = min(24 * max(1, len(all_clients)) + 80, 1000)

chart = alt.Chart(data_final).mark_rect().encode(
    x=alt.X("yearmonthdate(Data):O", title="Data"),
    y=alt.Y("Cliente:N", sort=all_clients, title="Cliente"),
    color=alt.Color("Mov:Q",
                    scale=alt.Scale(domain=[0, 1], range=["#ffffff", "#34a853"]),
                    legend=None),
    tooltip=[
        alt.Tooltip("yearmonthdate(Data):O", title="Data"),
        alt.Tooltip("Cliente:N"),
        alt.Tooltip("Mov:Q", title="Teve movimentação (1=Sim, 0=Não)")
    ]
).properties(height=height)

st.altair_chart(chart, use_container_width=True)

# Botão para forçar atualização
if st.button("Atualizar dados agora"):
    load_data.clear()
    st.rerun()

st.caption("Lendo CSV publicado (pub?output=csv&gid=...). Atualiza com cache de 15 min.")


