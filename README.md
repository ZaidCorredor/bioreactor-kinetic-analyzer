# Bioreactor Batch Kinetic Analyzer & Filtering Pipeline

A Python data pipeline designed to process raw fermentation logs (`.csv` / `.xlsx`), apply **Savitzky-Golay filters** to eliminate experimental noise from spectrophotometric/HPLC assays, and calculate key bioprocess parameters:
- Specific growth rate ($\mu$) and maximum growth rate ($\mu_{\max}$)
- Product and biomass yields ($Y_{P/S}$, $Y_{X/S}$)
- Volumetric rates for substrate consumption and product formation ($r_S$, $r_P$, $r_X$)

## Project Structure
- `src/data_loader.py`: Safe parsing and schema validation.
- `src/kinetics.py`: Filtering and analytical derivative calculations using SciPy.
- `src/visualizer.py`: 3-axis kinetic plotting with Matplotlib.

## Quickstart
To run this project locally, execute the following commands in your terminal:

```bash
git clone https://github.com/tu-usuario/bioreactor-kinetic-analyzer.git
cd bioreactor-kinetic-analyzer
pip install -r requirements.txt
python main.py
```
## Demo en Vivo
Puedes probar la aplicación interactiva aquí: 
[Bioreactor Kinetic Analyzer en Streamlit Cloud](https://bioreactor-kinetic-analyzer.streamlit.app/)
