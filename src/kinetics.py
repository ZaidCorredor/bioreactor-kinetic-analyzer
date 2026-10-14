import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import linregress

def calcular_mu_max_semilog(t, x, min_puntos=3):
    """
    Calcula mu_max buscando la pendiente máxima de ln(X) vs t 
    en una ventana deslizante donde el ajuste lineal tenga buen R^2.
    """
    # Filtrar valores válidos de biomasa (> 0)
    mascara = x > 1e-3
    t_val = t[mascara]
    ln_x = np.log(x[mascara])
    
    n = len(t_val)
    if n < min_puntos:
        return 0.0, 0.0

    mejor_mu = 0.0
    mejor_r2 = 0.0

    # Ventana deslizante para detectar la verdadera fase exponencial
    for w in range(min_puntos, min(6, n + 1)):
        for i in range(n - w + 1):
            t_sub = t_val[i : i + w]
            ln_x_sub = ln_x[i : i + w]
            
            # Solo evaluar si hay avance en el tiempo
            if t_sub[-1] - t_sub[0] < 1e-4:
                continue

            reg = linregress(t_sub, ln_x_sub)
            # Priorizar pendientes positivas con alta correlación lineal
            if reg.slope > mejor_mu and reg.rvalue**2 > 0.90:
                mejor_mu = reg.slope
                mejor_r2 = reg.rvalue**2

    # Si los datos son muy ruidosos para R2 > 0.90, tomar la mejor pendiente positiva
    if mejor_mu == 0.0:
        for i in range(n - min_puntos + 1):
            reg = linregress(t_val[i : i + min_puntos], ln_x[i : i + min_puntos])
            if reg.slope > mejor_mu:
                mejor_mu = reg.slope
                mejor_r2 = reg.rvalue**2

    return float(mejor_mu), float(mejor_r2)


def calcular_cinetica(df, ventana=5, orden=2):
    df_res = df.copy()
    
    # 1. Asegurar orden cronológico estricto
    df_res = df_res.sort_values(by="Tiempo proceso (h)").reset_index(drop=True)
    t = df_res["Tiempo proceso (h)"].values
    
    # Ajustar ventana para que sea impar y no exceda el número de puntos
    n_puntos = len(df_res)
    if ventana >= n_puntos:
        ventana = n_puntos - 1 if n_puntos % 2 == 0 else n_puntos
    if ventana < 3:
        ventana = 3

    # --- 2. FILTRADO CON SAVITZKY-GOLAY ---
    # Glucosa
    if "Glucosa (g/L)" in df_res.columns:
        s_filt = savgol_filter(df_res["Glucosa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Glucosa_filtrada"] = np.clip(s_filt, 0, None)
        # Velocidad volumétrica de consumo: -r_S = -dS/dt
        ds_dt = np.gradient(df_res["Glucosa_filtrada"], t)
        df_res["r_S"] = np.clip(-ds_dt, 0, None)

    # Etanol
    if "Etanol (g/L)" in df_res.columns:
        p_filt = savgol_filter(df_res["Etanol (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Etanol_filtrada"] = np.clip(p_filt, 0, None)
        # Velocidad volumétrica de producción: r_P = dP/dt
        dp_dt = np.gradient(df_res["Etanol_filtrada"], t)
        df_res["r_P"] = np.clip(dp_dt, 0, None)

    # Biomasa
    if "Biomasa (g/L)" in df_res.columns:
        x_filt = savgol_filter(df_res["Biomasa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Biomasa_filtrada"] = np.clip(x_filt, 0, None)
        # Velocidad volumétrica de crecimiento: r_X = dX/dt
        dx_dt = np.gradient(df_res["Biomasa_filtrada"], t)
        df_res["r_X"] = np.clip(dx_dt, 0, None)

    # --- 3. VELOCIDADES ESPECÍFICAS (q_i y μ instantáneo acotado) ---
    if "Biomasa_filtrada" in df_res.columns:
        X = df_res["Biomasa_filtrada"].values
        umbral_x = 0.5  # Si la biomasa es menor a 0.5 g/L, evitamos divisiones con artefactos
        
        # μ instantáneo por diferenciación puntual
        if "r_X" in df_res.columns:
            df_res["mu"] = np.where(X > umbral_x, df_res["r_X"] / X, 0.0)
            
        # q_P (g Etanol / (g Biomasa * h))
        if "r_P" in df_res.columns:
            df_res["q_P"] = np.where(X > umbral_x, df_res["r_P"] / X, 0.0)
            
        # q_S (g Glucosa / (g Biomasa * h))
        if "r_S" in df_res.columns:
            df_res["q_S"] = np.where(X > umbral_x, df_res["r_S"] / X, 0.0)

    # --- 4. CÁLCULO DE PARÁMETROS GLOBALES Y ROBUSTOS ---
    s0 = df_res["Glucosa (g/L)"].iloc[0]
    sf = df_res["Glucosa (g/L)"].iloc[-1]
    p0 = df_res["Etanol (g/L)"].iloc[0]
    pf = df_res["Etanol (g/L)"].iloc[-1]
    x0 = df_res["Biomasa (g/L)"].iloc[0]
    xf = df_res["Biomasa (g/L)"].iloc[-1]
    
    delta_s = max(s0 - sf, 1e-6)
    delta_t = max(t[-1] - t[0], 1e-6)

    # Cálculo semilogarítmico de mu_max sobre los datos de biomasa
    mu_max_robusto, r2_mu = calcular_mu_max_semilog(
        t, 
        df_res["Biomasa_filtrada"].values if "Biomasa_filtrada" in df_res.columns else df_res["Biomasa (g/L)"].values
    )

    metricas = {
        "Y_ps": round(float((pf - p0) / delta_s), 4),
        "Y_xs": round(float((xf - x0) / delta_s), 4),
        "mu_max": round(float(mu_max_robusto), 4),
        "mu_r2": round(float(r2_mu), 4),
        "max_r_P": round(float(df_res["r_P"].max()), 4) if "r_P" in df_res.columns else 0.0,
        "max_q_P": round(float(df_res["q_P"].max()), 4) if "q_P" in df_res.columns else 0.0,
        "Q_X_global": round(float((xf - x0) / delta_t), 4)
    }

    return df_res, metricas
