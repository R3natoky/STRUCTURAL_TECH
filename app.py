import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from analisis_estructural import VigaRectangular
import constantes as const

# --- 1. CONFIGURACIÓN DE LA PÁGINA (Debe ir primero) ---
st.set_page_config(page_title="VigaCalc Pro", layout="wide")
st.title("🏗️ VigaCalc Pro: Diseño Doblemente Reforzado")

# --- 2. DEFINICIÓN DE LA FUNCIÓN DE DIBUJO (Lo movemos ARRIBA para que Python la lea antes de usarla) ---
def dibujar_viga_completa(viga, d_inf, d_sup):
    """
    Dibuja la sección transversal con el zoom ajustado y varillas.
    """
    # Crear figura y ejes
    fig, ax = plt.subplots(figsize=(4, 5))
    
    # Datos geométricos
    B, H = viga.base, viga.altura
    rec = const.RECUBRIMIENTO_VIGA
    
    # A. Dibujar Concreto (Gris)
    ax.add_patch(patches.Rectangle((0, 0), B, H, fc='#E0E0E0', ec='black', lw=2))
    
    # B. Dibujar Estribo (Azul Punteado)
    w_est = B - 2*rec
    h_est = H - 2*rec
    ax.add_patch(patches.Rectangle((rec, rec), w_est, h_est, fc='none', ec='blue', ls='--', lw=1))
    
    # Función auxiliar interna para dibujar filas de varillas
    def dibujar_fila(cantidad, nombre_varilla, y_pos, color):
        info = const.VARILLAS_INFO[nombre_varilla]
        db = info["diam"]
        ancho_util = w_est - 2*const.DIAMETRO_ESTRIBO_DEF
        
        if cantidad == 1:
            xs = [B/2]
        else:
            sep = (ancho_util - cantidad*db) / (cantidad - 1) if cantidad > 1 else 0
            start_x = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
            xs = [start_x + i*(db + sep) for i in range(cantidad)]
            
        for x in xs:
            ax.add_patch(patches.Circle((x, y_pos), db/2, fc=color, ec='black'))

    # C. Dibujar Acero Inferior (Rojo - Tracción)
    if d_inf and d_inf["resultado"]["cantidad"] > 0:
        cant = d_inf["resultado"]["cantidad"]
        capas = d_inf["resultado"].get("capas", 1)
        varilla = d_inf["resultado"]["varilla"]
        db = const.VARILLAS_INFO[varilla]["diam"]
        y_base = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
        
        if capas == 1:
            dibujar_fila(cant, varilla, y_base, '#D32F2F')
        else:
            # Dibujo simplificado de 2 capas
            c1 = d_inf["resultado"].get("max_por_capa", int(cant/2))
            c2 = cant - c1
            dibujar_fila(c1, varilla, y_base, '#D32F2F')
            dibujar_fila(c2, varilla, y_base + 35, '#D32F2F')

    # D. Dibujar Acero Superior (Verde - Compresión)
    if d_sup and d_sup["resultado"]["cantidad"] > 0:
        cant = d_sup["resultado"]["cantidad"]
        varilla = d_sup["resultado"]["varilla"]
        db = const.VARILLAS_INFO[varilla]["diam"]
        y_top = H - (rec + const.DIAMETRO_ESTRIBO_DEF + db/2)
        dibujar_fila(cant, varilla, y_top, '#2E7D32')

    # --- E. AJUSTE DE ZOOM (CRÍTICO PARA QUE NO SE VEA BLANCO) ---
    ax.set_xlim(-50, B + 50)
    ax.set_ylim(-50, H + 50)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    return fig

# --- 3. BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("1. Geometría")
    col1, col2 = st.columns(2)
    b_cm = col1.number_input("Base (cm)", 20.0, 100.0, 30.0, step=5.0)
    h_cm = col2.number_input("Altura (cm)", 30.0, 200.0, 60.0, step=5.0)
    
    st.header("2. Materiales y Carga")
    fc = st.selectbox("f'c (kg/cm²)", [210, 280, 350, 420])
    fy = st.number_input("fy (kg/cm²)", value=4200)
    mu = st.number_input("Momento Último (Tn-m)", 0.1, 500.0, 15.0, step=0.5, format="%.2f")
    
    st.header("3. Detallado")
    var_trac = st.selectbox("Varilla Tracción (Inf)", list(const.VARILLAS_INFO.keys()), index=3)
    var_comp = st.selectbox("Varilla Compresión (Sup)", list(const.VARILLAS_INFO.keys()), index=2)

# --- 4. LÓGICA DE EJECUCIÓN ---
try:
    # A. Instanciar y Calcular
    viga = VigaRectangular(b_cm, h_cm, fc, fy)
    viga.calcular_as(mu)

    # B. Distribuir Aceros
    # Tracción (Siempre intentamos distribuirlo)
    dist_inf = viga.distribuir_acero(var_trac, viga.area_acero_traccion)
    
    # Compresión (Solo si el cálculo dice que se necesita)
    dist_sup = None
    if viga.area_acero_compresion > 0:
        dist_sup = viga.distribuir_acero(var_comp, viga.area_acero_compresion)

    # --- 5. MOSTRAR RESULTADOS ---
    col_res, col_draw = st.columns([1, 1.5])

    with col_res:
        st.subheader("📊 Análisis")
        if "Doblemente" in viga.mensaje:
            st.warning(f"Estado: {viga.mensaje}")
        else:
            st.success(f"Estado: {viga.mensaje}")
        
        st.divider()
        
        # Resultados Tracción
        st.markdown("### 👇 Acero Inferior (Tracción)")
        st.metric("As Requerido", f"{viga.area_acero_traccion:.2f} mm²")
        
        if dist_inf["exito"]:
            st.info(f"**{dist_inf['resultado']['cantidad']} varillas de {var_trac}\"**")
            st.caption(f"Disposición: {dist_inf['resultado']['detalle']}")
        else:
            st.error(dist_inf["mensaje"])

        # Resultados Compresión
        st.markdown("### 👆 Acero Superior (Compresión)")
        if viga.area_acero_compresion > 0:
            st.metric("A's Requerido", f"{viga.area_acero_compresion:.2f} mm²")
            if dist_sup:
                if dist_sup["exito"]:
                    st.info(f"**{dist_sup['resultado']['cantidad']} varillas de {var_comp}\"**")
                else:
                    st.error(dist_sup["mensaje"])
        else:
            st.write("No se requiere refuerzo a compresión por cálculo.")
            st.caption("(Se recomienda acero de montaje mínimo)")

    with col_draw:
        st.subheader("🎨 Sección Transversal")
        # LLAMADA CORRECTA: La función ya fue definida en el paso 2
        figura = dibujar_viga_completa(viga, dist_inf, dist_sup)
        st.pyplot(figura)

except Exception as e:
    st.error(f"Se produjo un error en el cálculo: {e}")
    st.info("Por favor, verifica los datos de entrada (Dimensiones y Momentos).")