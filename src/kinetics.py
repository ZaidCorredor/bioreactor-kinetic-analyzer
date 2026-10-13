import numpy as np
from scipy.signal import savgol_filter

def calcular_cinetica(df, ventana=5, orden=2):
    df = df.copy()
    dt = df["Tiempo proceso (h)"].diff().mean()

    # Filtrado de perfiles
    df["Glucosa_filtrada"] = savgol_filter(df["Glucosa (g/L)"], ventana, orden)
    df["Etanol_filtrada"] = savgol_filter(df["Etanol (g/L)"], ventana, orden)
    df["Biomasa_filtrada"] = np.clip(
        savgol_filter(df["Biomasa (g/L)"], ventana, orden), a_min=1e-3, a_max=None
    )

    # Derivadas analíticas (velocidades)
    df["r_glucosa (g/L/h)"] = -savgol_filter(df["Glucosa (g/L)"], ventana, orden, deriv=1, delta=dt)
    df["r_etanol (g/L/h)"] = savgol_filter(df["Etanol (g/L)"], ventana, orden, deriv=1, delta=dt)
    df["r_biomasa (g/L/h)"] = savgol_filter(df["Biomasa (g/L)"], ventana, orden, deriv=1, delta=dt)
    df["mu (h^-1)"] = df["r_biomasa (g/L/h)"] / df["Biomasa_filtrada"]

    # Resumen métricas
    glu_cons = df["Glucosa (g/L)"].iloc[0] - df["Glucosa (g/L)"].iloc[-1]
    et_prod = df["Etanol (g/L)"].max() - df["Etanol (g/L)"].iloc[0]
    bio_prod = df["Biomasa (g/L)"].iloc[-1] - df["Biomasa (g/L)"].iloc[0]

    resumen = {
        "Y_ps": round(et_prod / glu_cons, 4) if glu_cons > 0 else 0,
        "Y_xs": round(bio_prod / glu_cons, 4) if glu_cons > 0 else 0,
        "mu_max": round(df["mu (h^-1)"].max(), 4),
        "max_r_etanol": round(df["r_etanol (g/L/h)"].max(), 4)
    }
    return df, resumen