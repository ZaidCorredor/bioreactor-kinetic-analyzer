import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

        # --- 3. VISUALIZACIÓN MULTIPANEL ---
        st.subheader("3. Perfiles Cinéticos y Análisis de Tasas")

        tab_global, tab_biomasa, tab_tasas = st.tabs([
            "📊 Perfil Global (S, P, X)", 
            "🧫 Crecimiento Celular (X y μ)", 
            "⚡ Tasas Volumétricas (rP, -rS)"
        ])

        t = df_procesado["Tiempo proceso (h)"]
        col_bio_filt = "Biomasa_filtrada" if "Biomasa_filtrada" in df_procesado.columns else "Biomasa (g/L)"

        # ==========================================
        # PESTAÑA 1: PERFIL GLOBAL CON BIOMASA
        # ==========================================
        with tab_global:
            fig_global = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=("Sustrato (Glucosa) y Producto (Etanol)", "Crecimiento de Biomasa (X)")
            )

            # Panel 1: Glucosa y Etanol
            if "Glucosa (g/L)" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Glucosa (g/L)"], mode="markers",
                    name="Glucosa (exp)", marker=dict(color="rgba(31, 119, 180, 0.4)", size=7)
                ), row=1, col=1)
                
            if "Glucosa_filtrada" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Glucosa_filtrada"], mode="lines",
                    name="Glucosa (filtrada)", line=dict(color="#1f77b4", width=2.5)
                ), row=1, col=1)

            if "Etanol (g/L)" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Etanol (g/L)"], mode="markers",
                    name="Etanol (exp)", marker=dict(color="rgba(44, 160, 44, 0.4)", size=7)
                ), row=1, col=1)
                
            if "Etanol_filtrada" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Etanol_filtrada"], mode="lines",
                    name="Etanol (filtrado)", line=dict(color="#2ca02c", width=2.5)
                ), row=1, col=1)

            # Panel 2: Biomasa
            if "Biomasa (g/L)" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Biomasa (g/L)"], mode="markers",
                    name="Biomasa (exp)", marker=dict(color="rgba(214, 39, 40, 0.4)", size=7)
                ), row=2, col=1)
                
            if col_bio_filt in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado[col_bio_filt], mode="lines",
                    name="Biomasa (filtrada)", line=dict(color="#d62728", width=2.5)
                ), row=2, col=1)

            fig_global.update_layout(
                height=600,
                template="plotly_white",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_global.update_yaxes(title=dict(text="Concentración (g/L)"), row=1, col=1)
            fig_global.update_yaxes(title=dict(text="Biomasa (g/L)"), row=2, col=1)
            fig_global.update_xaxes(title=dict(text="Tiempo de proceso (h)"), row=2, col=1)

            st.plotly_chart(fig_global, use_container_width=True)

        # ==========================================
        # PESTAÑA 2: BIOMASA Y VELOCIDAD ESPECÍFICA (μ)
        # ==========================================
        with tab_biomasa:
            fig_mu = make_subplots(specs=[[{"secondary_y": True}]])

            if col_bio_filt in df_procesado.columns:
                fig_mu.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado[col_bio_filt],
                        name="Biomasa X (g/L)", line=dict(color="#d62728", width=2.5)
                    ), secondary_y=False
                )

            if "mu" in df_procesado.columns:
                fig_mu.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["mu"],
                        name="μ (h⁻¹)", line=dict(color="#9467bd", width=2.5, dash="dot")
                    ), secondary_y=True
                )

            fig_mu.update_layout(
                title=dict(text="Cinética de Crecimiento Celular y Velocidad Específica (μ)"),
                template="plotly_white",
                hovermode="x unified",
                height=450
            )
            fig_mu.update_xaxes(title=dict(text="Tiempo de proceso (h)"))
            fig_mu.update_yaxes(title=dict(text="Biomasa (g/L)", font=dict(color="#d62728")), secondary_y=False)
            fig_mu.update_yaxes(title=dict(text="μ (h⁻¹)", font=dict(color="#9467bd")), secondary_y=True)

            st.plotly_chart(fig_mu, use_container_width=True)

        # ==========================================
        # PESTAÑA 3: TASAS VOLUMÉTRICAS
        # ==========================================
        with tab_tasas:
            fig_rates = go.Figure()

            if "r_etanol" in df_procesado.columns:
                fig_rates.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_etanol"],
                    name="r_P (Formación Etanol)", line=dict(color="#2ca02c", width=2)
                ))
            if "r_glucosa" in df_procesado.columns:
                fig_rates.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_glucosa"],
                    name="-r_S (Consumo Glucosa)", line=dict(color="#1f77b4", width=2)
                ))

            fig_rates.update_layout(
                title=dict(text="Tasas Volumétricas Instantáneas dC/dt (g/L·h)"),
                xaxis=dict(title=dict(text="Tiempo de proceso (h)")),
                yaxis=dict(title=dict(text="Tasa volumétrica (g/L·h)")),
                template="plotly_white",
                height=450
            )
            st.plotly_chart(fig_rates, use_container_width=True)

        # --- TABLA DE DATOS Y EXPORTACIÓN ---
        with st.expander("📋 Ver tabla completa de datos derivados y filtrados"):
            st.dataframe(df_procesado)
            csv = df_procesado.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar datos cinéticos (CSV)",
                data=csv,
                file_name="cinetica_procesada.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
