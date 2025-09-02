import pandas as pd
import streamlit as st
import altair as alt
import unicodedata
import re

# ===== URL CSV PUBLICADO (não use pubhtml) =====
# Troque o gid se a aba correta não for a primeira
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxA4DyiFFBv-scpSoVShs0udQphFfPA7pmOg47FTxWIQQqY93enCr-razUSo_IvpDi8l-0JfQef7-E/pub?gid=0&single=true&output=csv"
CACHE_TTL = 900  # 15 min
# ==============================================

st.set_page_config(page_title="Movimentação × Data", layout="wide")
st.title("Movimentação por Cliente × Data")

# ---------- util ----------
def norm(s: str) -> str:
    """normaliza: sem acento, minúsculo, sem espaços extras"""
    if s is None:
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.strip().lower()

def to_bin(v) -> int:
    """converte texto livre para 1/0"""
    s = str(v).strip().lower()
    return 1 if s in {"sim","s","1","true","t","yes","y","ok","x"} else 0

def infer_date_col(df: pd.DataFrame) -> str | None:
    """tenta achar a coluna que mais parece data"""
    best_col, best_ratio = None, 0.0
    for c in df.columns:
        # ignora colunas numéricas puras
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        # tenta parsear 200 primeiras linhas
        sample = pd.to_datetime(df[c].astype(str), dayfirst=True, errors="coerce").head(200)
        ratio = sample.notna().mean()
        if ratio > best_ratio:
            best_col, best_ratio = c, ratio
    return best_col if best_ratio >= 0.5 else None  # precisa ser "majoritariamente" data

def infer_mov_col(df: pd.DataFrame, exclude: set) -> str | None:
    """tenta achar coluna de movimentação por valores típicos (sim/não/1/0)"""
    candidates = []
    for c in df.columns:
        if c in exclude:
            continue
        series = df[c].astype(str).str.strip().str.lower()
        # score por presença de valores típicos
        good = series.isin({"sim","s","nao","não","n","0","1","true","false","t","f","yes","y","no"})
        score = good.mean()
        candidates.append((score, c))
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates and candidates[0][0] >= 0.5 else None

def infer_client_col(df: pd.DataFrame, exclude: set) -> str | None:
    """escolhe coluna de 'cliente/empresa' (texto, boa cardinalidade)"""
    # preferir nomes que contenham 'cliente' ou 'empresa'
    for c in df.columns:
        if c in exclude:
            continue
        if re.search(r"(cliente|empresa)", norm(c)):
            return c
    # fallback: primeira coluna de texto não excluída com cardinalidade razoável
    best = None
    best_card = 0
    for c in df.columns:
        if c in exclude:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        card = df[c].nunique(dropna=True)
        if 1 < card < len(df) and card > best_card:
            best, best_card = c, card
    return best
# --------------------------

@st.cache_data(ttl=CACHE_TTL)
def load_data():
    # 1) lê CSV
    df = pd.read_csv(CSV_URL)

    # 2) debug
    with st.expander("🔧 Debug (colunas e primeiras linhas)"):
        st.write("URL CSV:", CSV_URL)
        st.write("Colunas do CSV:", list(df.columns))
        st.dataframe(df.head())

    # 3) mapeia por nome "parecido"
    colmap = {norm(c): c for c in df.columns}

    def pick(candidates):
        for cand in candidates:
            key = norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    date_col = pick(["Data", "date", "DATA", "Dia"])
    cliente_col = pick(["Cliente", "Empresa", "Cliente/Empresa", "Nome do Cliente", "Client"])
    mov_col = pick(["Teve movimentação", "Teve movimentacao", "Movimentação", "Movimentacao", "Mov", "Movimentou", "teve movimento"])

    # Fallbacks robustos
    if not date_col:
        date_col = infer_date_col(df)
    if not date_col:
        raise ValueError(
            "Não encontrei a coluna de Data. Ajuste o cabeçalho na planilha (ex.: 'Data') "
            "ou publique a aba correta (gid)."
        )

    if not cliente_col:
        cliente_col = infer_client_col(df, exclude={date_col})
    if not cliente_col:
        raise ValueError(
            "Não encontrei a coluna de Cliente/Empresa. Ajuste o cabeçalho (ex.: 'Cliente' ou 'Empresa')."
        )

    if not mov_col:
        mov_col = infer_mov_col(df, exclude={date_col, cliente_col})
    if not mov_col:
        raise ValueError(
            "Não encontrei a coluna de 'Teve movimentação'. Use algo como 'Teve movimentação'/'Movimentação'/'Mov' "
            "com valores 'Sim/Não' (ou 1/0)."
        )

    # 4) padroniza nomes
    df = df.rename(columns={date_col: "Data", cliente_col: "Cliente", mov_col: "MovRaw"})

    # 5) parse da Data
    df["Data"] = pd.to_datetime(df["Data"].astype(str), dayfirst=True, errors="coerce")

    # 6) Sim/Não -> 1/0
    df["Mov"] = df["MovRaw"].map(to_bin).astype(int)

    # 7) limpa e consolida duplicatas por dia/cliente
    df = df.dropna(subset=["Data", "Cliente"])
    df = df.groupby([df["Data"].dt.date, "Cliente"], as_index=False)["Mov"].max()
    df["Data"] = pd.to_datetime(df["Data"])

    # 8) ordena
    return df.sort_values(["Data", "Cliente"]).reset_index(drop=True)

# ===== Carrega com tratamento de erro =====
try:
    df = load_data()
except Exception as e:
    st.error("❌ Falha ao carregar os dados. Confira o gid/URL e os cabeçalhos.")
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
