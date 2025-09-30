import pandas as pd
import streamlit as st
import altair as alt
import unicodedata
import re

# ===== URL CSV PUBLICADO =====
# O SEU NOVO LINK CORRIGIDO PARA FORMATO CSV:
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsw_WO1DoVu76FQ7rhs1S8CPBo0FRQ7VmoCpZBGV9WTsRdZm7TduvnKQnTVKR40vbMzQU3ypTj8Ls7/pub?gid=212895287&single=true&output=csv"
CACHE_TTL = 900 # 15 min

# ===== Cores e Constantes =====
COLOR_NO  = "#87CEEB"
COLOR_YES = "#0000CD"
GRID_STROKE = "#E0E0E0"
# Adicione aqui clientes/e-mails internos que não devem aparecer (use letras minúsculas)
CLIENTES_EXCLUIDOS = {"xraly", "igor@consultingblue.com.br", "fernando@consultingblue.com.br"} 
DIAS_SEMANA = {0: "Seg.", 1: "Ter.", 2: "Qua.", 3: "Qui.", 4: "Sex."}

# ==============================================

st.set_page_config(page_title="Movimentação × Data", layout="wide")
st.title("Movimentação por Cliente × Data")

# ---------- utils ----------
def norm(s: str) -> str:
    if pd.isna(s) or s is None:
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
    expected_hits = {"data","cliente","empresa","teve movimentacao","teve movimentação","movimentacao","movimentação","mov", "início", "título"}
    if any(x in expected_hits for x in row0_norm):
        df2 = df.copy()
        df2.columns = df2.iloc[0].fillna("").astype(str)
        df2 = df2.iloc[1:].reset_index(drop=True)
        return df2
    return df

# --------------------------
@st.cache_data(ttl=CACHE_TTL)
def load_data():
    base = pd.read_csv(CSV_URL)
    base = try_header_from_first_row(base)

    colmap = {norm(c): c for c in base.columns}

    def pick(candidates):
        for cand in candidates:
            key = norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    # Mapeamento para colunas (agenda)
    date_col      = pick(["Início", "Data", "C"])
    title_col     = pick(["Título", "B"])
    end_col       = pick(["Fim", "D"])
    attendees_col = pick(["Participantes", "E"])
    mov_col       = pick(["Teve movimentação", "Movimentação", "Mov"])
    cliente_source_col = pick(["Cliente", "Empresa", "Participantes", "A"])


    if date_col is None or cliente_source_col is None:
        raise ValueError("Colunas essenciais (Data/Início ou Cliente/Participantes) não encontradas. Verifique o GID e os cabeçalhos.")

    # 1. Cria o DataFrame Detalhado (df_detailed)
    df_detailed_temp = pd.DataFrame({
        "Data_Completa": pd.to_datetime(base[date_col].astype(str), dayfirst=True, errors="coerce"),
        "Título": base[title_col].astype(str).str.strip() if title_col else "Sem Título",
        "Início_Str": base[date_col].astype(str).str.strip(), 
        "Fim_Str": base[end_col].astype(str).str.strip() if end_col else "",
        "Participantes": base[attendees_col].astype(str).str.strip() if attendees_col else "N/A",
    })
    
    df_detailed_temp = df_detailed_temp.dropna(subset=["Data_Completa"])
    df_detailed_temp["Data"] = df_detailed_temp["Data_Completa"].dt.floor("D")
    
    # Lógica de Movimentação
    if mov_col:
        df_detailed_temp["Mov"] = base[mov_col].map(to_bin).astype(int)
    else:
        df_detailed_temp["Mov"] = 1

    # Lógica de Cliente (Extrai o nome de usuário do primeiro e-mail da coluna)
    cliente_source = base[cliente_source_col].astype(str).str.strip().str.lower()
    if norm(cliente_source_col) in ["participantes", "e", "a"]:
        cliente_source = cliente_source.str.split(',').str[0].str.split('@').str[0].str.strip()
    
    df_detailed_temp["Cliente"] = cliente_source

    df_detailed_temp = df_detailed_temp.dropna(subset=["Cliente", "Data"])

    # Remove clientes excluídos do DataFrame detalhado
    excluded_clients = [c.lower() for c in CLIENTES_EXCLUIDOS]
    df_detailed_temp = df_detailed_temp[~df_detailed_temp["Cliente"].isin(excluded_clients)]
    
    # Garante que a coluna Cliente é string no detalhado (PREVENÇÃO DE ERRO)
    df_detailed = df_detailed_temp.copy()
    df_detailed["Cliente"] = df_detailed["Cliente"].astype(str)
    
    # 2. Cria o DataFrame Agregado (df_agg) para os gráficos de calor
    df_agg = df_detailed[["Data", "Cliente", "Mov"]].copy()
    
    # Garante que Cliente é string no agregado (PREVENÇÃO DE ERRO)
    df_agg["Cliente"] = df_agg["Cliente"].astype(str) 
    
    df_agg["Semana"] = df_agg["Data"] - pd.to_timedelta(df_agg["Data"].dt.weekday, unit="D")
    df_agg = df_agg.groupby(["Data", "Cliente", "Semana"], as_index=False)["Mov"].max()

    return df_agg.sort_values(["Data", "Cliente"]).reset_index(drop=True), df_detailed


# ===== Carrega =====
try:
    df, df_detailed_base = load_data() 
except Exception as e:
    st.error("❌ Falha ao carregar os dados. Confira o gid/URL e os cabeçalhos. (Erro: " + str(e) + ")")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Sua base está vazia após o processamento. Confira o GID/URL e se as colunas 'Data' e 'Cliente' estão sendo reconhecidas.")
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

# DataFrame DETALHADO FILTRADO (para o resumo)
df_detailed_filtered = df_detailed_base.loc[
    df_detailed_base["Cliente"].isin(sel) & 
    (df_detailed_base["Data"].dt.date >= start) & 
    (df_detailed_base["Data"].dt.date <= end)
].copy()

# ===== KPIs principais =====
st.divider()
st.header("📌 Resumo do período selecionado")

if not dfp.empty:
    total_clientes = dfp["Cliente"].nunique()
    total_mov = dfp["Mov"].sum()
    media_mov = total_mov / total_clientes if total_clientes > 0 else 0
    mov_por_dia = dfp.groupby("Data")["Mov"].sum()
    dia_top = mov_por_dia.idxmax().date()
    mov_top = mov_por_dia.max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes ativos", total_clientes)
    c2.metric("Total de movimentações", total_mov)
    c3.metric("Média por cliente", f"{media_mov:.1f}")
    c4.metric("Dia com mais mov.", f"{dia_top} ({mov_top})")
else:
    st.info("Nenhum dado para o período selecionado.")

# ===== Abas =====
tab_dia, tab_sem, tab_rank = st.tabs(["📅 Por dia", "🗓️ Semanal (Seg–Sex)", "🏆 Ranking semanal"])

# ---------- Heatmap diário + Resumo de Reuniões ----------
with tab_dia:
    
    if dfp.empty:
        st.info("Nenhum dado para o período/filtro selecionado.")
    else:
        # --- 1. HEATMAP ---
        st.subheader("Visualização Diária (Heatmap)")
        
        all_dates  = pd.to_datetime(pd.date_range(start, end, freq="D"))
        all_clients = sorted(dfp["Cliente"].unique().tolist())
        
        # Cria o grid com tipos consistentes
        grid = pd.MultiIndex.from_product([all_dates, all_clients], names=["Data", "Cliente"]).to_frame(index=False)
        grid["Cliente"] = grid["Cliente"].astype(str) # Garante que Cliente é string
        
        # DataFrame dfp para mesclagem, garantindo tipos
        dfp_merge = dfp[["Data", "Cliente", "Mov"]].copy()
        dfp_merge["Cliente"] = dfp_merge["Cliente"].astype(str)
        
        # A mesclagem deve funcionar agora
        data_final = grid.merge(dfp_merge, on=["Data", "Cliente"], how="left")
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
        ).properties(height=height).interactive()

        st.altair_chart(chart, use_container_width=True)

    # --- 2. RESUMO DAS REUNIÕES (Detalhes) ---
    st.divider()
    st.subheader("📝 Detalhes das Reuniões")
    
    if df_detailed_filtered.empty:
        st.info("Nenhuma reunião detalhada encontrada no período ou com os filtros selecionados.")
    else:
        start_summary = df_detailed_filtered["Data"].min().date()
        end_summary = df_detailed_filtered["Data"].max().date()
        
        summary_date = st.date_input(
            "Selecione o dia para ver os detalhes:",
            value=end_summary,
            min_value=start_summary,
            max_value=end_summary
        )

        summary_mask_date = df_detailed_filtered["Data"].dt.date == summary_date
        
        df_summary = df_detailed_filtered.loc[summary_mask_date].copy()
        
        if df_summary.empty:
            st.info(f"Nenhuma reunião encontrada para {summary_date.strftime('%d/%m/%Y')} com os clientes selecionados.")
        else:
            df_summary_display = df_summary[[
                "Início_Str", "Fim_Str", "Título", "Cliente", "Participantes"
            ]].sort_values("Início_Str")
            
            df_summary_display.columns = [
                "Início", "Fim", "Título da Reunião", "Cliente Principal", "Todos Participantes"
            ]
            
            st.markdown(f"**Reuniões em {summary_date.strftime('%d/%m/%Y')}**:")
            st.dataframe(
                df_summary_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={"Todos Participantes": st.column_config.Column(width="large")}
            )


# ---------- Grade semanal ----------
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
            format_func=lambda s: f"{s.date()} – {(s + pd.Timedelta(days=4)).date()}"
        )

        dfw = dfp[dfp["Semana"] == sem_sel].copy()
        dfw["dow"] = dfw["Data"].dt.weekday
        dfw = dfw[dfw["dow"] <= 4]

        clientes_semana = sorted(dfp["Cliente"].unique().tolist())

        grid = pd.MultiIndex.from_product([clientes_semana, range(5)], names=["Cliente", "dow"]).to_frame(index=False)
        agg = dfw.groupby(["Cliente", "dow"], as_index=False)["Mov"].max()
        mat = grid.merge(agg, on=["Cliente", "dow"], how="left").fillna({"Mov": 0})
        mat["Dia"] = mat["dow"].map(DIAS_SEMANA)

        height = min(24 * max(1, len(clientes_semana)) + 80, 1000)

        chart_semana = alt.Chart(mat).mark_rect(stroke=GRID_STROKE, strokeWidth=0.7).encode(
            x=alt.X("Dia:N", sort=list(DIAS_SEMANA.values()), title=""),
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
        dfw = dfp[dfp["Semana"] == sem_sel].copy() 
        resumo = dfw.groupby("Cliente", as_index=False)["Mov"].sum().sort_values("Mov", ascending=False)
        
        if resumo.empty:
            st.info("Nenhuma movimentação para esta semana.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 🔝 Mais movimentações")
                st.dataframe(resumo.head(10), hide_index=True)

            with col2:
                st.markdown("### 🔻 Menos movimentações")
                resumo_tail = resumo[resumo['Mov'] > 0].tail(10).sort_values("Mov", ascending=True)
                if resumo_tail.empty:
                    st.info("Todos os clientes ativos tiveram movimentação zero.")
                else:
                    st.dataframe(resumo_tail, hide_index=True)

# ===== Alertas =====
st.divider()
st.header("🔔 Alertas automáticos")

if df.empty:
    st.info("Sem dados no período selecionado para gerar alertas.")
else:
    semanas_com_dados = sorted(df["Semana"].unique(), reverse=True)
    if len(semanas_com_dados) < 2:
        st.info("Dados insuficientes (menos de duas semanas) para comparação.")
    else:
        sem_atual = semanas_com_dados[0]
        sem_ant = semanas_com_dados[1]

        df_atual = df[df["Semana"] == sem_atual]
        df_ant   = df[df["Semana"] == sem_ant]

        ativos_atual = set(df_atual["Cliente"].unique())
        ativos_ant   = set(df_ant["Cliente"].unique())

        inativos = ativos_ant - ativos_atual
        novos = ativos_atual - ativos_ant

        if inativos:
            st.warning(f"⚠️ {len(inativos)} clientes ficaram **inativos** (não movimentaram) em {sem_atual.date()}: {', '.join(list(inativos)[:5])}{'...' if len(inativos) > 5 else ''}")
        else:
            st.success(f"✅ Nenhum cliente que movimentou em {sem_ant.date()} ficou inativo na última semana ({sem_atual.date()}).")

        if novos:
            st.info(f"ℹ️ {len(novos)} clientes tiveram **primeira movimentação** (relativa ao período analisado) em {sem_atual.date()}: {', '.join(list(novos)[:5])}{'...' if len(novos) > 5 else ''}")

        mov_atual = df_atual["Mov"].sum()
        mov_ant   = df_ant["Mov"].sum()
        
        if mov_ant > 0:
            delta = (mov_atual - mov_ant) / mov_ant
            delta_perc = abs(delta*100)
            
            if delta < -0.2:
                st.error(f"📉 Queda de **{delta_perc:.1f}%** nas movimentações ({mov_ant}→{mov_atual}) em relação à semana anterior ({sem_ant.date()}).")
            elif delta > 0.2:
                st.success(f"📈 Aumento de **{delta_perc:.1f}%** nas movimentações ({mov_ant}→{mov_atual}) em relação à semana anterior ({sem_ant.date()}).")
            else:
                st.info(f"📊 Volume de movimentações estável ({mov_ant}→{mov_atual}, diferença de {delta*100:.1f}%) em relação à semana anterior ({sem_ant.date()}).")
        elif mov_atual > 0:
             st.success(f"📈 Grande aumento: {mov_atual} movimentações nesta semana, contra 0 na semana anterior.")
        else:
            st.info("Volume de movimentações é zero nas duas últimas semanas.")

# ===== Botão de recarregar =====
st.divider()
if st.button("Atualizar dados agora"):
    load_data.clear()
    st.rerun()

st.caption("Lendo CSV publicado (pub?output=csv&gid=...). Ajuste o gid para a aba correta. Cores: NÃO=azul claro, SIM=azul escuro.")
