import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from analisis_estructural import VigaRectangular
import constantes as const

st.set_page_config(page_title="VigaCalc Pro", layout="wide")
st.title("🏗️ VigaCalc Pro: Diseño Doblemente Reforzado")

# --- INPUTS ---
with st.sidebar:
    st.header("1. Geometría")
    col1, col2 = st.columns(2)
    b_cm = col1.number_input("Base (cm)", 25.0, 100.0, 30.0, step=5.0)
    h_cm = col2.number_input("Altura (cm)", 30.0, 200.0, 60.0, step=5.0)
    
    st.header("2. Materiales y Carga")
    fc = st.selectbox("f'c (kg/cm²)", [210, 280, 350, 420])
    fy = st.number_input("fy (kg/cm²)", value=4200)
    mu = st.number_input("Momento Último (Tn-m)", 1.0, 200.0, 25.0, step=1.0)
    
    st.header("3. Detallado")
    var_trac = st.selectbox("Varilla Tracción (Inf)", list(const.VARILLAS_INFO.keys()), index=3) # 3/4
    var_comp = st.selectbox("Varilla Compresión (Sup)", list(const.VARILLAS_INFO.keys()), index=2) # 5/8

# --- CÁLCULOS ---
viga = VigaRectangular(b_cm, h_cm, fc, fy)
viga.calcular_as(mu)

# Distribuir ACERO INFERIOR (Tracción)
try:
    dist_inf = viga.distribuir_acero(var_trac, viga.area_acero_traccion)
except ValueError as e:
    st.error(f"Error Inf: {e}")
    st.stop()

# Distribuir ACERO SUPERIOR (Compresión) - Solo si es necesario
dist_sup = None
if viga.area_acero_compresion > 0:
    try:
        dist_sup = viga.distribuir_acero(var_comp, viga.area_acero_compresion)
    except ValueError as e:
        st.error(f"Error Sup: {e}")

# --- RESULTADOS ---
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
        st.info(f"**{dist_inf['resultado']['cantidad']} varillas de {var_trac}\"** ({dist_inf['resultado']['detalle']})")
    else:
        st.error(dist_inf["mensaje"])

    # Resultados Compresión
    st.markdown("### 👆 Acero Superior (Compresión)")
    if viga.area_acero_compresion > 0:
        st.metric("A's Requerido", f"{viga.area_acero_compresion:.2f} mm²")
        if dist_sup and dist_sup["exito"]:
            st.info(f"**{dist_sup['resultado']['cantidad']} varillas de {var_comp}\"**")
        elif dist_sup:
            st.error(dist_sup["mensaje"])
    else:
        st.caption("No se requiere refuerzo a compresión por cálculo.")
        st.write("(Se recomienda colocar acero mínimo de montaje, ej. 2 varillas)")

# --- DIBUJO ---
def dibujar_viga_completa(viga, d_inf, d_sup):
    fig, ax = plt.subplots(figsize=(4, 5))
    B, H = viga.base, viga.altura
    rec = const.RECUBRIMIENTO_VIGA
    
    # 1. Concreto y Estribo
    ax.add_patch(patches.Rectangle((0, 0), B, H, fc='#E0E0E0', ec='black', lw=2))
    w_est = B - 2*rec
    h_est = H - 2*rec
    ax.add_patch(patches.Rectangle((rec, rec), w_est, h_est, fc='none', ec='blue', ls='--', lw=1))
    
    # Función auxiliar para dibujar fila de varillas
    def dibujar_fila(cantidad, diametro, y_pos, color):
        info = const.VARILLAS_INFO[diametro]
        db = info["diam"]
        # Calcular posiciones X centradas
        ancho_util = w_est - 2*const.DIAMETRO_ESTRIBO_DEF
        if cantidad == 1:
            xs = [B/2]
        else:
            sep = (ancho_util - cantidad*db) / (cantidad - 1)
            start = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
            xs = [start + i*(db+sep) for i in range(cantidad)]
            
        for x in xs:
            ax.add_patch(patches.Circle((x, y_pos), db/2, fc=color, ec='black'))

    # 2. Dibujar INFERIOR (Rojo)
    if d_inf and d_inf["resultado"]["cantidad"] > 0:
        cant = d_inf["resultado"]["cantidad"]
        # Simplificación: si son 2 capas, dibujamos mitad y mitad visualmente
        capas = d_inf["resultado"]["capas"]
        db = const.VARILLAS_INFO[d_inf["resultado"]["varilla"]]["diam"]
        
        y_base = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
        
        if capas == 1:
            dibujar_fila(cant, d_inf["resultado"]["varilla"], y_base, '#D32F2F')
        else:
            # Dibujo simplificado de 2 capas
            c1 = d_inf["resultado"].get("max_por_capa", int(cant/2))
            c2 = cant - c1
            dibujar_fila(c1, d_inf["resultado"]["varilla"], y_base, '#D32F2F')
            dibujar_fila(c2, d_inf["resultado"]["varilla"], y_base + 30, '#D32F2F') # +30mm arriba

    # 3. Dibujar SUPERIOR (Verde oscuro)
    if d_sup and d_sup["resultado"]["cantidad"] > 0:
        cant = d_sup["resultado"]["cantidad"]
        db = const.VARILLAS_INFO[d_sup["resultado"]["varilla"]]["diam"]
        # Coordenada Y superior: H - rec - estribo - radio
        y_top = H - (rec + const.DIAMETRO_ESTRIBO_DEF + db/2)
        dibujar_fila(cant, d_sup["resultado"]["varilla"], y_top, 'green')

    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    return fig

with col_draw:
    st.pyplot(dibujar_viga_completa(viga, dist_inf, dist_sup))