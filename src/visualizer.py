"""
Módulo de visualización estática de alta resolución para publicaciones científicas.
Genera figuras multipanel de calidad exportables en formatos vectoriales (PDF) 
y rasterizados de alta densidad (PNG, 300+ DPI).
"""

import os
import matplotlib.pyplot as plt
import numpy as np

# Configuración global de estilo para publicación (estándar Elsevier / Springer / ACS)
def _aplicar_estilo_editorial():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "legend.frameon": False,
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.5,
        "figure.autolayout": False,
        "pdf.fonttype": 42,  # Evita convertir fuentes tipográficas en curvas/trazos en PDF
        "ps.fonttype": 42
    })


def exportar_figura_publicacion(df, output_path="figura_cinetica_q1", formatos=("png", "pdf"), dpi=300):
    """
    Genera un panel científico de 4 subgráficos (2x2):
      (a) Perfiles de concentración: Sustrato y Producto (S, P)
      (b) Cinética celular: Biomasa experimental y filtrada (X)
      (c) Velocidades volumétricas de reacción instantáneas (r_S, r_P, r_X)
      (d) Velocidades específicas de reacción normalizadas (q_S, q_P, mu)

    Parámetros:
      df: DataFrame procesado con columnas calculadas por kinetics.py
      output_path: Nombre base del archivo de salida (sin extensión)
      formatos: Tupla con los formatos deseados (ej. ('png', 'pdf'))
      dpi: Densidad de píxeles por pulgada (mínimo 300 para Q1)
    """
    _aplicar_estilo_editorial()
    
    t = df["Tiempo proceso (h)"]
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.8), sharex="col", dpi=dpi)
    
    # Paleta de colores sobria y contrastante
    c_s = "#1f77b4"  # Glucosa / Sustrato (Azul)
    c_p = "#2ca02c"  # Etanol / Producto (Verde)
    c_x = "#d62728"  # Biomasa (Rojo oscuro)
    c_mu = "#7f7f7f" # Velocidad específica de crecimiento (Gris grafito / Púrpura)

    # -------------------------------------------------------------------------
    # PANEL (a): Sustrato (Glucosa) y Producto (Etanol)
    # -------------------------------------------------------------------------
    ax_a = axs[0, 0]
    if "Glucosa (g/L)" in df.columns:
        ax_a.scatter(t, df["Glucosa (g/L)"], color=c_s, s=18, facecolors='none', edgecolors=c_s, label="Glucosa (exp)", zorder=3)
    if "Glucosa_filtrada" in df.columns:
        ax_a.plot(t, df["Glucosa_filtrada"], color=c_s, linestyle="-", label="Glucosa (filtro S-G)")
        
    if "Etanol (g/L)" in df.columns:
        ax_a.scatter(t, df["Etanol (g/L)"], color=c_p, s=18, facecolors='none', edgecolors=c_p, label="Etanol (exp)", zorder=3)
    if "Etanol_filtrada" in df.columns:
        ax_a.plot(t, df["Etanol_filtrada"], color=c_p, linestyle="-", label="Etanol (filtro S-G)")
        
    ax_a.set_ylabel("Concentración ($g\\cdot L^{-1}$)")
    ax_a.set_ylim(bottom=0)
    ax_a.grid(True, linestyle=":", alpha=0.6)
    ax_a.legend(loc="upper right")
    ax_a.text(0.03, 0.92, "(a)", transform=ax_a.transAxes, fontweight="bold", fontsize=10)

    # -------------------------------------------------------------------------
    # PANEL (b): Crecimiento de Biomasa Celular
    # -------------------------------------------------------------------------
    ax_b = axs[0, 1]
    col_bio_filt = "Biomasa_filtrada" if "Biomasa_filtrada" in df.columns else "Biomasa (g/L)"
    
    if "Biomasa (g/L)" in df.columns:
        ax_b.scatter(t, df["Biomasa (g/L)"], color=c_x, s=18, facecolors='none', edgecolors=c_x, label="Biomasa (exp)", zorder=3)
    if col_bio_filt in df.columns:
        ax_b.plot(t, df[col_bio_filt], color=c_x, linestyle="-", label="Biomasa (filtro S-G)")
        
    ax_b.set_ylabel("Biomasa $X$ ($g\\cdot L^{-1}$)")
    ax_b.set_ylim(bottom=0)
    ax_b.grid(True, linestyle=":", alpha=0.6)
    ax_b.legend(loc="lower right")
    ax_b.text(0.03, 0.92, "(b)", transform=ax_b.transAxes, fontweight="bold", fontsize=10)

    # -------------------------------------------------------------------------
    # PANEL (c): Velocidades Volumétricas de Reacción (r_i)
    # -------------------------------------------------------------------------
    ax_c = axs[1, 0]
    if "r_S" in df.columns:
        ax_c.plot(t, df["r_S"], color=c_s, linestyle="--", label="$-r_S$ (consumo)")
    if "r_P" in df.columns:
        ax_c.plot(t, df["r_P"], color=c_p, linestyle="-", label="$r_P$ (formación)")
    if "r_X" in df.columns:
        ax_c.plot(t, df["r_X"], color=c_x, linestyle="-.", label="$r_X$ (crecimiento)")

    ax_c.set_xlabel("Tiempo de proceso ($h$)")
    ax_c.set_ylabel("Vel. volumétrica ($g\\cdot L^{-1}\\cdot h^{-1}$)")
    ax_c.set_ylim(bottom=0)
    ax_c.grid(True, linestyle=":", alpha=0.6)
    ax_c.legend(loc="upper right")
    ax_c.text(0.03, 0.92, "(c)", transform=ax_c.transAxes, fontweight="bold", fontsize=10)

    # -------------------------------------------------------------------------
    # PANEL (d): Velocidades Específicas de Reacción (q_i y mu)
    # -------------------------------------------------------------------------
    ax_d = axs[1, 1]
    ax_d2 = ax_d.twinx()  # Eje secundario para q_S y q_P (diferente orden de magnitud que mu)

    lineas, etiquetas = [], []

    if "mu" in df.columns:
        l1 = ax_d.plot(t, df["mu"], color=c_mu, linestyle="-", label="$\\mu$ ($h^{-1}$)")
        lineas.extend(l1)
        etiquetas.append("$\\mu$ ($h^{-1}$)")

    if "q_S" in df.columns:
        l2 = ax_d2.plot(t, df["q_S"], color=c_s, linestyle=":", label="$q_S$")
        lineas.extend(l2)
        etiquetas.append("$q_S$")

    if "q_P" in df.columns:
        l3 = ax_d2.plot(t, df["q_P"], color=c_p, linestyle="--", label="$q_P$")
        lineas.extend(l3)
        etiquetas.append("$q_P$")

    ax_d.set_xlabel("Tiempo de proceso ($h$)")
    ax_d.set_ylabel("Vel. específica $\\mu$ ($h^{-1}$)", color=c_mu)
    ax_d2.set_ylabel("$q_i$ ($g\\cdot g_{X}^{-1}\\cdot h^{-1}$)", color="#333333")
    
    ax_d.set_ylim(bottom=0)
    ax_d2.set_ylim(bottom=0)
    ax_d.grid(True, linestyle=":", alpha=0.6)
    
    # Unificar leyenda de ambos ejes en un solo cuadro
    ax_d.legend(lineas, etiquetas, loc="upper right")
    ax_d.text(0.03, 0.92, "(d)", transform=ax_d.transAxes, fontweight="bold", fontsize=10)

    # Ajuste milimétrico de espaciado
    plt.tight_layout()

    # Guardar en todos los formatos solicitados
    rutas_generadas = []
    for fmt in formatos:
        nombre_completo = f"{output_path}.{fmt}"
        plt.savefig(nombre_completo, format=fmt, dpi=dpi, bbox_inches="tight")
        rutas_generadas.append(nombre_completo)

    plt.close(fig)
    return rutas_generadas
