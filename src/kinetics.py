import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

def calcular_cinetica(df, ventana=5, orden=2):
    df_res = df.copy()
    
    # Ordenar cronológicamente
    df_res = df_res.sort_values(by="Tiempo proceso (h)").reset_index(drop=True)
    t = df_res["Tiempo proceso (h)"].values
    
    # Validar tamaño de ventana
    if ventana >= len(df_res):
        ventana = len(df_res) - 1 if len(df_res) % 2 == 0 else len(df_res)
    if ventana < 3:
        ventana = 3

    # --- 1. FILTRADO CON SAVITZKY-GOLAY (np.clip evita valores < 0) ---
    if "Glucosa (g/L)" in df_res.columns:
        s_filt = savgol_filter(df_res["Glucosa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Glucosa_filtrada"] = np.clip(s_filt, 0, None)
        # Velocidad volumétrica de consumo: -r_S = -dS/dt
        ds_dt = np.gradient(df_res["Glucosa_filtrada"], t)
        df_res["r_S"] = np.clip(-ds_dt, 0, None)

    if "Etanol (g/L)" in df_res.columns:
        p_filt = savgol_filter(df_res["Etanol (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Etanol_filtrada"] = np.clip(p_filt, 0, None)
        # Velocidad volumétrica de producción: r_P = dP/dt
        dp_dt = np.gradient(df_res["Etanol_filtrada"], t)
        df_res["r_P"] = np.clip(dp_dt, 0, None)

    if "Biomasa (g/L)" in df_res.columns:
        x_filt = savgol_filter(df_res["Biomasa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Biomasa_filtrada"] = np.clip(x_filt, 0, None)
        # Velocidad volumétrica de crecimiento: r_X = dX/dt
        dx_dt = np.gradient(df_res["Biomasa_filtrada"], t)
        df_res["r_X"] = np.clip(dx_dt, 0, None)

    # --- 2. VELOCIDADES ESPECÍFICAS DE REACCIÓN (q y μ) ---
    # Se normalizan respecto a la biomasa filtrada X
    if "Biomasa_filtrada" in df_res.columns:
        X = df_res["Biomasa_filtrada"].values
        umbral_x = 1e-4  # Evitar división por cero o ruido en X cercana a 0
        
        # μ = r_X / X  [h^-1]
        if "r_X" in df_res.columns:
            df_res["mu"] = np.where(X > umbral_x, df_res["r_X"] / X, 0.0)
            
        # q_P = r_P / X  [g Etanol / (g Biomasa * h)]
        if "r_P" in df_res.columns:
            df_res["q_P"] = np.where(X > umbral_x, df_res["r_P"] / X, 0.0)
            
        # q_S = -r_S / X  [g Glucosa / (g Biomasa * h)]
        if "r_S" in df_res.columns:
            df_res["q_S"] = np.where(X > umbral_x, df_res["r_S"] / X, 0.0)

    # --- 3. RENDIMIENTOS Y PARÁMETROS GLOBALES ---
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
        "max_r_P": round(float(df_res["r_P"].max()), 4) if "r_P" in df_res.columns else 0.0,
        "max_q_P": round(float(df_res["q_P"].max()), 4) if "q_P" in df_res.columns else 0.0
    }

    return df_res, metricas
