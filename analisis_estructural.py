import numpy as np
import math # Necesario para redondear hacia arriba
import constantes as const

class VigaRectangular:
    """
    Clase para calcular el refuerzo de una viga rectangular de concreto armado.
    
    Todas las propiedades internas se almacenan en Sistema Internacional:
    - Fuerzas: Newtons (N)
    - Longitudes: Milímetros (mm)
    - Esfuerzos: MegaPascales (MPa)
    """

    def __init__(self, base_cm, altura_cm, fc_kg_cm2, fy_kg_cm2):
        """
        Constructor de la viga.
        Recibe dimensiones en cm y materiales en kg/cm² (común en planos),
        pero los almacena internamente en mm y MPa.
        """
        # Conversión a SI (mm y MPa)
        self.base = base_cm * const.CM_A_MM
        self.altura = altura_cm * const.CM_A_MM
        self.fc = fc_kg_cm2 * const.KG_CM2_A_MPA
        self.fy = fy_kg_cm2 * const.KG_CM2_A_MPA
        
        # Propiedades calculadas
        self.area_acero = 0.0
        self.mensaje = ""
        self._calcular_beta1()

    def _calcular_beta1(self):
        """Calcula el factor β1 según ACI 318M para el bloque de compresión."""
        if self.fc <= 28.0:
            self.beta1 = 0.85
        elif self.fc >= 55.0:
            self.beta1 = 0.65
        else:
            self.beta1 = 0.85 - 0.05 * (self.fc - 28.0) / 7.0

    def calcular_as(self, mu_ton_m):
        """
        Calcula el área de acero requerida para un momento último dado.
        
        Args:
            mu_ton_m: Momento último en Toneladas-metro
        """
        # 1. Convertir Momento a N-mm
        mu_n_mm = mu_ton_m * const.TON_M_A_N_MM
        
        # 2. Definir peralte efectivo (d) estimado
        # Se asume recubrimiento al centroide de varillas.
        d = self.altura - const.RECUBRIMIENTO_PROMEDIO
        
        # 3. Iteración para encontrar 'a' (profundidad bloque compresión) y 'As'
        # Ecuación: Mu = phi * As * fy * (d - a/2)
        # Ecuación: a = (As * fy) / (0.85 * fc * b)
        
        a = self.altura * 0.1  # Semilla inicial: a = 10% de la altura
        phi = const.PHI_FLEXION
        
        for _ in range(20): # 20 iteraciones suelen ser suficientes para converger
            # Despejando As de la ecuación de momento
            self.area_acero = mu_n_mm / (phi * self.fy * (d - a / 2.0))
            
            # Recalculando 'a' con el nuevo As
            a_nuevo = (self.area_acero * self.fy) / (0.85 * self.fc * self.base)
            
            # Criterio de convergencia simple
            if abs(a_nuevo - a) < 0.01: 
                a = a_nuevo
                break
            a = a_nuevo

        # 4. Verificaciones Normativas (ACI 318M - Sistema Métrico)
        self._verificar_cuantias(d)

    def _verificar_cuantias(self, d):
        """Verifica acero mínimo y máximo según ACI 318M."""
        
        # Acero Mínimo (ACI 9.6.1.2)
        # Mayor de: (0.25 * sqrt(fc) / fy) * b * d   y   (1.4 / fy) * b * d
        min1 = (0.25 * np.sqrt(self.fc) / self.fy) * self.base * d
        min2 = (1.4 / self.fy) * self.base * d
        as_min = max(min1, min2)

        # Acero Máximo (Para asegurar ductilidad, deformación neta tracción >= 0.004 o 0.005)
        # Simplificación común: rho_max ≈ 0.75 * rho_balanceada (Diseño antiguo)
        # O control por deformación unitaria (Diseño actual ACI). 
        # Usaremos la aproximación clásica de ductilidad para este ejemplo:
        # c_max = 0.375 * d (para zona controlada por tracción)
        # a_max = self.beta1 * (0.375 * d)
        # As_max = (0.85 * fc * b * a_max) / fy
        
        c_limite_traccion = (3/8) * d # Límite aprox para deformación 0.005
        a_max = self.beta1 * c_limite_traccion
        as_max = (0.85 * self.fc * self.base * a_max) / self.fy

        if self.area_acero < as_min:
            self.area_acero = as_min
            self.mensaje = "Se usa Acero Mínimo"
        elif self.area_acero > as_max:
            self.mensaje = "¡CUIDADO! Se excede el Acero Máximo (Falla Frágil)"
        else:
            self.mensaje = "Diseño OK (Dúctil)"

    def __str__(self):
        """Representación en texto del objeto (devuelve valores en unidades usuales para lectura)."""
        return (f"--- VIGA RECTANGULAR ---\n"
                f"Dimensiones: {self.base/10:.1f} x {self.altura/10:.1f} cm\n"
                f"Materiales: f'c={self.fc * const.MPA_A_KG_CM2:.1f} kg/cm², fy={self.fy * const.MPA_A_KG_CM2:.0f} kg/cm²\n"
                f"Resultado As: {self.area_acero / 100:.2f} cm²\n"
                f"Estado: {self.mensaje}")

    def seleccionar_varillas(self, nombre_varilla):
        """
        Calcula cuántas varillas de un diámetro específico se necesitan
        para cubrir el area_acero calculada previamente.
        """
        # 1. Validación de seguridad (Programación defensiva)
        if self.area_acero == 0.0:
            return "Error: Primero debes calcular el As (ejecuta calcular_as)"
        
        # 2. Obtener el área de una sola varilla del diccionario de constantes
        if nombre_varilla not in const.VARILLAS_ESTANDAR:
            return f"Error: Varilla {nombre_varilla} no disponible en catálogo."
            
        area_unitaria = const.VARILLAS_ESTANDAR[nombre_varilla]
        
        # 3. Cálculo del número de varillas
        # Usamos self.area_acero que FUE CALCULADO EN EL OTRO MÉTODO
        numero_necesario = self.area_acero / area_unitaria
        
        # 4. Redondear al entero superior (no puedes poner 2.3 varillas)
        numero_entero = math.ceil(numero_necesario)
        
        # 5. Guardar este nuevo resultado en el estado del objeto
        self.refuerzo_propuesto = f"{numero_entero} varillas de {nombre_varilla}\""
        
        # 6. Verificación rápida de cuantía real vs teórica
        area_real = numero_entero * area_unitaria
        
        return {
            "descripcion": self.refuerzo_propuesto,
            "area_req": round(self.area_acero, 1),
            "area_provista": round(area_real, 1),
            "ratio_seguridad": round(area_real / self.area_acero, 2)
        }
    
    def distribuir_acero(self, nombre_varilla):
        """
        Calcula la disposición de varillas.
        
        Raises:
            ValueError: Si el estado de la viga no permite calcular (As=0) 
                        o la varilla no existe.
        
        Returns:
            dict: Diccionario estandarizado con estructura:
                  {
                      "exito": bool,      # True si cumple criterios constructivos
                      "mensaje": str,     # Detalle del resultado o error de diseño
                      "resultado": dict   # Datos técnicos (cantidad, capas, espaciamiento)
                  }
        """
        # --- 1. VALIDACIÓN CON EXCEPTIONS (Errores Fatales) ---
        # Si esto falla, el programa salta al bloque 'except' inmediatamente.
        
        if self.area_acero <= 0:
            raise ValueError("Estado inválido: El As es 0. Ejecuta calcular_as() antes de distribuir.")
            
        if nombre_varilla not in const.VARILLAS_INFO:
            # Es útil mostrar qué varillas sí son válidas en el error
            opciones = list(const.VARILLAS_INFO.keys())
            raise ValueError(f"Varilla '{nombre_varilla}' no encontrada. Opciones: {opciones}")

        # --- 2. CÁLCULOS (Lógica de Negocio) ---
        info_varilla = const.VARILLAS_INFO[nombre_varilla]
        db = info_varilla["diam"]
        area_b = info_varilla["area"]
        
        # Cantidad matemática
        num_total = math.ceil(self.area_acero / area_b)
        
        # Geometría
        b_disponible = self.base - (2 * const.RECUBRIMIENTO_VIGA) - (2 * const.DIAMETRO_ESTRIBO_DEF)
        separacion_norma = max(const.SEPARACION_MINIMA_CONCRETO, db)
        
        # Capacidad por capa
        # Evitamos división por cero si la viga es absurdamene delgada
        ancho_ocupado_por_varilla = db + separacion_norma
        if ancho_ocupado_por_varilla <= 0:
             raise ValueError("Error geométrico crítico en dimensiones de varilla/separación.")

        max_por_capa = int((b_disponible + separacion_norma) / ancho_ocupado_por_varilla)

        # --- 3. CONSTRUCCIÓN DEL DICCIONARIO ESTANDARIZADO ---
        # Preparamos la estructura base
        respuesta = {
            "exito": True,
            "mensaje": "Distribución Conforme",
            "resultado": {
                "varilla": nombre_varilla,
                "cantidad": num_total,
                "capas": 1,
                "detalle": "",
                "area_real": num_total * area_b
            }
        }

        # Verificaciones de Diseño (No rompen el programa, solo marcan exito=False)
        if max_por_capa < 2:
            respuesta["exito"] = False
            respuesta["mensaje"] = "FALLA: Viga demasiado angosta para esta varilla (b_util insuficiente)."
            respuesta["resultado"]["cantidad"] = 0
            return respuesta

        # Lógica de capas
        if num_total <= max_por_capa:
            respuesta["resultado"]["detalle"] = f"1 capa de {num_total}"
        else:
            capa1 = max_por_capa
            capa2 = num_total - max_por_capa
            respuesta["resultado"]["capas"] = 2
            respuesta["resultado"]["detalle"] = f"2 capas: {capa1} (inf) + {capa2} (sup)"
            
            # Criterio de fallo por congestión
            if capa2 > max_por_capa:
                respuesta["exito"] = False
                respuesta["mensaje"] = "FALLA: Congestión excesiva. Se requieren más de 2 capas."
            elif num_total > max_por_capa: # Es 2 capas, pero aviso
                 respuesta["mensaje"] = "ATENCIÓN: Se requieren 2 capas (Diseño aceptable pero no óptimo)."

        return respuesta

# --- Bloque de Prueba ---
if __name__ == "__main__":
    viga = VigaRectangular(30, 60, 210, 4200)
    viga.calcular_as(24)
    
    print(f"Demanda de Acero: {viga.area_acero:.2f} mm²\n")

    # Lista de varillas a probar
    varillas_a_probar = ["1", "3/4", "5/8"]

    for diametro in varillas_a_probar:
        print(f"--- Probando varilla {diametro} ---")
        
        try:
            # 1. Intentamos ejecutar la lógica
            datos = viga.distribuir_acero(diametro)
            
            # 2. Verificamos si el diseño fue exitoso o fallido (pero calculado)
            if datos["exito"]:
                print(f"✅ APROBADO: {datos['mensaje']}")
                print(f"   Detalle: {datos['resultado']['detalle']}")
            else:
                print(f"⚠️ NO CONFORME: {datos['mensaje']}")
                print(f"   (Se requerirían {datos['resultado']['cantidad']} varillas)")

        except ValueError as error_fatal:
            # 3. Capturamos errores de mal uso (Inputs incorrectos)
            print(f"⛔ ERROR CRÍTICO DE EJECUCIÓN: {error_fatal}")
        
        print("") # Salto de linea
    