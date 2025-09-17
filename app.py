import pandas as pd
import streamlit as st
import altair as alt
import unicodedata
import re

# ===== URL CSV PUBLICADO =====
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxA4DyiFFBv-scpSoVShs0udQphFfPA7pmOg47FTxWIQQqY93enCr-razUSo_IvpDi8l-0JfQef7-E/pub?gid=0&single=true&output=csv"
CACHE_TTL = 900  # 15 min

# ===== Cores =====
COLOR_NO   = "#87CEEB"   
COLOR_YES  = "#0000CD"   
GRID_STROKE = "#E0E0E0"

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
    base = pd.read_csv(CSV_URL)
    base = try_header_from_first_row(base)

    # debug
    with st.expander("🔧 Debug (colunas e primeiras linhas)"):
        st.write("URL CSV:", CSV_URL)
        st.write("Colunas do CSV:", list(base.columns))
        st.dataframe(base.head())

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

    def infer_date_col(df: pd.DataFrame):
        best_col, best_ratio = None, 0.0
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                continue
            sample = pd.to_datetime(df[c].astype(str), dayfirst=True, errors="coerce").head(200)
            ratio = sample.notna().mean()
            if ratio > best_ratio:
                best_col, best_ratio = c, ratio
        return best_col if best_ratio >= 0.5 else None

    def infer_mov_col(df: pd.DataFrame, exclude: set):
        candidates = []
        for c in df.columns:
            if c in exclude:
                continue
            s = df[c].astype(str).str.strip().str.lower()
            good = s.isin({"sim","s","nao","não","n","0","1","true","false","t","f","yes","y","no"})
            score = good.mean()
            candidates.append((score, c))
        candidates.sort(reverse=True)
        return candidates[0][1] if candidates and candidates[0][0] >= 0.5 else None

    def infer_client_col(df: pd.DataFrame, exclude: set):
        for c in df.columns:
            if c in exclude: 
                continue
            if re.search(r"(cliente|empresa)", norm(c)):
                return c
        best, best_card = None, 0
        for c in df.columns:
            if c in exclude or pd.api.types.is_numeric_dtype(df[c]):
                continue
            card = df[c].nunique(dropna=True)
            if 1 < card < len(df) and card > best_card:
                best, best_card = c, card
        return best

    if not date_col:
        date_col = infer_date_col(base)
    if not cliente_col:
        cliente_col = infer_client_col(base, exclude={date_col} if date_col else set())
    if not mov_col:
        mov_col = infer_mov_col(base, exclude={date_col, cliente_col} if date_col and cliente_col else set())

    missing = []
    if not date_col:    missing.append("Data")
    if not cliente_col: missing.append("Cliente/Empresa")
    if not mov_col:     missing.append("Teve movimentação (Sim/Não)")
    st.write("🔎 Colunas escolhidas:", {"Data": date_col, "Cliente": cliente_col, "Mov": mov_col})
    if missing:
        raise ValueError(
            "Não encontrei as colunas esperadas: "
            + ", ".join(missing)
            + f". Colunas no CSV: {list(base.columns)}.\n"
            "Dica: ajuste os nomes na planilha OU adicione variações no código."
        )

    out = pd.DataFrame({
        "Data":    pd.to_datetime(base[date_col].astype(str), dayfirst=True, errors="coerce"),
        "Cliente": base[cliente_col].astype(str).str.strip(),
        "Mov":     base[mov_col].map(to_bin).astype(int)
    })

    out = out.dropna(subset=["Data", "Cliente"])
    out["Data"] = out["Data"].dt.floor("D")
    out = out.groupby(["Data", "Cliente"], as_index=False)["Mov"].max()
    return out.sort_values(["Data", "Cliente"]).reset_index(drop=True)

# ===== Carrega =====
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

# ---------- Grade semanal ----------
with tab_sem:
    st.subheader("Visão semanal (Seg–Sex)")

    if dfp.empty:
        st.info("Não há dados no período/cliente(s) selecionado(s).")
    else:
        semanas = sorted(dfp["Data"].dt.to_period("W-MON").unique())
        sem_padrao = max(semanas)
        idx_padrao = semanas.index(sem_padrao)
        sem_sel = st.selectbox(
            "Semana (início na segunda-feira)",
            options=semanas,
            index=idx_padrao,
            format_func=lambda p: f"{p.start_time.date()} – {(p.start_time + pd.Timedelta(days=4)).date()}"
        )

        dfw = dfp[dfp["Data"].dt.to_period("W-MON") == sem_sel].copy()
        dfw["dow"] = dfw["Data"].dt.weekday
        dfw = dfw[dfw["dow"] <= 4]

        clientes_semana = sorted(dfp["Cliente"].unique().tolist())

        grid = pd.MultiIndex.from_product([clientes_semana, range(5)], names=["Cliente", "dow"]).to_frame(index=False)
        agg = dfw.groupby(["Cliente", "dow"], as_index=False)["Mov"].max()
        mat = grid.merge(agg, on=["Cliente", "dow"], how="left").fillna({"Mov": 0})
        mat["Dia"] = mat["dow"].map({0: "Seg.", 1: "Ter.", 2: "Qua.", 3: "Qui.", 4: "Sex."})

        height = min(24 * max(1, len(clientes_semana)) + 80, 1000)

        chart_semana = alt.Chart(mat).mark_rect(stroke=GRID_STROKE, strokeWidth=0.7).encode(
            x=alt.X("Dia:N", sort=["Seg.", "Ter.", "Qua.", "Qui.", "Sex."], title=""),
            y=alt.Y("Cliente:N", sort=clientes_semana, title=""),
            color=alt.Color(
                "Mov:Q",
                scale=alt.Scale(domain=[0, 1], range=[COLOR_NO, COLOR_YES]),
                legend=None
            ),
            tooltip=[alt.Tooltip("Cliente:N"), alt.Tooltip("Dia:N"),
                     alt.Tooltip("Mov:Q", title="Teve movimentação (1=Sim, 0=Não)")]
        ).properties(height=height)

        st.altair_chart(chart_semana, use_container_width=True)

# ---------- Ranking semanal ----------
with tab_rank:
    st.subheader("Ranking de movimentações na semana selecionada")

    if dfp.empty:
        st.info("Não há dados para o ranking nessa semana.")
    else:
        dfw = dfp[dfp["Data"].dt.to_period("W-MON") == sem_sel].copy()
        resumo = dfw.groupby("Cliente", as_index=False)["Mov"].sum().sort_values("Mov", ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔝 Mais movimentações")
            st.dataframe(resumo.head(10))

        with col2:
            st.markdown("### 🔻 Menos movimentações")
            st.dataframe(resumo.tail(10).sort_values("Mov", ascending=True))

# ===== Botão de recarregar =====
st.divider()
if st.button("Atualizar dados agora"):
    load_data.clear()
    st.rerun()

st.caption("Lendo CSV publicado (pub?output=csv&gid=...). Ajuste o gid para a aba correta, se preciso. Cores: NÃO=azul claro, SIM=azul escuro.")
