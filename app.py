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
try:
    viga = VigaRectangular(b_cm, h_cm, fc, fy)
    viga.calcular_as(mu)

    # Distribuir ACERO INFERIOR (Tracción)
    dist_inf = viga.distribuir_acero(var_trac, viga.area_acero_traccion)

    # Distribuir ACERO SUPERIOR (Compresión) - Solo si es necesario
    dist_sup = None
    if viga.area_acero_compresion > 0:
        dist_sup = viga.distribuir_acero(var_comp, viga.area_acero_compresion)

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

    with col_draw:
        st.subheader("🎨 Sección Transversal")
        fig = dibujar_viga_completa(viga, dist_inf, dist_sup)
        st.pyplot(fig)

except Exception as e:
    st.error(f"Se produjo un error en el cálculo: {e}")
    st.info("Por favor, verifica los datos de entrada (Dimensiones y Momentos).")

# --- DIBUJO ---
# --- FUNCIÓN DE DIBUJO CORREGIDA ---
def dibujar_viga_completa(viga, d_inf, d_sup):
    # Creamos la figura
    fig, ax = plt.subplots(figsize=(4, 5))
    
    # Datos geométricos
    B, H = viga.base, viga.altura
    rec = const.RECUBRIMIENTO_VIGA
    
    # 1. Dibujar Concreto (Rectángulo Principal)
    # fc='#E0E0E0' es gris claro, ec='black' es borde negro
    ax.add_patch(patches.Rectangle((0, 0), B, H, fc='#E0E0E0', ec='black', lw=2))
    
    # 2. Dibujar Estribo (Linea punteada azul)
    w_est = B - 2*rec
    h_est = H - 2*rec
    ax.add_patch(patches.Rectangle((rec, rec), w_est, h_est, fc='none', ec='blue', ls='--', lw=1))
    
    # Función auxiliar interna para dibujar una fila de círculos
    def dibujar_fila(cantidad, nombre_varilla, y_pos, color):
        info = const.VARILLAS_INFO[nombre_varilla]
        db = info["diam"]
        
        # Ancho disponible dentro del estribo
        ancho_util = w_est - 2*const.DIAMETRO_ESTRIBO_DEF
        
        # Cálculo de coordenadas X
        if cantidad == 1:
            xs = [B/2] # Si es 1, va al centro
        else:
            # Espaciamiento entre centros de varillas
            sep = (ancho_util - cantidad*db) / (cantidad - 1) if cantidad > 1 else 0
            # Coordenada de la primera varilla (izquierda)
            start_x = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
            # Generamos lista de coordenadas
            xs = [start_x + i*(db + sep) for i in range(cantidad)]
            
        # Dibujamos cada círculo
        for x in xs:
            ax.add_patch(patches.Circle((x, y_pos), db/2, fc=color, ec='black'))

    # 3. Dibujar ACERO INFERIOR (Rojo)
    if d_inf and d_inf["resultado"]["cantidad"] > 0:
        cant = d_inf["resultado"]["cantidad"]
        capas = d_inf["resultado"].get("capas", 1)
        varilla = d_inf["resultado"]["varilla"]
        db = const.VARILLAS_INFO[varilla]["diam"]
        
        # Posición Y base (primera capa de abajo hacia arriba)
        y_base = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
        
        if capas == 1:
            dibujar_fila(cant, varilla, y_base, '#D32F2F') # Rojo
        else:
            # Si hay 2 capas, dividimos visualmente
            c1 = d_inf["resultado"].get("max_por_capa", int(cant/2))
            c2 = cant - c1
            dibujar_fila(c1, varilla, y_base, '#D32F2F')
            dibujar_fila(c2, varilla, y_base + 35, '#D32F2F') # 35mm más arriba

    # 4. Dibujar ACERO SUPERIOR (Verde)
    if d_sup and d_sup["resultado"]["cantidad"] > 0:
        cant = d_sup["resultado"]["cantidad"]
        varilla = d_sup["resultado"]["varilla"]
        db = const.VARILLAS_INFO[varilla]["diam"]
        
        # Posición Y superior (desde arriba hacia abajo)
        y_top = H - (rec + const.DIAMETRO_ESTRIBO_DEF + db/2)
        
        dibujar_fila(cant, varilla, y_top, '#2E7D32') # Verde Oscuro

    # --- CORRECCIÓN CRÍTICA ---
    # Obligamos a matplotlib a mirar la zona donde está la viga
    ax.set_xlim(-50, B + 50)
    ax.set_ylim(-50, H + 50)
    ax.set_aspect('equal')
    ax.axis('off') # Ocultamos los números de los ejes
    plt.tight_layout()
    
    return fig