import pandas as pd
import streamlit as st
import altair as alt
import unicodedata
import re

# ===== URL CSV PUBLICADO =====
CSV_MOV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxA4DyiFFBv-scpSoVShs0udQphFfPA7pmOg47FTxWIQQqY93enCr-razUSo_IvpDi8l-0JfQef7-E/pub?gid=0&single=true&output=csv"
CSV_REUNIOES_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsw_WO1DoVu76FQ7rhs1S8CPBo0FRQ7VmoCpZBGV9WTsRdZm7TduvnKQnTVKR40vbMzQU3ypTj8Ls7/pub?gid=212895287&single=true&output=csv"
CACHE_TTL = 900  # 15 min

# ===== Cores =====
COLOR_NO   = "#87CEEB"   
COLOR_YES  = "#0000CD"   
GRID_STROKE = "#E0E0E0"

# ===== Clientes excluídos =====
CLIENTES_EXCLUIDOS = {"XRally"}   # coloque aqui outros clientes que não devem aparecer

# ==============================================

st.set_page_config(page_title="Movimentação × Data", layout="wide")
st.title("Movimentação por Cliente × Data")

# ---------- utils ----------
def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.strip().lower()

def to_bin(v) -> int:
    s = str(v).strip().lower()
    return 1 if s in {"sim","s","1","true","t","yes","y","ok","x"} else 0

def try_header_from_first_row(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    row0 = df.iloc[0].astype(str).tolist()
    row0_norm = [norm(x) for x in row0]
    expected_hits = {"data","cliente","empresa","teve movimentacao","teve movimentação","movimentacao","movimentação","mov"}
    if any(x in expected_hits for x in row0_norm):
        df2 = df.copy()
        df2.columns = df2.iloc[0]
        df2 = df2.iloc[1:].reset_index(drop=True)
        return df2
    return df

# --------------------------
@st.cache_data(ttl=CACHE_TTL)
def load_data():
    # Carrega dados de movimentação
    base = pd.read_csv(CSV_MOV_URL)
    base = try_header_from_first_row(base)

    colmap = {norm(c): c for c in base.columns}

    def pick(candidates):
        for cand in candidates:
            key = norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    date_col    = pick(["Data", "date", "DATA", "Dia"])
    cliente_col = pick(["Cliente", "Empresa", "Cliente/Empresa", "Nome do Cliente", "Client"])
    mov_col     = pick(["Teve movimentação", "Teve movimentacao", "Movimentação", "Movimentacao", "Mov", "Movimentou", "teve movimento"])

    out = pd.DataFrame({
        "Data":    pd.to_datetime(base[date_col].astype(str), dayfirst=True, errors="coerce"),
        "Cliente": base[cliente_col].astype(str).str.strip(),
        "Mov":     base[mov_col].map(to_bin).astype(int)
    })

    out = out.dropna(subset=["Data", "Cliente"])
    out["Data"] = out["Data"].dt.floor("D")

    # 🔑 Semana = sempre a segunda-feira da semana
    out["Semana"] = out["Data"] - pd.to_timedelta(out["Data"].dt.weekday, unit="D")

    out = out.groupby(["Data", "Cliente", "Semana"], as_index=False)["Mov"].max()

    # 🚫 Remove clientes excluídos
    out = out[~out["Cliente"].isin(CLIENTES_EXCLUIDOS)]

    return out.sort_values(["Data", "Cliente"]).reset_index(drop=True)

@st.cache_data(ttl=CACHE_TTL)
def load_reunioes_data():
    reunioes_df = pd.read_csv(CSV_REUNIOES_URL)
    reunioes_df['Início'] = pd.to_datetime(reunioes_df['Início'])
    reunioes_df['Fim'] = pd.to_datetime(reunioes_df['Fim'])
    return reunioes_df

# ===== Carrega =====
try:
    df = load_data()
    reunioes_df = load_reunioes_data()
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

# ===== KPIs principais =====
st.divider()
st.header("📌 Resumo do período selecionado")

if not dfp.empty:
    total_clientes = dfp["Cliente"].nunique()
    total_mov = dfp["Mov"].sum()
    media_mov = total_mov / total_clientes if total_clientes > 0 else 0
    dia_top = dfp.groupby("Data")["Mov"].sum().idxmax().date()
    mov_top = dfp.groupby("Data")["Mov"].sum().max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes ativos", total_clientes)
    c2.metric("Total de movimentações", total_mov)
    c3.metric("Média por cliente", f"{media_mov:.1f}")
    c4.metric("Dia com mais mov.", f"{dia_top} ({mov_top})")
else:
    st.info("Nenhum dado para o período selecionado.")

# ===== Reuniões do Dia =====
st.header("📅 Reuniões do Dia")
mask_reun = (reunioes_df['Início'].dt.date >= start) & (reunioes_df['Fim'].dt.date <= end)
reunioes_filtradas = reunioes_df[mask_reun]

if not reunioes_filtradas.empty:
    st.dataframe(reunioes_filtradas[['Agenda', 'Título', 'Início', 'Fim', 'Participantes']])
else:
    st.info("Não há reuniões para o período selecionado.")

# ===== Abas =====
tab_dia, tab_sem, tab_rank = st.tabs(["📅 Por dia", "🗓️ Semanal (Seg–Sex)", "🏆 Ranking semanal"])

# ---------- Heatmap diário ----------
with tab_dia:
    all_dates   = pd.date_range(start, end, freq="D")
    all_clients = sorted(dfp["Cliente"].unique().tolist())
    if not all_clients:
        st.info("Nenhum cliente no período/filtro selecionado.")
    else:
        grid = pd.MultiIndex.from_product([all_dates, all_clients], names=["Data", "Cliente"]).to_frame(index=False)
        data_final = grid.merge(dfp[["Data", "Cliente", "Mov"]], on=["Data", "Cliente"], how="left")
        data_final["Mov"] = data_final["Mov"].fillna(0).astype(int)

        height = min(24 * max(1, len(all_clients)) + 80, 1000)

        chart = alt.Chart(data_final).mark_rect(stroke=GRID_STROKE, strokeWidth=0.7).encode(
            x=alt.X("yearmonthdate(Data):O", title="Data"),
            y=alt.Y("Cliente:N", sort=all_clients, title="Cliente"),
            color=alt.Color(
                "Mov:Q",
                scale=alt.Scale(domain=[0, 1], range=[COLOR_NO, COLOR_YES]),
                legend=None
            ),
            tooltip=[
                alt.Tooltip("yearmonthdate(Data):O", title="Data"),
                alt.Tooltip("Cliente:N"),
                alt.Tooltip("Mov:Q", title="Teve movimentação (1=Sim, 0=Não)")
            ]
        ).properties(height=height)

        st.altair_chart(chart, use_container_width=True)

# ---------- Ranking semanal ----------
with tab_rank:
    st.subheader("Ranking de movimentações na semana selecionada")

    if dfp.empty:
        st.info("Não há dados para o ranking nessa semana.")
    else:
        dfw = dfp[dfp["Semana"] == sem_sel].copy()
        resumo = dfw.groupby("Cliente", as_index=False)["Mov"].sum().sort_values("Mov", ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔝 Mais movimentações")
            st.dataframe(resumo.head(10))

        with col2:
            st.markdown("### 🔻 Menos movimentações")
            st.dataframe(resumo.tail(10).sort_values("Mov", ascending=True))

# ===== Alertas =====
st.divider()
st.header("🔔 Alertas automáticos")

if dfp.empty:
    st.info("Sem dados no período selecionado para gerar alertas.")
else:
    sem_atual = dfp["Semana"].max()
    sem_ant = sem_atual - pd.Timedelta(days=7)

    df_atual = dfp[dfp["Semana"] == sem_atual]
    df_ant   = dfp[dfp["Semana"] == sem_ant]

    ativos_atual = set(df_atual["Cliente"].unique())
    ativos_ant   = set(df_ant["Cliente"].unique())

    inativos = ativos_ant - ativos_atual
    novos = ativos_atual - ativos_ant

    if inativos:
        st.warning(f"⚠️ {len(inativos)} clientes ficaram **inativos** nesta semana: {', '.join(list(inativos)[:10])}...")
    else:
        st.success("✅ Nenhum cliente ficou inativo nesta semana.")

    if novos:
        st.info(f"ℹ️ {len(novos)} clientes tiveram **primeira movimentação** nesta semana: {', '.join(list(novos)[:10])}...")

    mov_atual = df_atual["Mov"].sum()
    mov_ant   = df_ant["Mov"].sum()
    if mov_ant > 0:
        delta = (mov_atual - mov_ant) / mov_ant
        if delta < -0.2:
            st.error(f"📉 Queda de {abs(delta*100):.1f}% nas movimentações em relação à semana anterior.")
        elif delta > 0.2:
            st.success(f"📈 Aumento de {delta*100:.1f}% nas movimentações em relação à semana anterior.")
        else:
            st.info("📊 Volume de movimentações estável em relação à semana anterior.")

# ===== Botão de recarregar =====
st.divider()
if st.button("Atualizar dados agora"):
    load_data.clear()
    st.rerun()

st.caption("Lendo CSV publicado (pub?output=csv&gid=...). Ajuste o gid para a aba correta. Cores: NÃO=azul claro, SIM=azul escuro.")

