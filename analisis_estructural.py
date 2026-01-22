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
# ... dentro de class VigaRectangular ...

    @property
    def area_acero(self):
        """
        Devuelve el acero a tracción por defecto cuando se llama a .area_acero
        Esto mantiene compatibilidad con código antiguo (como app.py)
        """
        return self.area_acero_traccion

    @area_acero.setter
    def area_acero(self, valor):
        """Permite asignar valor manualmente si fuera necesario"""
        self.area_acero_traccion = valor

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
        
        self._calcular_beta1()
        
        # Resultados
        self.area_acero_traccion = 0.0   # As (Abajo)
        self.area_acero_compresion = 0.0 # A's (Arriba)
        self.mensaje = ""
        
        # Asumimos recubrimiento superior igual al inferior para d'
        self.d_prima = const.RECUBRIMIENTO_PROMEDIO 

    def _calcular_beta1(self):
        if self.fc <= 28.0:
            self.beta1 = 0.85
        elif self.fc >= 55.0:
            self.beta1 = 0.65
        else:
            self.beta1 = 0.85 - 0.05 * (self.fc - 28.0) / 7.0

    def calcular_as(self, mu_ton_m):
        """
        Calcula el refuerzo considerando diseño simple o doblemente reforzado.
        """
        # 1. Preparación de datos
        mu_n_mm = mu_ton_m * const.TON_M_A_N_MM
        d = self.altura - const.RECUBRIMIENTO_PROMEDIO
        phi = const.PHI_FLEXION
        
        # 2. Calcular el Límite de la Viga Simplemente Reforzada
        # Según ACI, el límite dúctil seguro es cuando la deformación del acero es 0.005
        # Esto ocurre cuando c/d = 0.375
        c_limite = 0.375 * d
        a_limite = self.beta1 * c_limite
        
        # Capacidad nominal máxima permitida como viga simple (Mn_max)
        # Fuerza C (concreto) = 0.85 * fc * b * a_limite
        # Momento = C * (d - a_limite/2)
        cc_max = 0.85 * self.fc * self.base * a_limite
        mn_max_simple = cc_max * (d - a_limite / 2)
        mu_max_simple = phi * mn_max_simple

        # 3. TOMA DE DECISIÓN
        if mu_n_mm <= mu_max_simple:
            # --- CASO A: DISEÑO SIMPLEMENTE REFORZADO ---
            self._calcular_simple(mu_n_mm, d, phi)
            self.mensaje = "Diseño OK (Simplemente Reforzado)"
        else:
            # --- CASO B: DISEÑO DOBLEMENTE REFORZADO ---
            self._calcular_doble(mu_n_mm, d, phi, mn_max_simple, c_limite)
            self.mensaje = "Diseño OK (Doblemente Reforzado)"

    def _calcular_simple(self, mu, d, phi):
        """Iteración estándar para vigas simples"""
        self.area_acero_compresion = 0.0
        a = d * 0.2 # Semilla
        for _ in range(20):
            self.area_acero_traccion = mu / (phi * self.fy * (d - a / 2.0))
            a_nuevo = (self.area_acero_traccion * self.fy) / (0.85 * self.fc * self.base)
            if abs(a_nuevo - a) < 0.1: break
            a = a_nuevo
        
        # Verificar mínimo (simplificado)
        min_as = (0.25 * np.sqrt(self.fc) / self.fy) * self.base * d
        self.area_acero_traccion = max(self.area_acero_traccion, min_as)

    def _calcular_doble(self, mu, d, phi, mn_max_simple, c_limite):
        """
        Lógica para viga doblemente reforzada.
        Mu_total = Mu_concreto + Mu_acero_compresion
        """
        # 1. Determinar el momento "extra" que debe cargar el acero a compresión
        # Mn_requerido = Mu / phi
        # Mn_extra = Mn_requerido - Mn_max_concreto
        mn_requerido = mu / phi
        mn_extra = mn_requerido - mn_max_simple
        
        # 2. Verificar si el acero a compresión fluye (Strain Compatibility)
        # Triángulo de deformaciones: e_s' / 0.003 = (c - d') / c
        es_prima = 0.003 * (c_limite - self.d_prima) / c_limite
        
        # Esfuerzo en el acero de compresión (fs')
        fs_prima = es_prima * const.MODULO_ELASTICIDAD_ACERO
        
        # No puede ser mayor que fy
        fs_prima = min(fs_prima, self.fy)
        
        # 3. Calcular A's (Acero Compresión)
        # Mn_extra = A's * fs' * (d - d')
        self.area_acero_compresion = mn_extra / (fs_prima * (d - self.d_prima))
        
        # 4. Calcular As total (Acero Tracción)
        # As_total = As_max_simple + As_equilibrante_compresion
        # As_equilibrante * fy = A's * fs'
        as_max_simple = (0.85 * self.fc * self.base * (self.beta1 * c_limite)) / self.fy
        as_extra = self.area_acero_compresion * (fs_prima / self.fy)
        
        self.area_acero_traccion = as_max_simple + as_extra

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
    
    def distribuir_acero(self, nombre_varilla, area_a_cubrir=None):
        """
        Calcula varillas para un área específica.
        Si area_a_cubrir es None, usa el acero de tracción por defecto.
        """
        # 1. Definir qué área estamos calculando
        target = area_a_cubrir if area_a_cubrir is not None else self.area_acero_traccion
        
        # Si no se requiere acero (ej. compresión es 0), retornamos vacío pero con éxito
        if target <= 0:
            return {
                "exito": True, 
                "mensaje": "No requiere refuerzo", 
                "resultado": {"cantidad": 0, "capas": 0, "detalle": "Ninguno", "area_real": 0, "varilla": nombre_varilla}
            }

        # 2. Validaciones básicas
        if nombre_varilla not in const.VARILLAS_INFO:
            raise ValueError(f"Varilla {nombre_varilla} no existe")

        info_varilla = const.VARILLAS_INFO[nombre_varilla]
        db = info_varilla["diam"]
        area_b = info_varilla["area"]
        
        # 3. Cálculos Geométricos
        num_total = math.ceil(target / area_b)
        b_disponible = self.base - (2 * const.RECUBRIMIENTO_VIGA) - (2 * const.DIAMETRO_ESTRIBO_DEF)
        separacion_norma = max(const.SEPARACION_MINIMA_CONCRETO, db)
        
        ancho_ocupado_por_varilla = db + separacion_norma
        max_por_capa = int((b_disponible + separacion_norma) / ancho_ocupado_por_varilla)

        # 4. Construir Respuesta
        respuesta = {
            "exito": True,
            "mensaje": "OK",
            "resultado": {
                "varilla": nombre_varilla,
                "cantidad": num_total,
                "capas": 1,
                "detalle": "",
                "area_real": num_total * area_b,
                "max_por_capa": max_por_capa # Importante para el dibujo
            }
        }

        # Validaciones de Diseño
        if max_por_capa < 2:
            respuesta["exito"] = False
            respuesta["mensaje"] = "Viga muy angosta"
            return respuesta

        if num_total <= max_por_capa:
            respuesta["resultado"]["detalle"] = f"1 capa de {num_total}"
        else:
            capa1 = max_por_capa
            capa2 = num_total - max_por_capa
            respuesta["resultado"]["capas"] = 2
            respuesta["resultado"]["detalle"] = f"2 capas: {capa1} + {capa2}"
            
            if capa2 > max_por_capa:
                respuesta["exito"] = False
                respuesta["mensaje"] = "Congestión: Se requieren >2 capas"

        return respuesta
    
# --- Bloque de Prueba ---
if __name__ == "__main__":
    # Ejemplo: Viga de 30x60, Mu = 24 Ton-m (Suele requerir diseño doble)
    viga = VigaRectangular(30, 60, 210, 4200)
    viga.calcular_as(24)
    
    print(f"RESULTADOS DEL CÁLCULO:")
    print(f"  Acero Tracción (As): {viga.area_acero_traccion:.2f} mm²")
    print(f"  Acero Compresión (A's): {viga.area_acero_compresion:.2f} mm²")
    print(f"  Mensaje: {viga.mensaje}\n")

    # Lista de varillas a probar para tracción
    varilla_diseno = "3/4"
    print(f"--- Distribución para Tracción ({varilla_diseno}\") ---")
    
    try:
        datos = viga.distribuir_acero(varilla_diseno)
        if datos["exito"]:
            print(f"✅ OK: {datos['resultado']['detalle']} ({datos['resultado']['area_real']:.1f} mm² provistos)")
        else:
            print(f"⚠️ AVISO: {datos['mensaje']}")
    except Exception as e:
        print(f"⛔ ERROR: {e}")
    