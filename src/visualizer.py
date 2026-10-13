import matplotlib.pyplot as plt

def graficar_cinetica(df):
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.12))

    t = df["Tiempo proceso (h)"]
    ax1.plot(t, df["Glucosa_filtrada"], color="blue", label="Glucosa")
    ax2.plot(t, df["Etanol_filtrada"], color="green", label="Etanol")
    ax3.plot(t, df["Biomasa_filtrada"], color="orange", label="Biomasa")

    ax1.set_xlabel("Tiempo (h)")
    ax1.set_ylabel("Glucosa (g/L)", color="blue")
    ax2.set_ylabel("Etanol (g/L)", color="green")
    ax3.set_ylabel("Biomasa (g/L)", color="orange")
    ax1.set_title("Perfiles Cinéticos de Fermentación")
    ax1.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    return fig