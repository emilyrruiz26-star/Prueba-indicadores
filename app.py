import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Portal Usados Cenoa", layout="wide")

st.title("🚗 Control de Inventario - Usados Cenoa")
st.markdown("Visualización en tiempo real de unidades disponibles.")

# URL de tu Google Sheet
url = "https://docs.google.com/spreadsheets/d/1FkD2pPwIUnCW4ieuEvTPruOtrtjWgH9ellpvezwiRm8/edit#gid=144090567"

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Lectura de datos (se usa ttl para cachear los datos por 10 min)
    df = conn.read(spreadsheet=url, ttl="10m")

    # --- LIMPIEZA DE DATOS ---
    # Eliminamos filas vacías si las hay
    df = df.dropna(how="all")

    # --- FILTROS EN BARRA LATERAL ---
    st.sidebar.header("Filtros de Búsqueda")
    
    # Asumiendo columnas típicas de inventario (ajustar según tus nombres de columna reales)
    # Si las columnas tienen nombres diferentes, cámbialas aquí:
    marca_col = "Marca" if "Marca" in df.columns else df.columns[0]
    modelo_col = "Modelo" if "Modelo" in df.columns else df.columns[1]

    marcas = st.sidebar.multiselect("Seleccione Marca", options=df[marca_col].unique())
    
    df_selection = df.copy()
    if marcas:
        df_selection = df[df[marca_col].isin(marcas)]

    # --- TABLEROS (Métricas) ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Unidades", len(df_selection))
    # Ejemplo de métrica de precio si existe la columna 'Precio'
    if "Precio" in df.columns:
        precio_avg = df_selection["Precio"].mean()
        col2.metric("Precio Promedio", f"${precio_avg:,.0f}")

    # --- VISUALIZACIÓN DE DATOS ---
    st.subheader("Listado de Unidades")
    st.dataframe(df_selection, use_container_width=True)

    # Gráfico simple de stock por marca
    st.subheader("Distribución por Marca")
    stock_chart = df_selection[marca_col].value_counts()
    st.bar_chart(stock_chart)

except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.info("Asegúrate de que el enlace de Google Sheets sea público o las credenciales estén configuradas.")
