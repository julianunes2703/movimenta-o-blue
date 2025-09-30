import pandas as pd
import streamlit as st
import altair as alt

# Carregar os dados
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSsw_WO1DoVu76FQ7rhs1S8CPBo0FRQ7VmoCpZBGV9WTsRdZm7TduvnKQnTVKR40vbMzQU3ypTj8Ls7/pub?gid=212895287&single=true&output=csv"
df = pd.read_csv(CSV_URL)

# Garantir que a coluna 'Data' seja do tipo datetime
df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')

# Filtros de data
start_date = st.date_input("Data Inicial", min_value=df['Data'].min(), max_value=df['Data'].max())
end_date = st.date_input("Data Final", min_value=df['Data'].min(), max_value=df['Data'].max())

# Convertendo start_date e end_date para datetime para garantir compatibilidade
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# Filtrar os dados com base na seleção de datas
filtered_df = df[(df['Data'] >= start_date) & (df['Data'] <= end_date)]

# Remover duplicatas com base na 'Data' e 'Título' da reunião
filtered_df = filtered_df.drop_duplicates(subset=['Data', 'Título'])

# Substituir e-mails por nomes (se possível, se houver uma lista de mapeamento)
# Para esse exemplo, vamos considerar que você já tem uma coluna com nomes. Se não, podemos melhorar com mais manipulação de dados.

# Exibir gráfico de participação dos funcionários
# Contar o número de reuniões em que cada participante esteve
participant_counts = filtered_df['Participantes'].str.split(",").explode().str.strip().value_counts().reset_index()
participant_counts.columns = ['Participante', 'Reuniões']

# Gráfico de barras com a quantidade de reuniões por participante
chart = alt.Chart(participant_counts).mark_bar().encode(
    x=alt.X('Participante:N', title='Participante'),
    y=alt.Y('Reuniões:Q', title='Número de Reuniões'),
    color='Participante:N',
    tooltip=['Participante:N', 'Reuniões:Q']
).properties(
    title="Número de Reuniões por Participante",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)

# Exibir gráfico de pizza de participação
pie_chart = alt.Chart(participant_counts).mark_arc().encode(
    theta='Reuniões:Q',
    color='Participante:N',
    tooltip=['Participante:N', 'Reuniões:Q']
).properties(
    title="Participação de Reuniões por Participante"
)

st.altair_chart(pie_chart, use_container_width=True)

# Mostrar os detalhes das reuniões por participante
st.write("Detalhamento das Reuniões por Participante:")

# Agrupar e exibir reuniões por participante
for participant in participant_counts['Participante']:
    st.write(f"**{participant}**:")
    participant_meetings = filtered_df[filtered_df['Participantes'].str.contains(participant)]
    for _, row in participant_meetings.iterrows():
        st.write(f"- **{row['Título']}** em {row['Data'].strftime('%d/%m/%Y')}")
    st.write("---")
