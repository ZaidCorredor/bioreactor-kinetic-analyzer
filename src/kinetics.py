import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import linregress


def calcular_mu_max_semilog(t, biomasa):
    """
    Calcula mu_max y R² buscando la ventana móvil de fase exponencial
    con mayor pendiente y mejor ajuste lineal sobre ln(X).
    """
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

    # Si no encontró un tramo con R² > 0.8, toma la regresión global
    if mejor_mu == 0.0:
        reg_global = linregress(t, ln_x)
        mejor_mu = max(0.0, reg_global.slope)
        mejor_r2 = max(0.0, reg_global.rvalue**2)

    return mejor_mu, mejor_r2


def _estimar_ventana_optima(n_puntos, orden=2):
    """Calcula ventana impar adecuada para el tamaño muestral (~20% de puntos)."""
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


def calcular_cinetica(
    df, 
    col_tiempo="Tiempo proceso (h)", 
    col_sustrato="Glucosa (g/L)", 
    col_biomasa="Biomasa (g/L)", 
    col_producto="Etanol (g/L)", 
    ventana=5, 
    orden=2, 
    auto_ventana=False
):
    df_res = df.copy()
    n_puntos = len(df_res)

    # 1. Ajuste y validación del tamaño de ventana
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
    
    t = df_res[col_tiempo].values
    dt = df_res[col_tiempo].diff().mean()

    # 2. Filtrado Savitzky-Golay
    df_res["S_filtrada"] = savgol_filter(df_res[col_sustrato], ventana, orden)
    df_res["P_filtrada"] = savgol_filter(df_res[col_producto], ventana, orden)
    df_res["Biomasa_filtrada"] = np.clip(
        savgol_filter(df_res[col_biomasa], ventana, orden), 
        a_min=1e-4, 
        a_max=None
    )

    # 3. Velocidades volumétricas (derivadas analíticas con deriv=1)
    df_res["r_S"] = -savgol_filter(df_res[col_sustrato], ventana, orden, deriv=1, delta=dt)
    df_res["r_P"] = savgol_filter(df_res[col_producto], ventana, orden, deriv=1, delta=dt)
    df_res["r_X"] = savgol_filter(df_res[col_biomasa], ventana, orden, deriv=1, delta=dt)

    # 4. Velocidades específicas
    df_res["mu"] = df_res["r_X"] / df_res["Biomasa_filtrada"]
    df_res["q_S"] = df_res["r_S"] / df_res["Biomasa_filtrada"]
    df_res["q_P"] = df_res["r_P"] / df_res["Biomasa_filtrada"]

    # 5. Balances globales
    s0 = df_res[col_sustrato].iloc[0]
    sf = df_res[col_sustrato].iloc[-1]
    p0 = df_res[col_producto].iloc[0]
    p_max = df_res[col_producto].max()
    x0 = df_res[col_biomasa].iloc[0]
    xf = df_res[col_biomasa].iloc[-1]

    delta_s = max(s0 - sf, 1e-6)
    delta_p = max(p_max - p0, 0.0)
    delta_x = max(xf - x0, 0.0)
    delta_t = max(t[-1] - t[0], 1e-6)

    # Cálculo semilogarítmico de mu_max
    mu_max_robusto, r2_mu = calcular_mu_max_semilog(
        t,
        df_res["Biomasa_filtrada"].values if "Biomasa_filtrada" in df_res.columns else df_res[col_biomasa].values
    )

    # 6. Diccionario de métricas
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
