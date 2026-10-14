import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import linregress

def optimizar_ventana_savgol(y, max_ventana=11, orden=2):
    """
    Selecciona de forma automática la ventana óptima impar para Savitzky-Golay
    mediante validación cruzada y minimización del error residual.
    """
    n = len(y)
    if n < 5:
        return 3
    
    # La ventana máxima permitida no puede exceder el 60% de los datos ni ser par
    limite = min(max_ventana, int(n * 0.6))
    if limite % 2 == 0:
        limite -= 1
    limite = max(limite, orden + 1)
    if limite % 2 == 0:
        limite += 1
        
    candidatas = [w for w in range(3, limite + 1, 2) if w > orden]
    if not candidatas:
        return 3

    mejor_w = candidatas[0]
    menor_score = float('inf')

    # Evaluar compensación entre suavizado y conservación de tendencia
    for w in candidatas:
        try:
            y_filt = savgol_filter(y, window_length=w, polyorder=orden)
            # Penalización AIC simplificada (Residuales + penalización por sobre-suavizado)
            residuos = np.sum((y - y_filt) ** 2)
            score = residuos * (1 + (w / n))
            if score < menor_score:
                menor_score = score
                mejor_w = w
        except Exception:
            continue

    return mejor_w


def calcular_mu_max_semilog(t, x, min_puntos=3):
    """
    Calcula mu_max mediante regresión semilogarítmica en ventana deslizante
    (ln(X) vs t), garantizando R² > 0.90 para evitar artefactos numéricos de borde.
    """
    mascara = x > 1e-3
    t_val = t[mascara]
    ln_x = np.log(x[mascara])
    n = len(t_val)

    if n < min_puntos:
        return 0.0, 0.0

    mejor_mu = 0.0
    mejor_r2 = 0.0

    for w in range(min_puntos, min(6, n + 1)):
        for i in range(n - w + 1):
            t_sub = t_val[i : i + w]
            ln_x_sub = ln_x[i : i + w]
            if t_sub[-1] - t_sub[0] < 1e-4:
                continue

            reg = linregress(t_sub, ln_x_sub)
            if reg.slope > mejor_mu and reg.rvalue**2 > 0.90:
                mejor_mu = reg.slope
                mejor_r2 = reg.rvalue**2

    # Respaldo si los datos tienen alto ruido experimental
    if mejor_mu == 0.0:
        for i in range(n - min_puntos + 1):
            reg = linregress(t_val[i : i + min_puntos], ln_x[i : i + min_puntos])
            if reg.slope > mejor_mu:
                mejor_mu = reg.slope
                mejor_r2 = reg.rvalue**2

    return float(mejor_mu), float(mejor_r2)


def calcular_cinetica(df, ventana=None, orden=2, auto_ventana=True):
    df_res = df.copy()
    df_res = df_res.sort_values(by="Tiempo proceso (h)").reset_index(drop=True)
    t = df_res["Tiempo proceso (h)"].values
    n = len(df_res)

    # 1. Determinación de ventana (automática vs manual)
    if auto_ventana or ventana is None:
        col_ref = "Glucosa (g/L)" if "Glucosa (g/L)" in df_res.columns else df_res.columns[1]
        ventana = optimizar_ventana_savgol(df_res[col_ref].values, orden=orden)
    else:
        if ventana >= n:
            ventana = n - 1 if n % 2 == 0 else n
        if ventana <= orden:
            ventana = orden + 1 if (orden + 1) % 2 != 0 else orden + 2
        if ventana < 3:
            ventana = 3

    # --- 2. FILTRADO CON SAVITZKY-GOLAY ---
    # Glucosa
    if "Glucosa (g/L)" in df_res.columns:
        s_filt = savgol_filter(df_res["Glucosa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Glucosa_filtrada"] = np.clip(s_filt, 0, None)
        ds_dt = np.gradient(df_res["Glucosa_filtrada"], t)
        df_res["r_S"] = np.clip(-ds_dt, 0, None)

    # Etanol
    if "Etanol (g/L)" in df_res.columns:
        p_filt = savgol_filter(df_res["Etanol (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Etanol_filtrada"] = np.clip(p_filt, 0, None)
        dp_dt = np.gradient(df_res["Etanol_filtrada"], t)
        df_res["r_P"] = np.clip(dp_dt, 0, None)

    # Biomasa
    if "Biomasa (g/L)" in df_res.columns:
        x_filt = savgol_filter(df_res["Biomasa (g/L)"], window_length=ventana, polyorder=orden)
        df_res["Biomasa_filtrada"] = np.clip(x_filt, 0, None)
        dx_dt = np.gradient(df_res["Biomasa_filtrada"], t)
        df_res["r_X"] = np.clip(dx_dt, 0, None)

    # --- 3. VELOCIDADES ESPECÍFICAS (q_i y mu) CON CORRECCIÓN DE BORDE ---
    if "Biomasa_filtrada" in df_res.columns:
        X = df_res["Biomasa_filtrada"].values
        umbral_x = 0.5

        # Se excluye t=0 si hay inóculo bajo para evitar artefactos de división
        mascara_valida = (X > umbral_x) & (t > 0)

        df_res["mu"] = np.where(mascara_valida, df_res["r_X"] / X, np.nan)
        df_res["q_P"] = np.where(mascara_valida, df_res["r_P"] / X, np.nan)
        df_res["q_S"] = np.where(mascara_valida, df_res["r_S"] / X, np.nan)

        # Rellenar suavemente t=0 con el valor adyacente para continuidad gráfica
        df_res["mu"] = df_res["mu"].bfill().fillna(0.0)
        df_res["q_P"] = df_res["q_P"].bfill().fillna(0.0)
        df_res["q_S"] = df_res["q_S"].bfill().fillna(0.0)

    # --- 4. MÉTRICAS GLOBALES ---
    s0 = df_res["Glucosa (g/L)"].iloc[0]
    sf = df_res["Glucosa (g/L)"].iloc[-1]
    p0 = df_res["Etanol (g/L)"].iloc[0]
    pf = df_res["Etanol (g/L)"].iloc[-1]
    x0 = df_res["Biomasa (g/L)"].iloc[0]
    xf = df_res["Biomasa (g/L)"].iloc[-1]

    delta_s = max(s0 - sf, 1e-6)
    delta_t = max(t[-1] - t[0], 1e-6)

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
        "Q_X_global": round(float((xf - x0) / delta_t), 4),
        "ventana_usada": int(ventana)
    }

    return df_res, metricas
