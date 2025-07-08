import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG PÁGINA ---
st.set_page_config(page_title="Painel de SKUs Inativos", layout="wide")

# --- CARREGA DADOS ---
CSV_URL = st.secrets ["CSV_URL"]
df = pd.read_csv(CSV_URL)

# --- PREPARAÇÃO ---
df.columns = df.columns.str.lower()
df['gmv_acumulado_periodo'] = pd.to_numeric(df['gmv_acumulado_periodo'], errors='coerce')
df['max_ordered_at'] = pd.to_datetime(df['max_ordered_at'], errors='coerce')
df['dias_desde_ultima_venda'] = (datetime.today() - df['max_ordered_at']).dt.days
df['dias_ativos'] = 365 - df['dias_desde_ultima_venda']
df['dias_ativos'] = df['dias_ativos'].clip(lower=1)
df['gmv_perdido_estimado'] = df.apply(
    lambda row: (row['gmv_acumulado_periodo'] / row['dias_ativos']) * row['dias_desde_ultima_venda']
    if row['dias_ativos'] >= 30 else 0,
    axis=1
).round(2)

# --- RENOMEIA PRAÇA E ORDENA ---
df = df.rename(columns={'zone_name': 'praca'})
df = df.sort_values(by='gmv_perdido_estimado', ascending=False)

# --- FILTROS ---
st.title("📋 Painel de SKUs Inativos por Praça")
pracas = df['praca'].dropna().unique()
praca_selecionada = st.selectbox("Selecione a praça:", sorted(pracas))
df_filtrado = df[df['praca'] == praca_selecionada].copy()

marcas = df_filtrado['brand_name'].dropna().unique()
marca_selecionada = st.selectbox("Filtrar por marca (opcional):", ["Todas"] + list(sorted(marcas)))
if marca_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['brand_name'] == marca_selecionada]

# --- RESUMO COM CAIXAS ---
st.subheader("Resumo da Praça")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div style='padding:1em; background-color:#1e1e1e; border-radius:8px; text-align:center;'>
        <h4 style='margin-bottom:0; color:#fff;'>GMV Total 12M</h4>
        <p style='font-size:24px; margin-top:0; color:#fff;'>R$ {df_filtrado['gmv_acumulado_periodo'].sum():,.0f}</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div style='padding:1em; background-color:#1e1e1e; border-radius:8px; text-align:center;'>
        <h4 style='margin-bottom:0; color:#fff;'>GMV Perdido Estimado</h4>
        <p style='font-size:24px; margin-top:0; color:#ff4d4d;'>R$ {df_filtrado['gmv_perdido_estimado'].sum():,.0f}</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div style='padding:1em; background-color:#1e1e1e; border-radius:8px; text-align:center;'>
        <h4 style='margin-bottom:0; color:#fff;'>SKUs Inativos</h4>
        <p style='font-size:24px; margin-top:0; color:#fff;'>{df_filtrado.shape[0]}</p>
    </div>
    """, unsafe_allow_html=True)
    



# --- FORMATAÇÃO TABELA ---
df_filtrado['GMV (12M)'] = df_filtrado['gmv_acumulado_periodo'].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)
df_filtrado['GMV Perdido'] = df_filtrado['gmv_perdido_estimado'].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)
df_filtrado['Selecionar'] = False

# --- BOTÕES TOPO ALINHADOS ---
# Espaçamento abaixo dos cards de resumo
st.markdown("<div style='margin-top: 30px'></div>", unsafe_allow_html=True)

# Alinha os botões à esquerda com espaçamento
with st.container():
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        if st.button("🔝 Selecionar Top 10 por GMV Perdido", key="btn_top_10", use_container_width=True):
            top_10_eans = df_filtrado.nlargest(10, 'gmv_perdido_estimado')['ean'].tolist()
            df_filtrado['Selecionar'] = df_filtrado['ean'].isin(top_10_eans)
    with col2:
        if st.button("✅ Selecionar Todos", key="btn_todos", use_container_width=True):
            df_filtrado['Selecionar'] = True
    with col3:
        st.download_button(
            label="⬇️ Baixar tabela completa da praça",
            data=df_filtrado.drop(columns=["Selecionar"]).to_csv(index=False).encode("utf-8"),
            file_name=f"skus_inativos_{praca_selecionada.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )

# --- TABELA COM CHECKBOX ---
df_editor = df_filtrado[[
    'Selecionar', 'ean', 'search_index', 'brand_name', 'manufacturer_name',
    'GMV (12M)', 'GMV Perdido', 'unidades_vendidas_periodo',
    'max_ordered_at', 'dias_desde_ultima_venda'
]].rename(columns={
    'ean': 'EAN',
    'search_index': 'Produto',
    'brand_name': 'Marca',
    'manufacturer_name': 'Fabricante',
    'unidades_vendidas_periodo': 'Unidades Vendidas',
    'max_ordered_at': 'Última Venda',
    'dias_desde_ultima_venda': 'Dias Inativo'
})

edited_df = st.data_editor(
    df_editor,
    use_container_width=True,
    height=800,
    column_config={
        "Selecionar": st.column_config.CheckboxColumn(required=False),
        "GMV (12M)": st.column_config.TextColumn(width="small"),
        "GMV Perdido": st.column_config.TextColumn(width="small"),
        "Dias Inativo": st.column_config.NumberColumn(format="%d", width="small")
    },
    disabled=["EAN", "Produto", "Marca", "Fabricante", "GMV (12M)", "GMV Perdido", "Unidades Vendidas", "Última Venda", "Dias Inativo"]
)

# --- SELECIONADOS E GMV INCREMENTAL ---
df_selecionados = edited_df[edited_df['Selecionar'] == True]
eans_selecionados = df_selecionados['EAN'].tolist()

if eans_selecionados:
    df_base = df[df['ean'].isin(eans_selecionados)].copy()
    df_base['meses_ativos'] = (df_base['dias_ativos'] / 30).clip(lower=1)
    df_base['gmv_mensal_estimado'] = df_base['gmv_acumulado_periodo'] / df_base['meses_ativos']
    gmv_mensal_estimado = df_base['gmv_mensal_estimado'].sum()
else:
    gmv_mensal_estimado = 0

valor_formatado = f"R$ {gmv_mensal_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
st.markdown(f"""
<div style='
    font-size:24px;
    margin-top:1.5em;
    padding:1em;
    border-radius:10px;
    background: linear-gradient(90deg, #003300 0%, #004d00 100%);
    color: #b6fcb6;
    font-weight: bold;
    border: 1px solid #00aa00;'>
    📈 <strong>Impacto estimado com reativação:</strong><br>
    <span style='color:#00ff00; font-size:28px;'>{valor_formatado}/mês</span>
</div>
""", unsafe_allow_html=True)

# --- TABELA DE SKUs SELECIONADOS ---
if not df_selecionados.empty:
    st.subheader("SKUs Selecionados para Ativação")
    st.dataframe(df_selecionados[['EAN', 'Produto', 'GMV (12M)', 'GMV Perdido']], use_container_width=True)

# --- DOWNLOAD CSV DOS SKUs SELECIONADOS ---
if not df_selecionados.empty:
    df_csv = df_selecionados[['EAN']].drop_duplicates()
    csv_bytes = df_csv.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📅 Baixar CSV para ativação",
        data=csv_bytes,
        file_name=f"ean_reativar_{praca_selecionada.lower().replace(' ', '_')}.csv",
        mime="text/csv"
    )


