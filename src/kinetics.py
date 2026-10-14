import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import linregress


def calcular_mu_max_semilog(t, biomasa):
    """Calcula mu_max y R² en la fase exponencial lineal sobre ln(X)."""
    ln_x = np.log(np.clip(biomasa, 1e-4, None))
    n = len(t)
    if n < 3:
        return 0.0, 0.0

    mejor_mu = 0.0
    mejor_r2 = 0.0
    ventana_puntos = min(max(3, int(n * 0.35)), n)

    for i in range(n - ventana_puntos + 1):
        t_sub = t[i : i + ventana_puntos]
        ln_x_sub = ln_x[i : i + ventana_puntos]
        reg = linregress(t_sub, ln_x_sub)
        r2 = reg.rvalue**2 if not np.isnan(reg.rvalue) else 0.0
        if reg.slope > mejor_mu and r2 > 0.80:
            mejor_mu = reg.slope
            mejor_r2 = r2

    if mejor_mu == 0.0:
        reg_global = linregress(t, ln_x)
        mejor_mu = max(0.0, reg_global.slope)
        mejor_r2 = max(0.0, reg_global.rvalue**2)

    return mejor_mu, mejor_r2


def _estimar_ventana_optima(n_puntos, orden=2):
    if n_puntos <= 5:
        w = 3
    else:
        w = int(n_puntos * 0.20)
        if w % 2 == 0:
            w += 1
    if w <= orden:
        w = orden + 1 if (orden + 1) % 2 != 0 else orden + 2
    if w >= n_puntos:
        w = n_puntos - 1 if (n_puntos - 1) % 2 != 0 else n_puntos - 2
    return max(3, w)


def calcular_cinetica(df, ventana=5, orden=2, auto_ventana=False):
    df_res = df.copy()
    n_puntos = len(df_res)

    # 1. Ajuste de ventana
    if auto_ventana or ventana is None:
        ventana = _estimar_ventana_optima(n_puntos, orden=orden)
    else:
        if ventana >= n_puntos:
            ventana = n_puntos - 1 if (n_puntos - 1) % 2 != 0 else n_puntos - 2
        if ventana <= orden:
            ventana = orden + 1 if (orden + 1) % 2 != 0 else orden + 2
        if ventana % 2 == 0:
            ventana += 1

    ventana = max(3, ventana)
    
    t = df_res["Tiempo proceso (h)"].values
    dt = df_res["Tiempo proceso (h)"].diff().mean()

    # 2. Perfiles suavizados con Savitzky-Golay
    df_res["Glucosa_filtrada"] = savgol_filter(df_res["Glucosa (g/L)"], ventana, orden)
    df_res["Etanol_filtrada"] = savgol_filter(df_res["Etanol (g/L)"], ventana, orden)
    df_res["Biomasa_filtrada"] = savgol_filter(df_res["Biomasa (g/L)"], ventana, orden)

    # =========================================================================
    # >>> AQUÍ VAN LAS RESTRICCIONES BIOLÓGICAS (EVITA NEGATIVOS) <<<
    # =========================================================================
    # Concentraciones: ninguna puede ser menor a cero
    df_res["Glucosa_filtrada"] = np.clip(df_res["Glucosa_filtrada"], a_min=0.0, a_max=None)
    df_res["Etanol_filtrada"] = np.clip(df_res["Etanol_filtrada"], a_min=0.0, a_max=None)
    df_res["Biomasa_filtrada"] = np.clip(df_res["Biomasa_filtrada"], a_min=1e-4, a_max=None)

    # 3. Velocidades volumétricas analíticas (deriv=1)
    df_res["r_S"] = -savgol_filter(df_res["Glucosa (g/L)"], ventana, orden, deriv=1, delta=dt)
    df_res["r_P"] = savgol_filter(df_res["Etanol (g/L)"], ventana, orden, deriv=1, delta=dt)
    df_res["r_X"] = savgol_filter(df_res["Biomasa (g/L)"], ventana, orden, deriv=1, delta=dt)

    # Rectificación: si la glucosa se agotó (<= 0.05 g/L), el consumo y producción cesan
    agotado = df_res["Glucosa_filtrada"] <= 0.05
    df_res["r_S"] = np.clip(df_res["r_S"], a_min=0.0, a_max=None)
    df_res.loc[agotado, "r_S"] = 0.0

    df_res["r_P"] = np.clip(df_res["r_P"], a_min=0.0, a_max=None)
    df_res.loc[agotado, "r_P"] = 0.0

    # 4. Velocidades específicas rectificadas
    df_res["mu"] = np.clip(df_res["r_X"] / df_res["Biomasa_filtrada"], a_min=0.0, a_max=None)
    df_res["q_S"] = df_res["r_S"] / df_res["Biomasa_filtrada"]
    df_res["q_P"] = df_res["r_P"] / df_res["Biomasa_filtrada"]
    # =========================================================================

    # 5. Balances globales y rendimientos
    s0 = df_res["Glucosa (g/L)"].iloc[0]
    sf = df_res["Glucosa (g/L)"].iloc[-1]
    p0 = df_res["Etanol (g/L)"].iloc[0]
    p_max = df_res["Etanol (g/L)"].max()
    x0 = df_res["Biomasa (g/L)"].iloc[0]
    xf = df_res["Biomasa (g/L)"].iloc[-1]

    delta_s = max(s0 - sf, 1e-6)
    delta_p = max(p_max - p0, 0.0)
    delta_x = max(xf - x0, 0.0)
    delta_t = max(t[-1] - t[0], 1e-6)

    mu_max_robusto, r2_mu = calcular_mu_max_semilog(
        t,
        df_res["Biomasa_filtrada"].values
    )

    metricas = {
        "Y_ps": round(float(delta_p / delta_s), 4),
        "Y_xs": round(float(delta_x / delta_s), 4),
        "mu_max": round(float(mu_max_robusto), 4),
        "mu_r2": round(float(r2_mu), 4),
        "max_r_P": round(float(df_res["r_P"].max()), 4) if "r_P" in df_res.columns else 0.0,
        "max_q_P": round(float(df_res["q_P"].max()), 4) if "q_P" in df_res.columns else 0.0,
        "Q_X_global": round(float((xf - x0) / delta_t), 4),
        "ventana_usada": int(ventana)
    }

    return df_res, metricas
