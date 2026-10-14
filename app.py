import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from src.kinetics import calcular_cinetica

# Configuración inicial de la página
st.set_page_config(
    page_title="Bioreactor Kinetic Analyzer",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Bioreactor Batch Kinetic Analyzer")
st.markdown("""
Analizador automatizado de perfiles de fermentación. Aplica un **filtro de Savitzky-Golay** 
para mitigar el ruido experimental y calcula rendimientos ($Y_{P/S}$, $Y_{X/S}$), 
tasas volumétricas y velocidad específica de crecimiento ($\mu$).
""")

# --- BARRA LATERAL (CONFIGURACIÓN) ---
st.sidebar.header("⚙️ Parámetros del Filtro")
ventana = st.sidebar.slider(
    "Tamaño de ventana (puntos, impar):", 
    min_value=3, max_value=15, value=5, step=2
)
orden = st.sidebar.slider(
    "Orden del polinomio:", 
    min_value=1, max_value=4, value=2, step=1
)

# --- CARGA DE ARCHIVO ---
st.subheader("1. Carga de datos de fermentación")
archivo_subido = st.file_uploader(
    "Carga un archivo Excel (.xlsx) o CSV con columnas: Tiempo proceso (h), Glucosa (g/L), Etanol (g/L), Biomasa (g/L)",
    type=["xlsx", "csv"]
)

# Opción de usar datos de muestra si no se ha subido archivo
usar_muestra = st.checkbox("¿Usar datos de muestra de prueba (data/excelprueba.xlsx)?", value=(archivo_subido is None))

df = None

if archivo_subido is not None:
    if archivo_subido.name.endswith(".xlsx"):
        df = pd.read_excel(archivo_subido)
    else:
        df = pd.read_csv(archivo_subido)
elif usar_muestra:
    try:
        df = pd.read_excel("data/excelprueba.xlsx")
    except Exception:
        st.info("Sube tu archivo .xlsx o .csv arriba para comenzar el análisis.")

# --- PROCESAMIENTO Y VISUALIZACIÓN ---
if df is not None:
    try:
        # Usamos tu módulo de cálculo
        df_procesado, metricas = calcular_cinetica(df, ventana=ventana, orden=orden)

        st.subheader("2. Métricas y Rendimientos Calculados")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rendimiento $Y_{P/S}$", f"{metricas['Y_ps']} g/g")
        col2.metric("Rendimiento $Y_{X/S}$", f"{metricas['Y_xs']} g/g")
        col3.metric("Vel. máx. crecimiento ($\mu_{\max}$)", f"{metricas['mu_max']} h⁻¹")
        col4.metric("Vel. máx. formación etanol", f"{metricas['max_r_etanol']} g/L/h")

        # Gráfico interactivo con Plotly
        st.subheader("3. Perfil Cinético Filtrado")
        t = df_procesado["Tiempo proceso (h)"]

        fig = go.Figure()

        # Datos de Glucosa
        fig.add_trace(go.Scatter(
            x=t, y=df_procesado["Glucosa (g/L)"],
            mode="markers", name="Glucosa (exp)",
            marker=dict(color="rgba(31, 119, 180, 0.4)", size=8)
        ))
        fig.add_trace(go.Scatter(
            x=t, y=df_procesado["Glucosa_filtrada"],
            mode="lines", name="Glucosa (filtrada)",
            line=dict(color="#1f77b4", width=3)
        ))

        # Datos de Etanol
        fig.add_trace(go.Scatter(
            x=t, y=df_procesado["Etanol (g/L)"],
            mode="markers", name="Etanol (exp)",
            marker=dict(color="rgba(44, 160, 44, 0.4)", size=8),
            yaxis="y2"
        ))
        fig.add_trace(go.Scatter(
            x=t, y=df_procesado["Etanol_filtrada"],
            mode="lines", name="Etanol (filtrado)",
            line=dict(color="#2ca02c", width=3),
            yaxis="y2"
        ))

        # Configuración de ejes múltiples (sintaxis compatible con versiones recientes de Plotly)
        fig.update_layout(
            title="Curvas Cinéticas Suavizadas (Savitzky-Golay)",
            xaxis=dict(title=dict(text="Tiempo de proceso (h)")),
            yaxis=dict(
                title=dict(text="Glucosa (g/L)", font=dict(color="#1f77b4")),
                tickfont=dict(color="#1f77b4")
            ),
            yaxis2=dict(
                title=dict(text="Etanol (g/L)", font=dict(color="#2ca02c")),
                tickfont=dict(color="#2ca02c"),
                overlaying="y",
                side="right"
            ),
            legend=dict(x=0.01, y=0.99),
            template="plotly_white",
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        # Tabla de datos calculados
        with st.expander("Ver tabla completa de datos derivados y filtrados"):
            st.dataframe(df_procesado)

    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
