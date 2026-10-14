import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


def calcular_cinetica(df, col_tiempo, col_sustrato, col_biomasa, col_producto, ventana=5, orden=2):
    """
    Calcula cinéticas de fermentación agnósticas al bioproceso.
    
    Acepta cualquier nombre de columna para tiempo, sustrato (S), biomasa (X) y producto (P).
    Aplica filtro Savitzky-Golay para suavizado y derivadas analíticas de ruido bajo.
    """
    df = df.copy()

    # Validar que la ventana sea impar y válida para el tamaño de datos
    n_puntos = len(df)
    if ventana >= n_puntos:
        ventana = n_puntos - 1 if (n_puntos - 1) % 2 != 0 else n_puntos - 2
    if ventana <= orden:
        ventana = orden + 2 if (orden + 2) % 2 != 0 else orden + 3

    # Paso de muestreo temporal (delta t)
    dt = df[col_tiempo].diff().mean()

    # 1. Perfiles suavizados con Savitzky-Golay
    df["S_filtrada"] = savgol_filter(df[col_sustrato], ventana, orden)
    df["P_filtrada"] = savgol_filter(df[col_producto], ventana, orden)
    df["Biomasa_filtrada"] = np.clip(
        savgol_filter(df[col_biomasa], ventana, orden),
        a_min=1e-3, a_max=None
    )

    # 2. Velocidades volumétricas (derivadas analíticas con deriv=1)
    # r_S: velocidad volumétrica de consumo de sustrato (-dS/dt, en positivo)
    df["r_S"] = -savgol_filter(df[col_sustrato], ventana, orden, deriv=1, delta=dt)
    
    # r_P: velocidad volumétrica de formación de producto (dP/dt)
    df["r_P"] = savgol_filter(df[col_producto], ventana, orden, deriv=1, delta=dt)
    
    # r_X: velocidad volumétrica de crecimiento de biomasa (dX/dt)
    df["r_X"] = savgol_filter(df[col_biomasa], ventana, orden, deriv=1, delta=dt)

    # 3. Velocidades específicas de reacción
    # mu = (1/X) * (dX/dt)
    df["mu"] = df["r_X"] / df["Biomasa_filtrada"]
    
    # q_S = (1/X) * (-dS/dt)
    df["q_S"] = df["r_S"] / df["Biomasa_filtrada"]
    
    # q_P = (1/X) * (dP/dt)
    df["q_P"] = df["r_P"] / df["Biomasa_filtrada"]

    # 4. Balances globales y rendimientos observados
    s_inicial = df[col_sustrato].iloc[0]
    s_final = df[col_sustrato].iloc[-1]
    s_consumido = s_inicial - s_final

    p_inicial = df[col_producto].iloc[0]
    p_max = df[col_producto].max()
    p_producido = p_max - p_inicial

    x_inicial = df[col_biomasa].iloc[0]
    x_final = df[col_biomasa].iloc[-1]
    x_producido = x_final - x_inicial

    # Rendimientos macroscópicos
    y_ps = (p_producido / s_consumido) if s_consumido > 0 else 0.0
    y_xs = (x_producido / s_consumido) if s_consumido > 0 else 0.0

    # Valores máximos
    mu_max = df["mu"].max()
    t_duplicacion = (np.log(2) / mu_max) if mu_max > 0 else None

    metricas = {
        "sustrato_consumido": round(s_consumido, 4),
        "producto_maximo": round(p_max, 4),
        "biomasa_final": round(x_final, 4),
        "Y_ps": round(y_ps, 4),
        "Y_xs": round(y_xs, 4),
        "mu_max": round(mu_max, 4),
        "t_duplicacion_h": round(t_duplicacion, 2) if t_duplicacion else None,
        "max_r_P": round(df["r_P"].max(), 4),
        "max_r_S": round(df["r_S"].max(), 4),
    }

    return df, metricas
