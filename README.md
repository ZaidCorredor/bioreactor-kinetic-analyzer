# 🧪 Bioreactor Batch Kinetic Analyzer & Filtering Pipeline

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bioreactor-kinetic-analyzer.streamlit.app)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Una solución integral en Python para el procesamiento, modelado cinético y visualización automatizada de cultivos en reactores por lote (*batch*). La aplicación elimina el ruido experimental analítico mediante filtrado polinomial de **Savitzky-Golay** con selección automatizada de ventana, y calcula parámetros de balance macroscópico y velocidades de reacción bajo estándares de ingeniería de bioprocesos.

---

## 🚀 Demo en Vivo
Puedes probar la plataforma interactiva directamente en la nube:  
👉 **[Bioreactor Kinetic Analyzer en Streamlit Cloud](https://bioreactor-kinetic-analyzer.streamlit.app)**

---

## 🔬 Capacidades y Métricas Calculadas

### 1. Parámetros Cinéticos y Rendimientos
- **Velocidad máxima específica de crecimiento ($\mu_{\max}$):** Determinada mediante regresión lineal semilogarítmica en ventana deslizante ($\ln X \text{ vs. } t$) acotada por umbral de correlación ($R^2 > 0.90$), eliminando sobreestimaciones causadas por inóculos bajos o efectos de borde numéricos.
- **Rendimientos estequiométricos globales:** Rendimiento producto/sustrato ($Y_{P/S}$) y biomasa/sustrato ($Y_{X/S}$).
- **Productividad volumétrica global de biomasa ($Q_X$):** Masa celular neta producida por unidad de volumen y tiempo total ($g\cdot L^{-1}\cdot h^{-1}$).

### 2. Velocidades Volumétricas de Reacción ($r_i$)
- Velocidad volumétrica de consumo de sustrato ($-r_S = -\frac{dS}{dt}$).
- Velocidad volumétrica de formación de producto ($r_P = \frac{dP}{dt}$).
- Velocidad volumétrica de crecimiento celular ($r_X = \frac{dX}{dt}$).

### 3. Velocidades Específicas de Reacción ($q_i$)
- Velocidad específica de consumo ($q_S = \frac{-r_S}{X}$).
- Velocidad específica de producción ($q_P = \frac{r_P}{X}$).
- Velocidad específica de crecimiento celular instantánea ($\mu(t) = \frac{r_X}{X}$).

---

## 📁 Estructura del Repositorio

```text
bioreactor-kinetic-analyzer/
├── app.py                  # Dashboard interactivo en Streamlit con visualizaciones multipanel Plotly
├── data/
│   └── excelprueba.xlsx    # Dataset experimental de muestra para pruebas
├── src/
│   ├── __init__.py
│   ├── kinetics.py         # Algoritmo de ventana óptima, filtro Savitzky-Golay y derivadas cinéticas
│   └── visualizer.py       # Generador de figuras estáticas de alta resolución (300 DPI, PDF/PNG Q1)
├── requirements.txt        # Librerías y dependencias del entorno
└── README.md               # Documentación general del proyecto
```

---

## 📊 Formato de Datos de Entrada

La aplicación procesa archivos en formato Excel (`.xlsx`) o CSV (`.csv`) que contengan las siguientes cabeceras exactas:

| Columna | Unidad típica | Descripción |
| :--- | :---: | :--- |
| Tiempo proceso (h) | h | Tiempo transcurrido del proceso |
| Glucosa (g/L) | g/L | Concentración de sustrato carbonado limitante |
| Etanol (g/L) | g/L | Concentración del producto metabólico principal |
| Biomasa (g/L) | g/L | Concentración de biomasa celular en peso seco |

---

## ⚙️ Instalación y Ejecución Local

Si deseas ejecutar o ampliar el proyecto de manera local:

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/tu-usuario/bioreactor-kinetic-analyzer.git](https://github.com/tu-usuario/bioreactor-kinetic-analyzer.git)
   cd bioreactor-kinetic-analyzer
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   # En Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # En Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependencias requeridas:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Iniciar la aplicación:**
   ```bash
   streamlit run app.py
   ```

---

## 🖼️ Exportación para Publicaciones Científicas

El módulo `src/visualizer.py` permite compilar las figuras del proceso en formato vectorial listo para enviar a revistas de alto impacto (Q1) como *Bioresource Technology* o *Biochemical Engineering Journal*:

```python
import pandas as pd
from src.kinetics import calcular_cinetica
from src.visualizer import exportar_figura_publicacion

# Carga y análisis cinético
df = pd.read_excel("data/excelprueba.xlsx")
df_procesado, metricas = calcular_cinetica(df, auto_ventana=True)

# Exportación a 300 DPI (genera panel a, b, c, d en PDF vectorial y PNG)
exportar_figura_publicacion(df_procesado, output_path="perfil_cinetico_q1", formatos=("png", "pdf"), dpi=300)
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.
