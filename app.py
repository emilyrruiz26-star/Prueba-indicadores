import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Tablero SSI Cenoa", layout="wide", page_icon="📊")

st.title("📊 Control de Encuestas y SSI - Cenoa")
st.markdown("---")

# URL de tu hoja específica (gid=144090567 corresponde a 'ENCUESTA 11/25')
URL = "https://docs.google.com/spreadsheets/d/1FkD2pPwIUnCW4ieuEvTPruOtrtjWgH9ellpvezwiRm8/edit?gid=144090567#gid=144090567"

# 2. Conexión y Carga de Datos
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_and_clean_data():
    # Leer datos crudos
    raw_df = conn.read(spreadsheet=URL)
    
    # TRUCO: Si la fila 0 tiene los nombres (Dominio, Vendedor, Estado...), la promovemos
    df = raw_df.copy()
    df.columns = df.iloc[0] # La primera fila real se vuelve el encabezado
    df = df[1:].reset_index(drop=True) # Borramos la fila repetida
    
    # Limpiar nombres de columnas de espacios raros
    df.columns = [str(c).strip() for c in df.columns]
    
    # Limpiar columna %SSI (quitar el % y convertir a número)
    if "%SSI" in df.columns:
        df["%SSI_num"] = df["%SSI"].astype(str).str.replace('%', '').str.replace(',', '.')
        df["%SSI_num"] = pd.to_numeric(df["%SSI_num"], errors='coerce') / 100
        
    return df

try:
    data = load_and_clean_data()

    # --- SECCIÓN DE MÉTRICAS (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_encuestas = len(data)
        st.metric("Total General", f"{total_encuestas}")

    with col2:
        # Cálculo del SSI Promedio vs Objetivo 90%
        if "%SSI_num" in data.columns:
            ssi_actual = data["%SSI_num"].mean()
            objetivo = 0.90
            delta_val = (ssi_actual - objetivo) * 100
            st.metric(
                label="Resultado SSI", 
                value=f"{ssi_actual*100:.1f}%", 
                delta=f"{delta_val:.1f}% vs Obj. 90%",
                delta_color="normal" if ssi_actual >= objetivo else "inverse"
            )

    with col3:
        # Contar Respondidas
        respondidas = len(data[data["Estado"].str.contains("Respondida", case=False, na=False)])
        st.metric("Respondidas", respondidas)

    with col4:
        # Tasa de respuesta
        tasa = (respondidas / total_encuestas) * 100 if total_encuestas > 0 else 0
        st.metric("Tasa de Respuesta", f"{tasa:.1f}%")

    st.markdown("---")

    # --- SECCIÓN DE GRÁFICOS ---
    fila_graficos = st.columns([1, 1])

    with fila_graficos[0]:
        st.subheader("Estado de las Encuestas")
        if "Estado" in data.columns:
            # Gráfico de torta interactivo
            fig_pie = px.pie(
                data, 
                names="Estado", 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

    with fila_graficos[1]:
        st.subheader("Datos Detallados")
        # Mostramos la tabla filtrando solo columnas útiles
        columnas_ver = [c for c in data.columns if not c.endswith('_num')]
        st.dataframe(data[columnas_ver], height=350, use_container_width=True)

    # --- FILTRO ADICIONAL ---
    st.sidebar.header("Opciones de Visualización")
    vendedores = st.sidebar.multiselect("Filtrar por Vendedor", options=data["Vendedor"].unique())
    
    if vendedores:
        df_sub = data[data["Vendedor"].isin(vendedores)]
        st.subheader(f"Análisis para: {', '.join(vendedores)}")
        st.write(df_sub)

except Exception as e:
    st.error("Error al cargar la información.")
    st.exception(e)
    st.info("Asegúrate de que la hoja de Google Sheets tenga los encabezados en la primera fila y sea pública.")
