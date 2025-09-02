import pandas as pd
import streamlit as st
import altair as alt
import unicodedata

# ===== URL CSV PUBLICADO (não use pubhtml) =====
# Se precisar outra aba, troque o gid=0 para o gid da aba correta.
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxA4DyiFFBv-scpSoVShs0udQphFfPA7pmOg47FTxWIQQqY93enCr-razUSo_IvpDi8l-0JfQef7-E/pub?gid=0&single=true&output=csv"
CACHE_TTL = 900  # 15 min
# ==============================================

st.set_page_config(page_title="Movimentação × Data", layout="wide")
st.title("Movimentação por Cliente × Data")

def norm(s: str) -> str:
    """normaliza: sem acento, minúsculo, sem espaços extras"""
    if s is None: 
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.strip().lower()

def to_bin(v) -> int:
    """converte texto livre para 1/0 (evita .strip em Series)"""
    s = str(v).strip().lower()
    return 1 if s in {"sim","s","1","true","yes","y","ok","x"} else 0

@st.cache_data(ttl=CACHE_TTL)
def load_data():
    # 1) Lê o CSV publicado
    df = pd.read_csv(CSV_URL)

    # 2) Debug (colunas + amostra)
    with st.expander("🔧 Debug (colunas e primeiras linhas)"):
        st.write("Colunas do CSV:", list(df.columns))
        st.dataframe(df.head())

    # 3) Auto-detecção de colunas por similaridade
    colmap = {norm(c): c for c in df.columns}

    def pick(candidates):
        for cand in candidates:
            key = norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    date_col    = pick(["Data", "date", "DATA", "Dia"])
    cliente_col = pick(["Cliente", "Empresa", "Cliente/Empresa", "Nome do Cliente", "Client"])
    mov_col     = pick(["Teve movimentação", "Teve movimentacao", "Movimentação", "Movimentacao", "Mov", "Movimentou", "teve movimento"])

    missing = []
    if not date_col:    missing.append("Data")
    if not cliente_col: missing.append("Cliente/Empresa")
    if not mov_col:     missing.append("Teve movimentação (Sim/Não)")

    if missing:
        raise ValueError(
            "Não encontrei as colunas esperadas: "
            + ", ".join(missing)
            + f". Colunas no CSV: {list(df.columns)}.\n"
            "Dica: ajuste os nomes na planilha OU adicione variações nas listas acima."
        )

    # 4) Padroniza nomes
    df = df.rename(columns={date_col: "Data", cliente_col: "Cliente", mov_col: "MovRaw"})

    # 5) Converte Data
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    # 6) Converte Sim/Não em 1/0 (sem .strip direto na Series)
    df["Mov"] = df["MovRaw"].map(to_bin).astype(int)

    # 7) Limpa e consolida duplicatas por dia/cliente
    df = df.dropna(subset=["Data", "Cliente"])
    df = df.groupby([df["Data"].dt.date, "Cliente"], as_index=False)["Mov"].max()
    df["Data"] = pd.to_datetime(df["Data"])

    return df.sort_values(["Data", "Cliente"]).reset_index(drop=True)

# ===== Carrega dados =====
try:
    df = load_data()
except Exception as e:
    st.error("❌ Falha ao carregar os dados. Confira o gid/URL e os cabeçalhos.")
    st.code(CSV_URL)
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Sua base está vazia após o processamento.")
    st.stop()

# ===== Filtros =====
dmin, dmax = df["Data"].min().date(), df["Data"].max().date()
c1, c2 = st.columns(2)
start = c1.date_input("Data inicial", value=dmin, min_value=dmin, max_value=dmax)
end   = c2.date_input("Data final",   value=dmax, min_value=dmin, max_value=dmax)

mask = (df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)
dfp = df.loc[mask].copy()

clientes = sorted(dfp["Cliente"].unique().tolist())
sel = st.multiselect("Filtrar clientes (opcional)", clientes, default=clientes)
dfp = dfp[dfp["Cliente"].isin(sel)]

# ===== Garante grade completa (datas × clientes) =====
all_dates   = pd.date_range(start, end, freq="D")
all_clients = sorted(dfp["Cliente"].unique().tolist())
if not all_clients:
    st.info("Nenhum cliente no período/filtro selecionado.")
    st.stop()

grid = pd.MultiIndex.from_product([all_dates, all_clients], names=["Data", "Cliente"]).to_frame(index=False)
data_final = grid.merge(dfp[["Data", "Cliente", "Mov"]], on=["Data", "Cliente"], how="left")
data_final["Mov"] = data_final["Mov"].fillna(0).astype(int)

# ===== Heatmap =====
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

# ===== Botão de recarregar =====
if st.button("Atualizar dados agora"):
    load_data.clear()
    st.rerun()

st.caption("Lendo CSV publicado (pub?output=csv&gid=...). Ajuste o gid para a aba correta se necessário.")
