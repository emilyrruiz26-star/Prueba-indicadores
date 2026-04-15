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
    
    # --- PROCESAMIENTO DE FECHAS (Sin dependencia de Locale) ---
    if "Fecha de Entrega" in df.columns:
        df["Fecha de Entrega"] = pd.to_datetime(df["Fecha de Entrega"], dayfirst=True, errors='coerce')
        
        # Extraemos mes numérico y lo mapeamos a nombre manualmente
        meses_dict = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        df["Año"] = df["Fecha de Entrega"].dt.year.fillna(0).astype(int)
        df["Mes_Num"] = df["Fecha de Entrega"].dt.month.fillna(0).astype(int)
        df["Mes"] = df["Mes_Num"].map(meses_dict).fillna("Sin Fecha")
        
    # --- PROCESAMIENTO DE SSI (Corrección escala 0-100) ---
    if "%SSI" in df.columns:
        # Limpieza de caracteres
        df["%SSI_num"] = df["%SSI"].astype(str).str.replace('%', '').str.replace(',', '.')
        df["%SSI_num"] = pd.to_numeric(df["%SSI_num"], errors='coerce')
        
        # Lógica de escala: si los datos vienen como 7.9 para representar 79%,
        # multiplicamos por 10. Si vienen como 0.79, multiplicamos por 100.
        def corregir_escala(x):
            if pd.isna(x): return 0.0
            if x <= 1.0: return x * 100 # Caso 0.85 -> 85%
            if x < 10.0: return x * 10  # Caso 7.9 -> 79%
            return x                    # Caso 85.0 -> 85%
            
        df["%SSI_num"] = df["%SSI_num"].apply(corregir_escala)
        
    return df

try:
    data_full = load_and_clean_data()

    # --- FILTROS LATERALES ---
    st.sidebar.header("📅 Filtros Temporales")
    
    # Filtro de Año
    años_disponibles = sorted([a for a in data_full["Año"].unique() if a != 0], reverse=True)
    if not años_disponibles: años_disponibles = [0]
    año_sel = st.sidebar.multiselect("Seleccionar Año", options=años_disponibles, default=años_disponibles)

    # Filtro de Mes (Ordenado cronológicamente)
    df_meses_orden = data_full[["Mes", "Mes_Num"]].drop_duplicates().sort_values("Mes_Num")
    meses_opciones = df_meses_orden["Mes"].tolist()
    mes_sel = st.sidebar.multiselect("Seleccionar Mes", options=meses_opciones, default=meses_opciones)

    # Filtrado de los datos
    data = data_full[(data_full["Año"].isin(año_sel)) & (data_full["Mes"].isin(mes_sel))]

    # --- KPIs PRINCIPALES ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total General", len(data))

    with col2:
        if "%SSI_num" in data.columns:
            ssi_actual = data["%SSI_num"].mean()
            objetivo = 90.0
            delta_val = ssi_actual - objetivo
            st.metric(
                label="Resultado SSI", 
                value=f"{ssi_actual:.1f}%", 
                delta=f"{delta_val:.1f}% vs Obj. 90%",
                delta_color="normal" if ssi_actual >= objetivo else "inverse"
            )

    with col3:
        if "Estado" in data.columns:
            # Contamos respondidas buscando la palabra clave
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
            fig_pie.update_layout(showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Detalle de Unidades")
        # Columnas a ocultar del usuario final
        cols_no = ["%SSI_num", "Año", "Mes", "Mes_Num"]
        cols_mostrar = [c for c in data.columns if c not in cols_no]
        st.dataframe(data[cols_mostrar], height=400, use_container_width=True)

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
    st.info("Sugerencia: Revisa que la columna 'Fecha de Entrega' en el Excel tenga formato de fecha (ej. DD/MM/AAAA).")
