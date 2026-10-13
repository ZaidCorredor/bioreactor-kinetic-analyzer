import matplotlib.pyplot as plt
from src.data_loader import cargar_datos
from src.kinetics import calcular_cinetica
from src.visualizer import graficar_cinetica

if __name__ == "__main__":
    df = cargar_datos("data/excelprueba.xlsx")
    df_proc, resumen = calcular_cinetica(df)
    print("Métricas calculadas:", resumen)
    fig = graficar_cinetica(df_proc)
    plt.show()