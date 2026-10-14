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


def calcular_cinetica(
    df, 
    col_tiempo=None, 
    col_sustrato=None, 
    col_producto=None, 
    col_biomasa=None, 
    ventana=5, 
    orden=2, 
    auto_ventana=False
):
    """
    Calcula cinéticas de fermentación.
    Los 4 argumentos de columnas son completamente opcionales (=None).
    Si no se pasan, toma las columnas en el orden natural del Excel:
    Columna 0 = Tiempo
    Columna 1 = Sustrato
    Columna 2 = Producto
    Columna 3 = Biomasa
    """
    df_res = df.copy()
    cols = df_res.columns.tolist()

    # Si no se definieron o no existen en el archivo, se asignan por posición estricta
    c_t = col_tiempo if (col_tiempo in cols) else cols[0]
    c_s = col_sustrato if (col_sustrato in cols) else cols[min(1, len(cols) - 1)]
    c_p = col_producto if (col_producto in cols) else cols[min(2, len(cols) - 1)]
    c_x = col_biomasa if (col_biomasa in cols) else cols[min(3, len(cols) - 1)]

    # Asignación numérica directa (S = Sustrato real, P = Producto real)
    df_res["t"] = pd.to_numeric(df_res[c_t], errors="coerce")
    df_res["S"] = pd.to_numeric(df_res[c_s], errors="coerce")
    df_res["P"] = pd.to_numeric(df_res[c_p], errors="coerce")
    df_res["X"] = pd.to_numeric(df_res[c_x], errors="coerce")

    # Limpiar filas nulas y ordenar cronológicamente
    df_res = df_res.dropna(subset=["t", "S", "P", "X"]).sort_values("t").reset_index(drop=True)
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

    t_vals = df_res["t"].values
    dt = np.diff(t_vals)
    dt_medio = np.mean(dt) if len(dt) > 0 else 1.0

    # 2. Filtrado Savitzky-Golay
    df_res["S_filtrada"] = savgol_filter(df_res["S"], ventana, orden)
    df_res["P_filtrada"] = savgol_filter(df_res["P"], ventana, orden)
    df_res["X_filtrada"] = savgol_filter(df_res["X"], ventana, orden)

    # Restricciones físicas (no valores negativos)
    df_res["S_filtrada"] = np.clip(df_res["S_filtrada"], a_min=0.0, a_max=None)
    df_res["P_filtrada"] = np.clip(df_res["P_filtrada"], a_min=0.0, a_max=None)
    df_res["X_filtrada"] = np.clip(df_res["X_filtrada"], a_min=1e-4, a_max=None)

    # 3. Velocidades volumétricas analíticas
    df_res["r_S"] = -savgol_filter(df_res["S"], ventana, orden, deriv=1, delta=dt_medio)
    df_res["r_P"] = savgol_filter(df_res["P"], ventana, orden, deriv=1, delta=dt_medio)
    df_res["r_X"] = savgol_filter(df_res["X"], ventana, orden, deriv=1, delta=dt_medio)

    # Rectificación biológica por agotamiento de sustrato
    agotado = df_res["S_filtrada"] <= 0.05
    df_res["r_S"] = np.clip(df_res["r_S"], a_min=0.0, a_max=None)
    df_res.loc[agotado, "r_S"] = 0.0

    df_res["r_P"] = np.clip(df_res["r_P"], a_min=0.0, a_max=None)
    df_res.loc[agotado, "r_P"] = 0.0

    # 4. Velocidades específicas
    df_res["mu"] = np.clip(df_res["r_X"] / df_res["X_filtrada"], a_min=0.0, a_max=None)
    df_res["q_S"] = df_res["r_S"] / df_res["X_filtrada"]
    df_res["q_P"] = df_res["r_P"] / df_res["X_filtrada"]

    # 5. Balances globales
    s0 = df_res["S"].iloc[0]
    sf = df_res["S"].iloc[-1]
    p0 = df_res["P"].iloc[0]
    p_max = df_res["P"].max()
    x0 = df_res["X"].iloc[0]
    xf = df_res["X"].iloc[-1]

    delta_s = max(s0 - sf, 1e-6)
    delta_p = max(p_max - p0, 0.0)
    delta_x = max(xf - x0, 0.0)
    delta_t = max(t_vals[-1] - t_vals[0], 1e-6)

    mu_max_robusto, r2_mu = calcular_mu_max_semilog(t_vals, df_res["X_filtrada"].values)

    # Columnas canónicas añadidas para visualizer.py
    df_res["Tiempo proceso (h)"] = df_res["t"]
    df_res["Glucosa (g/L)"] = df_res["S"]
    df_res["Glucosa_filtrada"] = df_res["S_filtrada"]
    df_res["Etanol (g/L)"] = df_res["P"]
    df_res["Etanol_filtrada"] = df_res["P_filtrada"]
    df_res["Biomasa (g/L)"] = df_res["X"]
    df_res["Biomasa_filtrada"] = df_res["X_filtrada"]

    metricas = {
        "Y_ps": round(float(delta_p / delta_s), 4),
        "Y_xs": round(float(delta_x / delta_s), 4),
        "mu_max": round(float(mu_max_robusto), 4),
        "mu_r2": round(float(r2_mu), 4),
        "max_r_P": round(float(df_res["r_P"].max()), 4),
        "max_q_P": round(float(df_res["q_P"].max()), 4),
        "Q_X_global": round(float(delta_x / delta_t), 4),
        "ventana_usada": int(ventana)
    }

    return df_res, metricas
