import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Tablero SSI Cenoa", layout="wide")

st.title("📊 Control de Encuestas y SSI")

# URL de tu hoja (asegúrate que incluya el gid de la hoja "ENCUESTA 11/25")
URL = "https://docs.google.com/spreadsheets/d/1FkD2pPwIUnCW4ieuEvTPruOtrtjWgH9ellpvezwiRm8/edit?gid=144090567#gid=144090567"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def load_and_clean_data():
    # 1. Leer datos
    raw_df = conn.read(spreadsheet=URL)
    
    # 2. Corregir Encabezados (Usar la fila 0 como nombres de columna)
    df = raw_df.copy()
    df.columns = df.iloc[0] # Setea la fila 0 como nombres
    df = df[1:].reset_index(drop=True) # Elimina la fila 0 de los datos
    
    # Limpiar nombres de columnas (quitar espacios o saltos de línea)
    df.columns = [str(c).strip() for c in df.columns]
    return df

try:
    df = load_and_clean_data()

    # --- MÉTRICAS PRINCIPALES ---
    col1, col2, col3 = st.columns(3)

    # Cálculo de SSI (Asumiendo que la columna se llama "%SSI")
    # Convertimos a numérico por si vienen como texto
    if "%SSI" in df.columns:
        ssi_actual = pd.to_numeric(df["%SSI"], errors='coerce').mean()
        objetivo = 0.90
        
        with col1:
            color = "normal" if ssi_actual >= objetivo else "inverse"
            st.metric("Resultado SSI", f"{ssi_actual*100:.1f}%", 
                      delta=f"{(ssi_actual - objetivo)*100:.1f}% vs Objetivo",
                      delta_color=color)

    # --- GRÁFICOS ---
    left_chart, right_chart = st.columns(2)

    with left_chart:
        st.subheader("Estado de Encuestas")
        if "Estado" in df.columns:
            # Gráfico de Torta para Enviadas, Pendientes, Respondidas
            fig_pie = px.pie(df, names="Estado", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("No se encontró la columna 'Estado'")

    with right_chart:
        st.subheader("Detalle del Inventario")
        st.dataframe(df, height=400)

    # --- FILTRO POR VENDEDOR O SUCURSAL ---
    st.divider()
    sucursal = st.multiselect("Filtrar por Sucursal", options=df["Sucursal de entrega"].unique())
    if sucursal:
        df_filtered = df[df["Sucursal de entrega"].isin(sucursal)]
        st.write(df_filtered)

except Exception as e:
    st.error(f"Error procesando los datos: {e}")
    st.info("Revisa que los nombres de las columnas en el Excel coincidan exactamente con el código.")
