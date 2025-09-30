import pandas as pd
import streamlit as st
import altair as alt
import unicodedata
import re

# =========================================================================
# ===== 1. URLS CSV PUBLICADAS (ATENÇÃO: SUBSTITUA O LINK ORIGINAL AQUI) =====
# =========================================================================

# URL da planilha ORIGINAL (Movimentação por Cliente) - SUBSTITUA AQUI!
CSV_URL_MOVIMENTACAO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxA4DyiFFBv-scpSoVShs0udQphFfPA7pmOg47FTfWIQQqY93enCr-razUSo_IvpDi8l-0JfQef7-E/pub?gid=0&single=true&output=csv" 

# URL da planilha NOVA (Ocorrência de Reuniões) - JÁ COM SEU LINK CORRIGIDO
CSV_URL_REUNIAO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsw_WO1DoVu76FQ7rhs1S8CPBo0FRQ7VmoCpZBGV9WTsRdZm7TduvnKQnTVKR40vbMzQU3ypTj8Ls7/pub?gid=212895287&single=true&output=csv"
CACHE_TTL = 900  # 15 min


# ===== Cores =====
COLOR_NO   = "#87CEEB"   
COLOR_YES  = "#0000CD"   
GRID_STROKE = "#E0E0E0"

# ===== Clientes excluídos =====
CLIENTES_EXCLUIDOS = {"XRally"}   # coloque aqui outros clientes que não devem aparecer


st.set_page_config(page_title="Movimentação × Reuniões", layout="wide")
st.title("Movimentação por Cliente vs. Ocorrência de Reuniões")

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

# Função adaptada para tentar pegar o cabeçalho (necessária para ambas as cargas)
def try_header_from_first_row(df: pd.DataFrame, expected_hits: set) -> pd.DataFrame:
    if df.empty:
        return df
    row0 = df.iloc[0].astype(str).tolist()
    row0_norm = [norm(x) for x in row0]
    if any(x in expected_hits for x in row0_norm):
        df2 = df.copy()
        df2.columns = df2.iloc[0]
        df2 = df2.iloc[1:].reset_index(drop=True)
        return df2
    return df

# --------------------------
# ===== Lógica de Carregamento ORIGINAL (Movimentação por Cliente) =====


    # ===== Lógica de Carregamento ORIGINAL (Movimentação por Cliente) =====
@st.cache_data(ttl=CACHE_TTL)
def load_data():
    # Hits originais (para a análise de cliente)
    expected_hits = {"data","cliente","empresa","teve movimentacao","teve movimentação","movimentacao","movimentação","mov"}
    
    # Usa a URL específica para Movimentação
    try:
        base = pd.read_csv(CSV_URL_MOVIMENTACAO)
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados de MOVIMENTAÇÃO. Verifique o link. Erro: {e}")
        return pd.DataFrame()
        
    base = try_header_from_first_row(base, expected_hits)

    colmap = {norm(c): c for c in base.columns}

    def pick(candidates):
        for cand in candidates:
            key = norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    date_col = pick(["Data", "date", "DATA", "Dia"])
    cliente_col = pick(["Cliente", "Empresa", "Cliente/Empresa", "Nome do Cliente", "Client"])
    mov_col = pick(["Teve movimentação", "Teve movimentacao", "Movimentação", "Movimentacao", "Mov", "Movimentou", "teve movimento"])
    
    if not date_col or not cliente_col or not mov_col:
        st.warning("Colunas do modo 'Movimentação por Cliente' não encontradas.")
        return pd.DataFrame()

    out = pd.DataFrame({
        "Data": pd.to_datetime(base[date_col].astype(str), dayfirst=True, errors="coerce"),
        "Cliente": base[cliente_col].astype(str).str.strip(),
        "Mov": base[mov_col].map(to_bin).astype(int)
    })

    out = out.dropna(subset=["Data", "Cliente"])
    out["Data"] = out["Data"].dt.floor("D")

    # 🔑 Semana = sempre a segunda-feira da semana
    out["Semana"] = out["Data"] - pd.to_timedelta(out["Data"].dt.weekday, unit="D")

    out = out.groupby(["Data", "Cliente", "Semana"], as_index=False)["Mov"].max()

    # 🚫 Remove clientes excluídos
    out = out[~out["Cliente"].isin(CLIENTES_EXCLUIDOS)]

    return out.sort_values(["Data", "Cliente"]).reset_index(drop=True)

# ===== Lógica de Carregamento ADICIONAL (Reuniões por Título) =====
@st.cache_data(ttl=CACHE_TTL)
def load_data_reunioes():
    # Hits para o novo modo (para a análise de reuniões)
    expected_hits = {"data","titulo","participantes"}
    
    # Usa a URL específica para Reuniões
    try:
        base = pd.read_csv(CSV_URL_REUNIAO)
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados de REUNIÕES. Verifique o link. Erro: {e}")
        return pd.DataFrame()

    base = try_header_from_first_row(base, expected_hits)

    colmap = {norm(c): c for c in base.columns}

    def pick(candidates):
        for cand in candidates:
            key = norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    date_col      = pick(["Data", "date", "DATA", "Dia"])
    titulo_col    = pick(["Titulo", "Título", "Name", "Reunião"]) # Título da reunião
    
    if not date_col or not titulo_col:
        st.warning("Colunas do modo 'Ocorrência de Reuniões' (Data ou Título) não encontradas.")
        return pd.DataFrame()

    out = pd.DataFrame({
        "Data":           pd.to_datetime(base[date_col].astype(str), dayfirst=True, errors="coerce"),
        "Titulo":         base[titulo_col].astype(str).str.strip(),
    })

    out = out.dropna(subset=["Data", "Titulo"])
    out["Data"] = out["Data"].dt.floor("D")

    # 🔑 O ponto chave: Agrupa por Data e Título para ter a ocorrência única (1) de cada reunião
    out["Ocorreu"] = 1
    out = out.groupby(["Data", "Titulo"], as_index=False)["Ocorreu"].max()

    # 🔑 Semana = sempre a segunda-feira da semana
    out["Semana"] = out["Data"] - pd.to_timedelta(out["Data"].dt.weekday, unit="D")

    return out.sort_values(["Data", "Titulo"]).reset_index(drop=True)

# ===== Carrega DADOS ORIGINAIS =====
try:
    df = load_data()
except Exception as e:
    # A mensagem de erro é tratada dentro de load_data se a URL falhar
    pass 

# ===== Carrega DADOS ADICIONAIS (Reuniões) =====
try:
    df_reunioes = load_data_reunioes()
except Exception as e:
    # A mensagem de erro é tratada dentro de load_data_reunioes se a URL falhar
    pass

# =========================================================================
# --- SEÇÃO 1: MOVIMENTAÇÃO POR CLIENTE (ORIGINAL) ---
# =========================================================================

st.markdown("## Análise 1: Movimentação por Cliente")
if df.empty:
    st.warning("A seção 'Movimentação por Cliente' não foi exibida. Verifique o link e os cabeçalhos da URL de Movimentação.")
else:
    # ===== Filtros (Original) =====
    dmin, dmax = df["Data"].min().date(), df["Data"].max().date()
    c1, c2 = st.columns(2)
    start = c1.date_input("Data inicial", value=dmin, min_value=dmin, max_value=dmax, key="start_mov")
    end   = c2.date_input("Data final",   value=dmax, min_value=dmin, max_value=dmax, key="end_mov")

    mask = (df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)
    dfp = df.loc[mask].copy()

    clientes = sorted(dfp["Cliente"].unique().tolist())
    sel = st.multiselect("Filtrar clientes (opcional)", clientes, default=clientes, key="sel_mov")
    dfp = dfp[dfp["Cliente"].isin(sel)]

    # ===== KPIs principais (Original) =====
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
        st.info("Nenhum dado de Movimentação para o período selecionado.")

    # ===== Abas (Original) =====
    tab_dia, tab_sem, tab_rank = st.tabs(["📅 Por dia", "🗓️ Semanal (Seg–Sex)", "🏆 Ranking semanal"])

    # ---------- Heatmap diário (Original) ----------
    with tab_dia:
        all_dates   = pd.date_range(start, end, freq="D")
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

    # ---------- Grade semanal (Original) ----------
    with tab_sem:
        st.subheader("Visão semanal (Seg–Sex)")

        if dfp.empty:
            st.info("Não há dados no período/cliente(s) selecionado(s).")
        else:
            semanas = sorted(dfp["Semana"].unique())
            sem_padrao = max(semanas)
            idx_padrao = semanas.index(sem_padrao)
            sem_sel = st.selectbox(
                "Semana (início na segunda-feira)",
                options=semanas,
                index=idx_padrao,
                format_func=lambda s: f"{s.date()} – {(s + pd.Timedelta(days=4)).date()}",
                key="sem_sel_mov"
            )

            dfw = dfp[dfp["Semana"] == sem_sel].copy()
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

    # ---------- Ranking semanal (Original) ----------
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

    # ===== Alertas (Original) =====
    st.divider()
    st.header("🔔 Alertas automáticos")

    if dfp.empty:
        st.info("Sem dados no período selecionado para gerar alertas.")
    else:
        sem_atual = dfp["Semana"].max()
        sem_ant = sem_atual - pd.Timedelta(days=7)

        df_atual = dfp[dfp["Semana"] == sem_atual]
        df_ant   = dfp[dfp["Semana"] == sem_ant]

        ativos_atual = set(df_atual["Cliente"].unique())
        ativos_ant   = set(df_ant["Cliente"].unique())

        inativos = ativos_ant - ativos_atual
        novos = ativos_atual - ativos_ant

        if inativos:
            st.warning(f"⚠️ {len(inativos)} clientes ficaram **inativos** nesta semana: {', '.join(list(inativos)[:10])}...")
        else:
            st.success("✅ Nenhum cliente ficou inativo nesta semana.")

        if novos:
            st.info(f"ℹ️ {len(novos)} clientes tiveram **primeira movimentação** nesta semana: {', '.join(list(novos)[:10])}...")

        mov_atual = df_atual["Mov"].sum()
        mov_ant   = df_ant["Mov"].sum()
        if mov_ant > 0:
            delta = (mov_atual - mov_ant) / mov_ant
            if delta < -0.2:
                st.error(f"📉 Queda de {abs(delta*100):.1f}% nas movimentações em relação à semana anterior.")
            elif delta > 0.2:
                st.success(f"📈 Aumento de {delta*100:.1f}% nas movimentações em relação à semana anterior.")
            else:
                st.info("📊 Volume de movimentações estável em relação à semana anterior.")


---
# ## Análise 2: Ocorrência de Reuniões Únicas (Adicional)
---

if df_reunioes.empty:
    st.warning("A seção 'Ocorrência de Reuniões' não foi exibida. Verifique o link e os cabeçalhos ('Data' e 'Título') da URL de Reuniões.")
else:
    # ===== Filtros de Reuniões =====
    dmin_r, dmax_r = df_reunioes["Data"].min().date(), df_reunioes["Data"].max().date()
    c1_r, c2_r = st.columns(2)
    start_r = c1_r.date_input("Data inicial (Reuniões)", value=dmin_r, min_value=dmin_r, max_value=dmax_r, key="start_r")
    end_r   = c2_r.date_input("Data final (Reuniões)",    value=dmax_r, min_value=dmin_r, max_value=dmax_r, key="end_r")

    mask_r = (df_reunioes["Data"].dt.date >= start_r) & (df_reunioes["Data"].dt.date <= end_r)
    dfp_r = df_reunioes.loc[mask_r].copy()

    titulos = sorted(dfp_r["Titulo"].unique().tolist())
    sel_r = st.multiselect("Filtrar reuniões (opcional)", titulos, default=titulos, key="sel_r")
    dfp_r = dfp_r[dfp_r["Titulo"].isin(sel_r)]

    st.subheader("Ocorrência de Reuniões por Dia (Heatmap)")

    if dfp_r.empty:
        st.info("Nenhuma reunião no período/filtro selecionado.")
    else:
        # Preparação do Heatmap (Ocorrência de Reuniões)
        all_dates_r = pd.date_range(start_r, end_r, freq="D")
        all_titulos = sorted(dfp_r["Titulo"].unique().tolist())
        
        # Grid completo para preencher os dias sem ocorrência (valor 0)
        grid_r = pd.MultiIndex.from_product([all_dates_r, all_titulos], names=["Data", "Titulo"]).to_frame(index=False)
        data_final_r = grid_r.merge(dfp_r[["Data", "Titulo", "Ocorreu"]], on=["Data", "Titulo"], how="left")
        data_final_r["Ocorreu"] = data_final_r["Ocorreu"].fillna(0).astype(int) # 0 se não ocorreu

        # Cores ajustadas para Reuniões (diferente do original)
        COLOR_R_NO = "#E0E0E0"  # Cinza claro para 'Não ocorreu'
        COLOR_R_YES = "#0000CD" # Azul escuro para 'Ocorreu'
        
        height_r = min(24 * max(1, len(all_titulos)) + 80, 1000)

        chart_reunioes = alt.Chart(data_final_r).mark_rect(stroke=GRID_STROKE, strokeWidth=0.7).encode(
            x=alt.X("yearmonthdate(Data):O", title="Data"),
            y=alt.Y("Titulo:N", sort=all_titulos, title="Reunião"),
            color=alt.Color(
                "Ocorreu:Q",
                scale=alt.Scale(domain=[0, 1], range=[COLOR_R_NO, COLOR_R_YES]),
                legend=None
            ),
            tooltip=[
                alt.Tooltip("yearmonthdate(Data):O", title="Data"),
                alt.Tooltip("Titulo:N", title="Reunião"),
                alt.Tooltip("Ocorreu:Q", title="Ocorreu (1=Sim, 0=Não)")
            ]
        ).properties(height=height_r)

        st.altair_chart(chart_reunioes, use_container_width=True)


# ===== Botão de recarregar =====
st.divider()
if st.button("Atualizar dados agora"):
    load_data.clear()
    load_data_reunioes.clear()
    st.rerun()

st.caption("A URL da seção de Reuniões foi atualizada. Lembre-se de substituir o link `CSV_URL_MOVIMENTACAO` pela sua URL de Movimentação.")




