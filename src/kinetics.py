import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

def calcular_cinetica(df, ventana=5, orden=2):
    df_res = df.copy()
    
    # 1. Asegurar orden cronológico
    df_res = df_res.sort_values(by="Tiempo proceso (h)").reset_index(drop=True)
    t = df_res["Tiempo proceso (h)"].values
    
    # Asegurar ventana válida (debe ser impar y menor al tamaño de datos)
    if ventana >= len(df_res):
        ventana = len(df_res) - 1 if len(df_res) % 2 == 0 else len(df_res)
    if ventana < 3:
        ventana = 3

    # Paso de tiempo aproximado (o uniforme)
    dt = np.gradient(t)

    # 2. Filtrado y corrección de valores no físicos (< 0)
    # Glucosa
    if "Glucosa (g/L)" in df_res.columns:
        s_filt = savgol_filter(df_res["Glucosa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Glucosa_filtrada"] = np.clip(s_filt, 0, None)  # No permitir concentraciones < 0
        # Tasa de consumo: -dS/dt (positiva)
        ds_dt = np.gradient(df_res["Glucosa_filtrada"], t)
        df_res["r_glucosa"] = np.clip(-ds_dt, 0, None)

    # Etanol
    if "Etanol (g/L)" in df_res.columns:
        p_filt = savgol_filter(df_res["Etanol (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Etanol_filtrada"] = np.clip(p_filt, 0, None)
        # Tasa de producción: dP/dt
        dp_dt = np.gradient(df_res["Etanol_filtrada"], t)
        df_res["r_etanol"] = np.clip(dp_dt, 0, None)

    # Biomasa
    if "Biomasa (g/L)" in df_res.columns:
        x_filt = savgol_filter(df_res["Biomasa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Biomasa_filtrada"] = np.clip(x_filt, 0, None)
        # Tasa de crecimiento dx/dt y velocidad específica mu = (1/X)*(dX/dt)
        dx_dt = np.gradient(df_res["Biomasa_filtrada"], t)
        df_res["r_biomasa"] = np.clip(dx_dt, 0, None)
        # Evitar división por cero
        df_res["mu"] = np.where(df_res["Biomasa_filtrada"] > 0, df_res["r_biomasa"] / df_res["Biomasa_filtrada"], 0)

    # 3. Métricas globales
    s0 = df_res["Glucosa (g/L)"].iloc[0]
    sf = df_res["Glucosa (g/L)"].iloc[-1]
    p0 = df_res["Etanol (g/L)"].iloc[0]
    pf = df_res["Etanol (g/L)"].iloc[-1]
    x0 = df_res["Biomasa (g/L)"].iloc[0]
    xf = df_res["Biomasa (g/L)"].iloc[-1]
    
    delta_s = max(s0 - sf, 1e-6)
    y_ps = (pf - p0) / delta_s
    y_xs = (xf - x0) / delta_s

    metricas = {
        "Y_ps": round(float(y_ps), 4),
        "Y_xs": round(float(y_xs), 4),
        "mu_max": round(float(df_res["mu"].max()), 4) if "mu" in df_res.columns else 0.0,
        "max_r_etanol": round(float(df_res["r_etanol"].max()), 4) if "r_etanol" in df_res.columns else 0.0
    }

    return df_res, metricas
