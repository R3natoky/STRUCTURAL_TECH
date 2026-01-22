import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

def verify_environment():
    print("=== Verificación de Entorno Estructural ===")
    print(f"Versión de Python: {sys.version}")
    print(f"Ruta del ejecutable: {sys.executable}")
    
    # Verificar Pandas
    try:
        df = pd.DataFrame({
            'Carga (kN)': [0, 10, 20, 30],
            'Deformación (mm)': [0, 0.5, 1.1, 1.8]
        })
        print(f"Pandas ok (v{pd.__version__})")
        print("DataFrame de prueba:")
        print(df)
    except Exception as e:
        print(f"Error en Pandas: {e}")

    # Verificar NumPy
    try:
        arr = np.array([1, 2, 3])
        print(f"NumPy ok (v{np.__version__})")
    except Exception as e:
        print(f"Error en NumPy: {e}")

    # Verificar Matplotlib (sin mostrar ventana para evitar bloqueos)
    try:
        plt.figure()
        plt.plot([0, 1], [0, 1])
        plt.title("Prueba de Renderizado")
        plt.close()
        print(f"Matplotlib ok (v{plt.__version__})")
    except Exception as e:
        print(f"Error en Matplotlib: {e}")
        
    print("===========================================")

if __name__ == "__main__":
    verify_environment()
