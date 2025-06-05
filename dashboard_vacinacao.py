import pandas as pd
import streamlit as st
import plotly.express as px

# --- INSTRUÇÕES DE INSTALAÇÃO E USO ---
# Para rodar este dashboard no seu computador:
# 1. Certifique-se de ter o Python instalado (versão 3.7 ou superior é recomendada).
# 2. Abra seu terminal ou prompt de comando (cmd no Windows, Terminal no macOS/Linux).
# 3. Use o seguinte comando para instalar as bibliotecas necessárias:
#    pip install pandas streamlit plotly
# 4. Salve este código Python em um arquivo, por exemplo, 'dashboard_vacinacao.py'.
# 5. Coloque o arquivo 'vacinacao_mar_2025--.csv' na **mesma pasta** onde você salvou 'dashboard_vacinacao.py'.
# 6. No terminal/prompt de comando, navegue até essa pasta usando 'cd sua_pasta'.
# 7. Execute o dashboard com o comando:
#    streamlit run dashboard_vacinacao.py
# 8. Um navegador web será aberto automaticamente com o dashboard.
# ------------------------------------

# --- Configurações da Página Streamlit ---
st.set_page_config(layout="wide", page_title="Registro de Vacinação")

# --- Carregar Dados (Função para cachear e otimizar) ---
# O cache (@st.cache_data) armazena em memória o DataFrame após a primeira carga,
# evitando que o arquivo CSV seja lido novamente a cada interação do usuário,
# o que é crucial para bases de dados grandes.
@st.cache_data
def load_data():
    try:
        # Tente 'latin1' primeiro para resolver problemas de codificação.
        # Se persistir o erro, mude para 'cp1252'.
        df = pd.read_csv('vacinacao_mar_2025--1.csv', sep=';', encoding='latin1')
        # Alternativa caso 'latin1' não funcione:
        # df = pd.read_csv('vacinacao_mar_2025--.csv', sep=';', encoding='cp1252')
    except FileNotFoundError:
        st.error("Erro: O arquivo 'vacinacao_mar_2025--.csv' não foi encontrado.")
        st.error("Por favor, certifique-se de que o arquivo CSV está na mesma pasta do script Python.")
        st.stop() # Interrompe a execução do Streamlit se o arquivo não for encontrado

    # Pré-processamento
    # Conversão da coluna de data para o formato datetime
    # 'errors='coerce'' transforma valores inválidos em NaT (Not a Time)
    df['dt_vacina'] = pd.to_datetime(df['dt_vacina'], format='%d/%m/%Y', errors='coerce')

    # Remover linhas onde a data é inválida/NaT
    df.dropna(subset=['dt_vacina'], inplace=True)

    # Adicionar uma coluna 'Dose' com valor 1 para facilitar a contagem de doses
    df['Dose'] = 1

    # --- Otimização de Tipos de Dados ---
    # Convertendo colunas de string que têm um número limitado de valores únicos para 'category'.
    # Isso pode economizar muita memória e acelerar operações de agrupamento/filtragem.
    categorical_cols = [
        'tp_sexo_paciente', 'no_raca_cor_paciente', 'sg_uf_estabelecimento',
        'ds_vacina', 'ds_vacina_fabricante'
    ]
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')

    # Otimizando 'nu_idade_paciente' para um tipo inteiro menor, se apropriado.
    # Isso reduz o uso de memória se as idades estiverem dentro de uma faixa menor.
    if 'nu_idade_paciente' in df.columns:
        # Garante que a coluna é numérica antes de tentar converter para int
        df['nu_idade_paciente'] = pd.to_numeric(df['nu_idade_paciente'], errors='coerce').fillna(0).astype(int)

        idade_max = df['nu_idade_paciente'].max()
        idade_min = df['nu_idade_paciente'].min()

        # int8 vai de -128 a 127
        if idade_max <= 127 and idade_min >= -128:
            df['nu_idade_paciente'] = df['nu_idade_paciente'].astype('int8')
        # int16 vai de -32768 a 32767
        elif idade_max <= 32767 and idade_min >= -32768:
            df['nu_idade_paciente'] = df['nu_idade_paciente'].astype('int16')
        # int32 para idades maiores, mas ainda dentro de um limite comum
        elif idade_max <= 2147483647 and idade_min >= -2147483648:
             df['nu_idade_paciente'] = df['nu_idade_paciente'].astype('int32')


    return df

# --- Chamada da função load_data() para carregar o DataFrame ---
# Esta linha executa a função load_data() e armazena o DataFrame resultante na variável 'df'.
# Graças ao @st.cache_data, esta execução completa (com leitura do CSV) só acontece na primeira vez.
df = load_data()

# --- Título do Dashboard ---
st.title("💉 Registro de Vacinação")

# --- Sidebar para Filtros ---
st.sidebar.header("Filtros")

# Filtro de Data
# Obter a menor e a maior data para definir os limites do seletor
# Adicione um tratamento para o caso de não haver datas válidas
if not df['dt_vacina'].empty:
    min_date = df['dt_vacina'].min().date()
    max_date = df['dt_vacina'].max().date()
else:
    # Se não houver datas válidas, defina um intervalo padrão para evitar o erro
    min_date = pd.to_datetime('2024-01-01').date() # Exemplo de data padrão
    max_date = pd.to_datetime('2025-12-31').date() # Exemplo de data padrão
    st.warning("Nenhuma data válida encontrada nos dados. Usando intervalo de data padrão.")

date_range = st.sidebar.date_input(
    "Selecione o Intervalo de Data",
    value=(min_date, max_date), # Valor inicial do seletor
    min_value=min_date,
    max_value=max_date
)

# Aplicar o filtro de data. df_filtered será o DataFrame base para os próximos filtros e gráficos.
if len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df[(df['dt_vacina'].dt.date >= start_date) & (df['dt_vacina'].dt.date <= end_date)]
else:
    # Se por algum motivo apenas uma data for selecionada, usa o DataFrame completo como base inicial
    df_filtered = df.copy()

# Os próximos filtros são aplicados em cascata sobre o df_filtered
# Filtro de Sexo
selected_sexo = st.sidebar.multiselect(
    "Sexo do Paciente",
    options=df_filtered['tp_sexo_paciente'].unique(),
    default=df_filtered['tp_sexo_paciente'].unique() # Todas as opções selecionadas por padrão
)
df_filtered = df_filtered[df_filtered['tp_sexo_paciente'].isin(selected_sexo)]

# Filtro de Cor do Paciente
selected_raca_cor = st.sidebar.multiselect(
    "Cor do Paciente",
    options=df_filtered['no_raca_cor_paciente'].unique(),
    default=df_filtered['no_raca_cor_paciente'].unique()
)
df_filtered = df_filtered[df_filtered['no_raca_cor_paciente'].isin(selected_raca_cor)]

# Filtro de UF de Aplicação (usando a UF do estabelecimento, como no dashboard)
selected_uf_aplicacao = st.sidebar.multiselect(
    "UF de Aplicação (Estabelecimento)",
    options=df_filtered['sg_uf_estabelecimento'].unique(),
    default=df_filtered['sg_uf_estabelecimento'].unique()
)
df_filtered = df_filtered[df_filtered['sg_uf_estabelecimento'].isin(selected_uf_aplicacao)]

# Filtro de Tipo de Vacina (Coluna 'ds_vacina' foi identificada como o "Tipo de Vacina")
selected_tipo_vacina = st.sidebar.multiselect(
    "Tipo de Vacina",
    options=df_filtered['ds_vacina'].unique(),
    default=df_filtered['ds_vacina'].unique()
)
df_filtered = df_filtered[df_filtered['ds_vacina'].isin(selected_tipo_vacina)]

# Filtro de Idade (Slider)
# Garantir que min_idade e max_idade sejam numéricos para o slider
min_idade_df = int(df_filtered['nu_idade_paciente'].min())
max_idade_df = int(df_filtered['nu_idade_paciente'].max())
idade_range = st.sidebar.slider(
    "Idade do Paciente",
    min_value=min_idade_df,
    max_value=max_idade_df,
    value=(min_idade_df, max_idade_df) # Intervalo inicial completo
)
df_filtered = df_filtered[(df_filtered['nu_idade_paciente'] >= idade_range[0]) & (df_filtered['nu_idade_paciente'] <= idade_range[1])]

# --- Verificação de Dados Filtrados ---
# Se o DataFrame ficar vazio após os filtros, exibe uma mensagem e para a execução.
if df_filtered.empty:
    st.warning("Não há dados para os filtros selecionados. Por favor, ajuste os filtros.")
    st.stop() # Interrompe a execução do Streamlit para evitar erros nos gráficos

# --- KPIs na Parte Superior ---
# Calculando os Key Performance Indicators
total_doses = df_filtered.shape[0] # Contagem de linhas = total de doses
total_estados = df_filtered['sg_uf_estabelecimento'].nunique() # Contagem de UFs únicas
total_fabricantes = df_filtered['ds_vacina_fabricante'].nunique() # Contagem de fabricantes únicos

# Exibindo os KPIs em colunas para uma apresentação visual clara
col1, col2, col3 = st.columns(3)
# Formatando para milhões (Mi) se o número for grande, ou número inteiro caso contrário
col1.metric("Total de Doses", f"{total_doses:,.0f}" if total_doses < 1_000_000 else f"{total_doses / 1_000_000:.2f} Mi")
col2.metric("Estados Envolvidos", f"{total_estados}")
col3.metric("Fabricantes Distintos", f"{total_fabricantes}")

st.markdown("---") # Separador visual para melhor organização

# --- Layout dos Gráficos ---
# Usando st.columns para organizar os gráficos em uma grade
# A primeira linha terá o gráfico de barras por estado e o mapa
row1_col1, row1_col2 = st.columns([0.6, 0.4]) # Proporção 60% para barras, 40% para o mapa

with row1_col1:
    st.subheader("Total de Doses por Estado")
    # Agrupando por UF e somando as doses
    df_uf_doses = df_filtered.groupby('sg_uf_estabelecimento')['Dose'].sum().reset_index()
    # Ordenando os estados pela quantidade de doses em ordem decrescente para o gráfico de barras
    df_uf_doses = df_uf_doses.sort_values(by='Dose', ascending=False)
    fig_uf_doses = px.bar(
        df_uf_doses,
        x='sg_uf_estabelecimento', # UF no eixo X
        y='Dose', # Doses no eixo Y
        title="Doses por UF de Aplicação",
        labels={'sg_uf_estabelecimento': 'UF', 'Dose': 'Total de Doses'},
        color_discrete_sequence=px.colors.qualitative.Plotly # Paleta de cores padrão do Plotly
    )
    st.plotly_chart(fig_uf_doses, use_container_width=True) # Exibe o gráfico, ajusta à largura do container

with row1_col2:
    st.subheader("Mapa de Doses por UF")
    # Para o mapa coroplético do Brasil, Plotly Express tem um bom suporte.
    # 'geojson' aponta para um arquivo GeoJSON com os limites dos estados brasileiros.
    # 'locations' usa a coluna de siglas das UFs do DataFrame.
    # 'featureidkey' mapeia a coluna de locations com a propriedade de identificação do GeoJSON.
    fig_map = px.choropleth(
        df_uf_doses,
        geojson="https://raw.githubusercontent.com/codeforamerica/click-that-hood/master/geojson/brazil-states.geojson",
        locations='sg_uf_estabelecimento',
        featureidkey="properties.UF_05", # Chave do GeoJSON que corresponde à sigla da UF
        color='Dose',
        color_continuous_scale="Viridis", # Escala de cores contínua (ex: de roxo para amarelo)
        scope="south america", # Foca na América do Sul
        projection="mercator", # Projeção geográfica adequada para mapas regionais
        title="Distribuição de Doses por Estado no Brasil",
        labels={'Dose': 'Total de Doses'}
    )
    fig_map.update_geos(fitbounds="locations", visible=False) # Ajusta o mapa para os limites dos dados e remove bordas
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}) # Margens mínimas para o mapa
    st.plotly_chart(fig_map, use_container_width=True)

# A segunda linha terá três gráficos: doses por raça, doses por sexo e doses por fabricante
row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    st.subheader("Quantidade de Doses por Raça")
    df_raca_doses = df_filtered.groupby('no_raca_cor_paciente')['Dose'].sum().reset_index()
    fig_raca_doses = px.pie(
        df_raca_doses,
        values='Dose',
        names='no_raca_cor_paciente',
        title="Doses por Raça/Cor",
        hole=0.4, # Cria um gráfico de donut (pizza com centro vazado)
        color_discrete_sequence=px.colors.qualitative.Pastel # Paleta de cores suaves
    )
    st.plotly_chart(fig_raca_doses, use_container_width=True)

with row2_col2:
    st.subheader("Quantidade de Doses por Sexo")
    df_sexo_doses = df_filtered.groupby('tp_sexo_paciente')['Dose'].sum().reset_index()
    fig_sexo_doses = px.pie(
        df_sexo_doses,
        values='Dose',
        names='tp_sexo_paciente',
        title="Doses por Sexo",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe # Outra paleta de cores
    )
    st.plotly_chart(fig_sexo_doses, use_container_width=True)

with row2_col3:
    st.subheader("Total de Doses por Fabricante")
    df_fabricante_doses = df_filtered.groupby('ds_vacina_fabricante')['Dose'].sum().reset_index()
    # Pega os 10 maiores fabricantes para uma visualização mais clara e performática
    df_fabricante_doses = df_fabricante_doses.sort_values(by='Dose', ascending=False).head(10)
    fig_fabricante_doses = px.bar(
        df_fabricante_doses,
        x='Dose',
        y='ds_vacina_fabricante',
        orientation='h', # Barras horizontais
        title="Top 10 Fabricantes por Doses",
        labels={'ds_vacina_fabricante': 'Fabricante', 'Dose': 'Total de Doses'},
        color_discrete_sequence=px.colors.qualitative.Vivid
    )
    # Ordena as barras em ordem crescente para que a maior fique no topo
    fig_fabricante_doses.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_fabricante_doses, use_container_width=True)

st.markdown("---")
st.markdown("Este dashboard é um modelo baseado na amostra de dados fornecida e busca replicar as visualizações do dashboard anexado. Os dados e as visualizações podem não refletir o cenário completo ou exato da vacinação.")