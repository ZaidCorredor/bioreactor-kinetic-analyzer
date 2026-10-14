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
**velocidades volumétricas de reacción** ($r_i$) y **velocidades específicas de reacción** ($q_i$, $\mu$).
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
        df_procesado, metricas = calcular_cinetica(df, ventana=ventana, orden=orden)

        st.subheader("2. Métricas y Parámetros Cinéticos Globales")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rendimiento $Y_{P/S}$", f"{metricas['Y_ps']} g/g")
        col2.metric("Rendimiento $Y_{X/S}$", f"{metricas['Y_xs']} g/g")
        col3.metric("Vel. máx. crecimiento ($\mu_{\max}$)", f"{metricas['mu_max']} h⁻¹")
        col4.metric("Vel. máx. formación etanol ($r_{P,\max}$)", f"{metricas['max_r_P']} g/(L·h)")

        # --- 3. VISUALIZACIÓN MULTIPANEL ---
        st.subheader("3. Perfiles Cinéticos y Análisis de Velocidades")

        tab_global, tab_volumetrica, tab_especifica = st.tabs([
            "📊 Perfil de Concentraciones (S, P, X)", 
            "⚡ Velocidades Volumétricas (r)", 
            "🔬 Velocidades Específicas (q, μ)"
        ])

        t = df_procesado["Tiempo proceso (h)"]
        col_bio_filt = "Biomasa_filtrada" if "Biomasa_filtrada" in df_procesado.columns else "Biomasa (g/L)"

        # ==========================================
        # PESTAÑA 1: PERFIL DE CONCENTRACIONES (S, P, X)
        # ==========================================
        with tab_global:
            fig_global = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.15,
                subplot_titles=("Sustrato (Glucosa) y Producto (Etanol)", "Crecimiento de Biomasa (X)")
            )

            # Panel 1: Glucosa y Etanol
            if "Glucosa (g/L)" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Glucosa (g/L)"], mode="markers",
                    name="Glucosa (exp)", marker=dict(color="#1f77b4", opacity=0.45, size=7)
                ), row=1, col=1)
                
            if "Glucosa_filtrada" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Glucosa_filtrada"], mode="lines",
                    name="Glucosa (filtrada)", line=dict(color="#1f77b4", width=2.5)
                ), row=1, col=1)

            if "Etanol (g/L)" in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado["Etanol (g/L)"], mode="markers",
                    name="Etanol (exp)", marker=dict(color="#2ca02c", opacity=0.45, size=7)
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
                    name="Biomasa (exp)", marker=dict(color="#d62728", opacity=0.45, size=7)
                ), row=2, col=1)
                
            if col_bio_filt in df_procesado.columns:
                fig_global.add_trace(go.Scatter(
                    x=t, y=df_procesado[col_bio_filt], mode="lines",
                    name="Biomasa (filtrada)", line=dict(color="#d62728", width=2.5)
                ), row=2, col=1)

            fig_global.update_layout(
                height=650,
                template="plotly_white",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.06,
                    xanchor="center",
                    x=0.5
                ),
                margin=dict(t=80, b=50, l=60, r=40)
            )
            fig_global.update_yaxes(title=dict(text="Concentración (g/L)"), row=1, col=1, rangemode="nonnegative")
            fig_global.update_yaxes(title=dict(text="Biomasa (g/L)"), row=2, col=1, rangemode="nonnegative")
            fig_global.update_xaxes(title=dict(text="Tiempo de proceso (h)"), row=2, col=1)

            st.plotly_chart(fig_global, use_container_width=True)

        # ==========================================
        # PESTAÑA 2: VELOCIDADES VOLUMÉTRICAS (r)
        # ==========================================
        with tab_volumetrica:
            fig_vol = go.Figure()

            if "r_S" in df_procesado.columns:
                fig_vol.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_S"],
                    name="-r_S (Consumo de Glucosa)", line=dict(color="#1f77b4", width=2.5)
                ))
            if "r_P" in df_procesado.columns:
                fig_vol.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_P"],
                    name="r_P (Formación de Etanol)", line=dict(color="#2ca02c", width=2.5)
                ))
            if "r_X" in df_procesado.columns:
                fig_vol.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_X"],
                    name="r_X (Crecimiento Celular)", line=dict(color="#d62728", width=2.5, dash="dash")
                ))

            fig_vol.update_layout(
                title=dict(text="Velocidades Volumétricas de Reacción Instantáneas r_i (g/(L·h))"),
                xaxis=dict(title=dict(text="Tiempo de proceso (h)")),
                yaxis=dict(title=dict(text="Velocidad volumétrica (g/(L·h))"), rangemode="nonnegative"),
                template="plotly_white",
                hovermode="x unified",
                height=500
            )
            st.plotly_chart(fig_vol, use_container_width=True)

        # ==========================================
        # PESTAÑA 3: VELOCIDADES ESPECÍFICAS (q, μ)
        # ==========================================
        with tab_especifica:
            fig_esp = make_subplots(specs=[[{"secondary_y": True}]])

            # μ en eje primario
            if "mu" in df_procesado.columns:
                fig_esp.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["mu"],
                        name="μ (Vel. específica crecimiento)", line=dict(color="#9467bd", width=3)
                    ), secondary_y=False
                )

            # q_P y q_S en eje secundario
            if "q_P" in df_procesado.columns:
                fig_esp.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["q_P"],
                        name="q_P (Prod. específica Etanol)", line=dict(color="#2ca02c", width=2, dash="dot")
                    ), secondary_y=True
                )
            if "q_S" in df_procesado.columns:
                fig_esp.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["q_S"],
                        name="q_S (Consumo específico Glucosa)", line=dict(color="#1f77b4", width=2, dash="dot")
                    ), secondary_y=True
                )

            fig_esp.update_layout(
                title=dict(text="Velocidades Específicas de Reacción Normalizadas por Biomasa (1/X · dC/dt)"),
                xaxis=dict(title=dict(text="Tiempo de proceso (h)")),
                template="plotly_white",
                hovermode="x unified",
                height=520,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_esp.update_yaxes(
                title=dict(text="μ (h⁻¹)", font=dict(color="#9467bd")), 
                secondary_y=False, rangemode="nonnegative"
            )
            fig_esp.update_yaxes(
                title=dict(text="q_P, q_S (g / (g_biomasa · h))", font=dict(color="#333333")), 
                secondary_y=True, rangemode="nonnegative"
            )

            st.plotly_chart(fig_esp, use_container_width=True)

        # --- TABLA Y DESCARGA ---
        with st.expander("📋 Ver tabla completa con r_i, q_i y concentraciones filtradas"):
            st.dataframe(df_procesado)
            csv = df_procesado.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar datos cinéticos completos (CSV)",
                data=csv,
                file_name="cinetica_procesada.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
