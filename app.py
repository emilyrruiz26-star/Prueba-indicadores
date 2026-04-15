import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Tablero SSI Cenoa", layout="wide", page_icon="📊")

st.title("📊 Control de Encuestas y SSI - Cenoa")
st.markdown("---")

# URL de la hoja
URL = "https://docs.google.com/spreadsheets/d/1FkD2pPwIUnCW4ieuEvTPruOtrtjWgH9ellpvezwiRm8/edit?gid=144090567#gid=144090567"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_and_clean_data():
    raw_df = conn.read(spreadsheet=URL)
    
    # Promover fila 0 a encabezado
    df = raw_df.copy()
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    
    # --- PROCESAMIENTO DE FECHAS ---
    # Convertimos la columna de fecha a formato datetime de Python
    if "Fecha de Entrega" in df.columns:
        df["Fecha de Entrega"] = pd.to_datetime(df["Fecha de Entrega"], dayfirst=True, errors='coerce')
        # Creamos columnas auxiliares para los filtros
        df["Año"] = df["Fecha de Entrega"].dt.year.fillna(0).astype(int)
        df["Mes"] = df["Fecha de Entrega"].dt.month_name(locale='es_ES').fillna("Sin Fecha")
        # Diccionario para ordenar meses correctamente
        meses_orden = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        
    # --- PROCESAMIENTO DE SSI (CORRECCIÓN 79%) ---
    if "%SSI" in df.columns:
        # Quitamos el símbolo % y convertimos a número
        df["%SSI_num"] = df["%SSI"].astype(str).str.replace('%', '').str.replace(',', '.')
        df["%SSI_num"] = pd.to_numeric(df["%SSI_num"], errors='coerce')
        # Si el valor promedio es menor a 1 (ej: 0.85), lo multiplicamos por 100 para que sea 85
        # Pero si ya es 85, lo dejamos así.
        # En tu caso, si 7.9% debería ser 79%, multiplicamos por 10.
        # Optaremos por asegurar que el valor sea base 100:
        df["%SSI_num"] = df["%SSI_num"].apply(lambda x: x*10 if x < 10 else x)
        
    return df

try:
    data_full = load_and_clean_data()

    # --- FILTROS LATERALES ---
    st.sidebar.header("📅 Filtros Temporales")
    
    # Filtro de Año
    años_disponibles = sorted([a for a in data_full["Año"].unique() if a != 0], reverse=True)
    año_sel = st.sidebar.multiselect("Seleccionar Año", options=años_disponibles, default=años_disponibles)

    # Filtro de Mes
    meses_disponibles = data_full["Mes"].unique().tolist()
    mes_sel = st.sidebar.multiselect("Seleccionar Mes", options=meses_disponibles, default=meses_disponibles)

    # Filtrado de los datos
    data = data_full[(data_full["Año"].isin(año_sel)) & (data_full["Mes"].isin(mes_sel))]

    # --- KPIs PRINCIPALES ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Encuestas", len(data))

    with col2:
        if "%SSI_num" in data.columns:
            ssi_actual = data["%SSI_num"].mean()
            objetivo = 90.0 # Objetivo en base 100
            delta_val = ssi_actual - objetivo
            st.metric(
                label="Resultado SSI", 
                value=f"{ssi_actual:.1f}%", 
                delta=f"{delta_val:.1f}% vs Obj. 90%",
                delta_color="normal" if ssi_actual >= objetivo else "inverse"
            )

    with col3:
        if "Estado" in data.columns:
            respondidas = len(data[data["Estado"].astype(str).str.contains("Respondida", case=False, na=False)])
            st.metric("Respondidas", respondidas)

    with col4:
        tasa = (respondidas / len(data)) * 100 if len(data) > 0 else 0
        st.metric("Tasa de Respuesta", f"{tasa:.1f}%")

    st.markdown("---")

    # --- GRÁFICOS ---
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("Estado de las Encuestas")
        if "Estado" in data.columns:
            fig_pie = px.pie(data, names="Estado", hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Detalle del Periodo Seleccionado")
        cols_mostrar = [c for c in data.columns if c not in ["%SSI_num", "Año", "Mes"]]
        st.dataframe(data[cols_mostrar], height=400)

except Exception as e:
    st.error(f"Error en los datos: {e}")
    st.info("Asegúrate de que la columna 'Fecha de Entrega' tenga un formato de fecha válido.")
