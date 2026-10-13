from pathlib import Path
import pandas as pd

def cargar_datos(ruta_datos):
    ruta = Path(ruta_datos)
    if ruta.suffix.lower() == ".xlsx":
        return pd.read_excel(ruta)
    if ruta.suffix.lower() == ".csv":
        return pd.read_csv(ruta)
    raise ValueError("El archivo debe tener extensión .xlsx o .csv")