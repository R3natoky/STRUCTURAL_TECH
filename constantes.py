"""
constantes.py
Almacena constantes físicas y factores de conversión para análisis estructural.
Sistema Base Interno: SI (Newtons, mm, MPa)
"""

# --- Factores de Conversión de Entrada (Usuario -> Sistema) ---
# Presión / Esfuerzo
KG_CM2_A_MPA = 0.0980665  # 1 kgf/cm² ≈ 0.098 MPa
MPA_A_KG_CM2 = 1 / KG_CM2_A_MPA

# Fuerza
TON_A_N = 9806.65         # 1 Tonelada fuerza ≈ 9806 N
KG_A_N = 9.80665          # 1 kg fuerza ≈ 9.8 N

# Longitud
M_A_MM = 1000.0           # 1 metro = 1000 mm
CM_A_MM = 10.0            # 1 cm = 10 mm

# Momento
TON_M_A_N_MM = TON_A_N * M_A_MM  # Ton-m a N-mm

# --- Constantes de Materiales (Defectos) ---
MODULO_ELASTICIDAD_ACERO = 200000.0  # MPa (N/mm²)
BETA_1_DEFAULT = 0.85                # Para f'c <= 28 MPa

# --- Constantes de Diseño (ACI 318M / E.060) ---
PHI_FLEXION = 0.90
RECUBRIMIENTO_PROMEDIO = 60.0        # mm (asumiendo una capa)
# Agrega esto a constantes.py

# Diccionario completo: Nombre comercial -> (Area mm², Diametro mm)
# Fuente: ASTM A615
VARILLAS_INFO = {
    "3/8": {"area": 71.0, "diam": 9.5},
    "1/2": {"area": 129.0, "diam": 12.7},
    "5/8": {"area": 199.0, "diam": 15.9},
    "3/4": {"area": 284.0, "diam": 19.1},
    "1":   {"area": 510.0, "diam": 25.4},
    "1 3/8": {"area": 1006.0, "diam": 35.8} # La famosa #11
}

RECUBRIMIENTO_VIGA = 40.0 # mm (ACI vigas no expuestas)
DIAMETRO_ESTRIBO_DEF = 9.5 # mm (estribo de 3/8")
SEPARACION_MINIMA_CONCRETO = 25.0 # mm