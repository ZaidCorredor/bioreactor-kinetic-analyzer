import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_perfil_cinetico(df):
    """
    df debe contener las columnas:
    'Tiempo proceso (h)', 'Glucosa (g/L)', 'Etanol (g/L)', 'Biomasa (g/L)'
    y opcionalmente sus versiones suavizadas con savgol_filter.
    """
    # 1. Crear figura con eje secundario configurado
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    t = df["Tiempo proceso (h)"]

    # 2. Curva de Glucosa (Sustrato - Eje primario)
    fig.add_trace(
        go.Scatter(
            x=t,
            y=df["Glucosa (g/L)"],
            mode="lines+markers",
            name="Glucosa (g/L)",
            line=dict(color="#1f77b4", width=2.5),
            marker=dict(size=6)
        ),
        secondary_y=False
    )

    # 3. Curva de Etanol (Producto - Eje primario)
    fig.add_trace(
        go.Scatter(
            x=t,
            y=df["Etanol (g/L)"],
            mode="lines+markers",
            name="Etanol (g/L)",
            line=dict(color="#2ca02c", width=2.5),
            marker=dict(size=6)
        ),
        secondary_y=False
    )

    # 4. Curva de Biomasa (Células - Eje secundario para escala fina)
    fig.add_trace(
        go.Scatter(
            x=t,
            y=df["Biomasa (g/L)"],
            mode="lines+markers",
            name="Biomasa (g/L)",
            line=dict(color="#d62728", width=2.5, dash="dash"),
            marker=dict(size=6)
        ),
        secondary_y=True
    )

    # 5. Configurar diseño usando la sintaxis moderna (sin titlefont)
    fig.update_layout(
        title=dict(
            text="Cinética de Fermentación en Lote (Batch)",
            font=dict(size=18, family="Arial")
        ),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=60, r=60, t=80, b=60)
    )

    # Eje X
    fig.update_xaxes(
        title=dict(
            text="Tiempo de Proceso (h)",
            font=dict(size=13, color="#333333")
        ),
        showgrid=True,
        gridcolor="#eaeaea"
    )

    # Eje Y Primario (Sustrato / Producto)
    fig.update_yaxes(
        title=dict(
            text="Glucosa & Etanol (g/L)",
            font=dict(size=13, color="#1f77b4")
        ),
        secondary_y=False,
        showgrid=True,
        gridcolor="#eaeaea"
    )

    # Eje Y Secundario (Biomasa)
    fig.update_yaxes(
        title=dict(
            text="Biomasa (g/L)",
            font=dict(size=13, color="#d62728")
        ),
        secondary_y=True,
        showgrid=False  # Se apaga para no cruzar líneas de grilla
    )

    return fig
