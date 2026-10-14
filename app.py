import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.kinetics import calcular_cinetica
from src.visualizer import exportar_figura_publicacion

st.set_page_config(
    page_title="Universal Bioreactor Kinetic Analyzer",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Universal Bioreactor Batch Kinetic Analyzer")
st.markdown("""
Analizador cinético automatizado aplicable a fermentaciones y cultivos con **bacterias, levaduras o células fúngicas**. 
Aplica un **filtro de Savitzky-Golay** con selección inteligente de ventana para mitigar el ruido experimental y calcula 
rendimientos globales ($Y_{P/S}$, $Y_{X/S}$), **velocidades volumétricas de reacción** ($r_i$) y **velocidades específicas** ($q_i$, $\mu$).
""")

# --- CARGA DE ARCHIVO ---
st.subheader("1. Carga de datos de fermentación")
archivo_subido = st.file_uploader(
    "Carga un archivo Excel (.xlsx) o CSV con tus datos experimentales:",
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

# --- BARRA LATERAL (CONFIGURACIÓN) ---
if df is not None:
    cols = df.columns.tolist()

    # Función inteligente para preseleccionar columnas por palabras clave completas
    def detectar_indice(palabras_clave, fallback_idx):
        for idx, col_name in enumerate(cols):
            nombre_limpio = col_name.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            # Excluir 'tiempo' si no estamos buscando tiempo
            if "tiempo" not in palabras_clave and any(t in nombre_limpio for t in ["tiempo", "time"]):
                continue
            for palabra in palabras_clave:
                if palabra in nombre_limpio:
                    return idx
        return min(fallback_idx, len(cols) - 1)

    idx_sug_t = detectar_indice(["tiempo", "time", "hora", "hours"], fallback_idx=0)
    idx_sug_s = detectar_indice(["glucosa", "glucose", "sustrato", "substrate", "glicerol", "lactosa", "sacarosa", "xilosa"], fallback_idx=1)
    idx_sug_p = detectar_indice(["etanol", "ethanol", "lactico", "lactato", "lactic", "citrico", "citric", "producto", "product", "acetico"], fallback_idx=2)
    idx_sug_x = detectar_indice(["biomasa", "biomass", "od600", "od", "cel", "levadura", "bacteria"], fallback_idx=3)

    st.sidebar.header("🔬 Identidad del Bioproceso")
    microorganismo = st.sidebar.text_input("Microorganismo / Cepa:", value="Saccharomyces cerevisiae")

    st.sidebar.markdown("---")
    st.sidebar.header("📋 Selección de Columnas")
    st.sidebar.caption("Verifica o ajusta qué columna de tu archivo corresponde a cada variable:")

    col_t_sel = st.sidebar.selectbox("⏱️ Columna de Tiempo (h):", cols, index=idx_sug_t)
    col_s_sel = st.sidebar.selectbox("🍬 Sustrato Limitante [S]:", cols, index=idx_sug_s)
    col_p_sel = st.sidebar.selectbox("🧪 Producto de Interés [P]:", cols, index=idx_sug_p)
    col_x_sel = st.sidebar.selectbox("🌱 Biomasa Celular [X]:", cols, index=idx_sug_x)

    # Validar que no se hayan seleccionado columnas repetidas
    cols_seleccionadas = [col_t_sel, col_s_sel, col_p_sel, col_x_sel]
    if len(set(cols_seleccionadas)) < 4:
        st.sidebar.error("⚠️ Has asignado la misma columna a dos variables diferentes. Por favor revisa los selectores.")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Configuración del Filtro")

    modo_auto = st.sidebar.toggle(
        "🎯 Optimización Automática de Ventana", 
        value=True, 
        help="Calcula matemáticamente la ventana ideal minimizando el error residual."
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

    # Nombres visuales limpios para títulos y leyendas
    sustrato_nombre = col_s_sel.split("(")[0].strip()
    producto_nombre = col_p_sel.split("(")[0].strip()

    # --- PROCESAMIENTO Y VISUALIZACIÓN ---
    try:
        df_procesado, metricas = calcular_cinetica(
            df, 
            col_tiempo=col_t_sel,
            col_sustrato=col_s_sel,
            col_producto=col_p_sel,
            col_biomasa=col_x_sel,
            ventana=ventana_sel, 
            orden=orden_sel, 
            auto_ventana=modo_auto
        )

        st.subheader(f"2. Parámetros Cinéticos Globales ({microorganismo})")
                
        # Fila 1: Rendimientos y Crecimiento
        f1_col1, f1_col2, f1_col3 = st.columns(3)
        f1_col1.metric(f"Rendimiento $Y_{{P/S}}$", f"{metricas['Y_ps']} g/g", help=f"g de {producto_nombre} / g de {sustrato_nombre}")
        f1_col2.metric(f"Rendimiento $Y_{{X/S}}$", f"{metricas['Y_xs']} g/g", help=f"g de Biomasa / g de {sustrato_nombre}")
        f1_col3.metric("Vel. máx. $\mu_{\max}$", f"{metricas['mu_max']} h⁻¹", f"Ajuste R² = {metricas['mu_r2']}")

        # Fila 2: Productividades y Tasas volumétricas
        f2_col1, f2_col2 = st.columns(2)
        f2_col1.metric(f"Vel. máx. producción ($r_{{P,\max}}$)", f"{metricas['max_r_P']} g/(L·h)")
        f2_col2.metric("Productividad de Biomasa ($Q_X$)", f"{metricas['Q_X_global']} g/(L·h)")

        if modo_auto:
            st.caption(f"ℹ️ *Ventana óptima aplicada automáticamente: **{metricas['ventana_usada']} puntos**.*")

        # --- 3. VISUALIZACIÓN MULTIPANEL ---
        st.subheader("3. Perfiles Cinéticos y Análisis de Velocidades")

        tab_global, tab_volumetrica, tab_especifica = st.tabs([
            f"📊 Concentraciones ({sustrato_nombre}, {producto_nombre}, X)", 
            "⚡ Velocidades Volumétricas (r)", 
            "🔬 Velocidades Específicas (q, μ)"
        ])

        t = df_procesado["t"]

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
                x=t, y=df_procesado["S"], mode="markers",
                name=f"{sustrato_nombre} (exp)", marker=dict(color="#1f77b4", opacity=0.45, size=7)
            ), row=1, col=1)
            
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["S_filtrada"], mode="lines",
                name=f"{sustrato_nombre} (filtrada)", line=dict(color="#1f77b4", width=2.5)
            ), row=1, col=1)

            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["P"], mode="markers",
                name=f"{producto_nombre} (exp)", marker=dict(color="#2ca02c", opacity=0.45, size=7)
            ), row=1, col=1)
            
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["P_filtrada"], mode="lines",
                name=f"{producto_nombre} (filtrado)", line=dict(color="#2ca02c", width=2.5)
            ), row=1, col=1)

            # Panel 2: Biomasa
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["X"], mode="markers",
                name="Biomasa (exp)", marker=dict(color="#d62728", opacity=0.45, size=7)
            ), row=2, col=1)
            
            fig_global.add_trace(go.Scatter(
                x=t, y=df_procesado["X_filtrada"], mode="lines",
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
            fig_global.update_xaxes(title=dict(text=f"Tiempo ({col_t_sel})"), row=2, col=1)

            st.plotly_chart(fig_global, use_container_width=True)

        # ==========================================
        # PESTAÑA 2: VELOCIDADES VOLUMÉTRICAS (r)
        # ==========================================
        with tab_volumetrica:
            fig_vol = go.Figure()

            fig_vol.add_trace(go.Scatter(
                x=t, y=df_procesado["r_S"],
                name=f"-r_S (Consumo de {sustrato_nombre})", line=dict(color="#1f77b4", width=2.5)
            ))
            fig_vol.add_trace(go.Scatter(
                x=t, y=df_procesado["r_P"],
                name=f"r_P (Formación de {producto_nombre})", line=dict(color="#2ca02c", width=2.5)
            ))
            fig_vol.add_trace(go.Scatter(
                x=t, y=df_procesado["r_X"],
                name="r_X (Crecimiento Celular)", line=dict(color="#d62728", width=2.5, dash="dash")
            ))

            fig_vol.update_layout(
                title=dict(text="Velocidades Volumétricas de Reacción Instantáneas r_i (g/(L·h))"),
                xaxis=dict(title=dict(text=f"Tiempo ({col_t_sel})")),
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

            fig_esp.add_trace(
                go.Scatter(
                    x=t, y=df_procesado["mu"],
                    name="μ (Vel. específica crecimiento)", line=dict(color="#9467bd", width=3)
                ), secondary_y=False
            )
            fig_esp.add_trace(
                go.Scatter(
                    x=t, y=df_procesado["q_P"],
                    name=f"q_P (Prod. específica {producto_nombre})", line=dict(color="#2ca02c", width=2, dash="dot")
                ), secondary_y=True
            )
            fig_esp.add_trace(
                go.Scatter(
                    x=t, y=df_procesado["q_S"],
                    name=f"q_S (Consumo específico {sustrato_nombre})", line=dict(color="#1f77b4", width=2, dash="dot")
                ), secondary_y=True
            )

            fig_esp.update_layout(
                title=dict(text="Velocidades Específicas de Reacción Normalizadas por Biomasa (1/X · dC/dt)"),
                xaxis=dict(title=dict(text=f"Tiempo ({col_t_sel})")),
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
