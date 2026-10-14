import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.kinetics import calcular_cinetica
from src.visualizer import exportar_figura_publicacion

# Configuración inicial de la página
st.set_page_config(
    page_title="Universal Bioreactor Kinetic Analyzer",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Universal Bioreactor Batch Kinetic Analyzer")
st.markdown("""
Analizador cinético automatizado aplicable a fermentaciones y cultivos con **bacterias, levaduras o células fúngicas**. 
Aplica un **filtro de Savitzky-Golay** con selección inteligente de ventana para mitigar el ruido instrumental y calcula 
rendimientos globales ($Y_{P/S}$, $Y_{X/S}$), **velocidades volumétricas de reacción** ($r_i$) y **velocidades específicas** ($q_i$, $\mu$).
""")

# --- CARGA DE ARCHIVO ---
st.subheader("1. Carga de datos de fermentación")
archivo_subido = st.file_uploader(
    "Carga un archivo Excel (.xlsx) o CSV con tus datos de bioproceso:",
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

# --- BARRA LATERAL (CONFIGURACIÓN DINÁMICA) ---
if df is not None:
    cols = df.columns.tolist()

    st.sidebar.header("🔬 Identidad del Bioproceso")
    microorganismo = st.sidebar.text_input("Microorganismo / Cepa:", value="Saccharomyces cerevisiae")
    sustrato_nombre = st.sidebar.text_input("Nombre Sustrato (S):", value="Glucosa")
    producto_nombre = st.sidebar.text_input("Nombre Producto (P):", value="Etanol")

    st.sidebar.markdown("---")
    st.sidebar.header("📌 Mapeo Dinámico de Columnas")

    # Detección heurística de columnas comunes
    idx_t = next((i for i, c in enumerate(cols) if any(k in c.lower() for k in ["tiempo", "time", "h", "t"])), 0)
    idx_s = next((i for i, c in enumerate(cols) if any(k in c.lower() for k in ["glucosa", "glucose", "sustrato", "sub", "s"])), min(1, len(cols)-1))
    idx_x = next((i for i, c in enumerate(cols) if any(k in c.lower() for k in ["biomasa", "biomass", "od", "x"])), min(2, len(cols)-1))
    idx_p = next((i for i, c in enumerate(cols) if any(k in c.lower() for k in ["etanol", "ethanol", "producto", "product", "p"])), min(3, len(cols)-1))

    col_t = st.sidebar.selectbox("Columna de Tiempo (h):", cols, index=idx_t)
    col_s = st.sidebar.selectbox("Columna de Sustrato [S]:", cols, index=idx_s)
    col_x = st.sidebar.selectbox("Columna de Biomasa [X]:", cols, index=idx_x)
    col_p = st.sidebar.selectbox("Columna de Producto [P]:", cols, index=idx_p)

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Configuración del Filtro")

    modo_auto = st.sidebar.toggle(
        "🎯 Optimización Automática de Ventana", 
        value=True, 
        help="Calcula la ventana ideal minimizando el error residual según el número de datos."
    )

    if modo_auto:
        st.sidebar.info("Modo Automático activo: El algoritmo detecta el tamaño óptimo de ventana.")
        ventana_sel = None
        orden_sel = 2
    else:
        ventana_sel = st.sidebar.slider(
            "Tamaño de ventana (puntos, impar):", 
            min_value=3, max_value=15, value=5, step=2
        )
        orden_sel = st.sidebar.slider(
            "Orden del polinomio:", 
            min_value=1, max_value=4, value=2, step=1
        )

    # --- PROCESAMIENTO Y VISUALIZACIÓN ---
    try:
        # Ejecución del cálculo cinético con columnas dinámicas
        df_procesado, metricas = calcular_cinetica(
            df, 
            col_tiempo=col_t,
            col_sustrato=col_s,
            col_biomasa=col_x,
            col_producto=col_p,
            ventana=ventana_sel, 
            orden=orden_sel, 
            auto_ventana=modo_auto
        )

        # Mapeo de compatibilidad canónica para exportar_figura_publicacion en visualizer.py
        df_procesado["Tiempo proceso (h)"] = df_procesado[col_t]
        df_procesado["Glucosa (g/L)"] = df_procesado[col_s]
        df_procesado["Glucosa_filtrada"] = df_procesado["S_filtrada"]
        df_procesado["Etanol (g/L)"] = df_procesado[col_p]
        df_procesado["Etanol_filtrada"] = df_procesado["P_filtrada"]
        df_procesado["Biomasa (g/L)"] = df_procesado[col_x]

        st.subheader(f"2. Parámetros Cinéticos Globales ({microorganismo})")
                
        # Fila 1: Rendimientos y Crecimiento
        f1_col1, f1_col2, f1_col3 = st.columns(3)
        f1_col1.metric(f"Rendimiento $Y_{{P/S}}$", f"{metricas['Y_ps']} g/g", help=f"g de {producto_nombre} / g de {sustrato_nombre}")
        f1_col2.metric(f"Rendimiento $Y_{{X/S}}$", f"{metricas['Y_xs']} g/g", help=f"g de Biomasa / g de {sustrato_nombre}")
        
        ajuste_r2 = f"Ajuste R² = {metricas.get('mu_r2', 'N/A')}" if 'mu_r2' in metricas else None
        f1_col3.metric("Vel. máx. $\mu_{\max}$", f"{metricas['mu_max']} h⁻¹", ajuste_r2)

        # Fila 2: Productividades y Tasas volumétricas
        f2_col1, f2_col2 = st.columns(2)
        f2_col1.metric(f"Vel. máx. prod. ($r_{{P,\max}}$)", f"{metricas.get('max_r_P', 'N/A')} g/(L·h)")
        
        q_x_val = metricas.get('Q_X_global', 'N/A')
        f2_col2.metric("Productividad Biomasa ($Q_X$)", f"{q_x_val} g/(L·h)" if q_x_val != 'N/A' else "N/A")

        if modo_auto and "ventana_usada" in metricas:
            st.caption(f"ℹ️ *Ventana óptima aplicada automáticamente: **{metricas['ventana_usada']} puntos**.*")

        # --- 3. VISUALIZACIÓN MULTIPANEL ---
        st.subheader("3. Perfiles Cinéticos y Análisis de Velocidades")

        tab_global, tab_volumetrica, tab_especifica = st.tabs([
            f"📊 Concentraciones ({sustrato_nombre}, {producto_nombre}, X)", 
            "⚡ Velocidades Volumétricas (r)", 
            "🔬 Velocidades Específicas (q, μ)"
        ])

        t = df_procesado[col_t]
        col_bio_filt = "Biomasa_filtrada" if "Biomasa_filtrada" in df_procesado.columns else col_x

        # ==========================================
        # PESTAÑA 1: PERFIL DE CONCENTRACIONES (S, P, X)
        # ==========================================
        with tab_global:
            fig_global = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.15,
                subplot_titles=(f"Sustrato ({sustrato_nombre}) y Producto ({producto_nombre})", "Crecimiento de Biomasa Celular (X)")
            )

            # Panel 1: Sustrato y Producto
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado[col_s], mode="markers",
                name=f"{sustrato_nombre} (exp)", marker=dict(color="#1f77b4", opacity=0.45, size=7)
            ), row=1, col=1)
            
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["S_filtrada"], mode="lines",
                name=f"{sustrato_nombre} (filtrada)", line=dict(color="#1f77b4", width=2.5)
            ), row=1, col=1)

            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado[col_p], mode="markers",
                name=f"{producto_nombre} (exp)", marker=dict(color="#2ca02c", opacity=0.45, size=7)
            ), row=1, col=1)
            
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["P_filtrada"], mode="lines",
                name=f"{producto_nombre} (filtrado)", line=dict(color="#2ca02c", width=2.5)
            ), row=1, col=1)

            # Panel 2: Biomasa
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado[col_x], mode="markers",
                name="Biomasa (exp)", marker=dict(color="#d62728", opacity=0.45, size=7)
            ), row=2, col=1)
            
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado[col_bio_filt], mode="lines",
                name="Biomasa (filtrada)", line=dict(color="#d62728", width=2.5)
            ), row=2, col=1)

            fig_global.update_layout(
                height=650,
                template="plotly_white",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="center", x=0.5),
                margin=dict(t=80, b=50, l=60, r=40)
            )
            fig_global.update_yaxes(title=dict(text="Concentración (g/L)"), row=1, col=1, rangemode="nonnegative")
            fig_global.update_yaxes(title=dict(text="Biomasa (g/L)"), row=2, col=1, rangemode="nonnegative")
            fig_global.update_xaxes(title=dict(text=f"Tiempo ({col_t})"), row=2, col=1)

            st.plotly_chart(fig_global, use_container_width=True)

        # ==========================================
        # PESTAÑA 2: VELOCIDADES VOLUMÉTRICAS (r)
        # ==========================================
        with tab_volumetrica:
            fig_vol = go.Figure()

            if "r_S" in df_procesado.columns:
                fig_vol.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_S"],
                    name=f"-r_S (Consumo de {sustrato_nombre})", line=dict(color="#1f77b4", width=2.5)
                ))
            if "r_P" in df_procesado.columns:
                fig_vol.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_P"],
                    name=f"r_P (Formación de {producto_nombre})", line=dict(color="#2ca02c", width=2.5)
                ))
            if "r_X" in df_procesado.columns:
                fig_vol.add_trace(go.Scatter(
                    x=t, y=df_procesado["r_X"],
                    name="r_X (Crecimiento Celular)", line=dict(color="#d62728", width=2.5, dash="dash")
                ))

            fig_vol.update_layout(
                title=dict(text="Velocidades Volumétricas de Reacción Instantáneas r_i (g/(L·h))"),
                xaxis=dict(title=dict(text=f"Tiempo ({col_t})")),
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

            if "mu" in df_procesado.columns:
                fig_esp.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["mu"],
                        name="μ (Vel. específica crecimiento)", line=dict(color="#9467bd", width=3)
                    ), secondary_y=False
                )

            if "q_P" in df_procesado.columns:
                fig_esp.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["q_P"],
                        name=f"q_P (Prod. específica {producto_nombre})", line=dict(color="#2ca02c", width=2, dash="dot")
                    ), secondary_y=True
                )
            if "q_S" in df_procesado.columns:
                fig_esp.add_trace(
                    go.Scatter(
                        x=t, y=df_procesado["q_S"],
                        name=f"q_S (Consumo específico {sustrato_nombre})", line=dict(color="#1f77b4", width=2, dash="dot")
                    ), secondary_y=True
                )

            fig_esp.update_layout(
                title=dict(text="Velocidades Específicas de Reacción Normalizadas por Biomasa (1/X · dC/dt)"),
                xaxis=dict(title=dict(text=f"Tiempo ({col_t})")),
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

        # --- 4. EXPORTACIÓN PARA PUBLICACIÓN EDITORIAL ---
        st.subheader("4. Exportación para Publicación Científica (Q1)")
        
        if st.button("🖼️ Generar figura para publicación (PDF / PNG 300 DPI)"):
            with st.spinner("Generando panel multipanel de alta resolución..."):
                archivos_generados = exportar_figura_publicacion(
                    df_procesado, 
                    output_path="figura_cinetica_q1", 
                    formatos=("png", "pdf"), 
                    dpi=300
                )
            
            st.success("¡Figura vectorial y PNG generadas con éxito a 300 DPI!")
            
            # Previsualización del PNG generado directamente en la app
            st.image("figura_cinetica_q1.png", caption=f"Panel editorial 2x2 para {microorganismo}", use_container_width=True)
            
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                with open("figura_cinetica_q1.pdf", "rb") as f_pdf:
                    st.download_button(
                        label="📥 Descargar Vectorial (PDF)",
                        data=f_pdf,
                        file_name=f"cinetica_{sustrato_nombre}_{producto_nombre}_Q1.pdf",
                        mime="application/pdf"
                    )
            
            with col_d2:
                with open("figura_cinetica_q1.png", "rb") as f_png:
                    st.download_button(
                        label="📥 Descargar Imagen (PNG 300 DPI)",
                        data=f_png,
                        file_name=f"cinetica_{sustrato_nombre}_{producto_nombre}_300dpi.png",
                        mime="image/png"
                    )

        # --- TABLA Y DESCARGA ---
        with st.expander("📋 Ver tabla completa con r_i, q_i y concentraciones filtradas"):
            st.dataframe(df_procesado)
            csv = df_procesado.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar datos cinéticos completos (CSV)",
                data=csv,
                file_name=f"cinetica_{microorganismo.replace(' ', '_')}.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
