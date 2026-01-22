import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from analisis_estructural import VigaRectangular
import constantes as const

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="VigaCalc Pro", layout="wide")
st.title("🏗️ VigaCalc Pro: Diseño Doblemente Reforzado")

# --- 2. DEFINICIÓN DE LA FUNCIÓN DE DIBUJO PROFESIONAL ---
def dibujar_viga_completa(viga, d_inf, d_sup):
    """
    Dibuja la sección transversal con cotas (dimensiones) estilo plano.
    """
    # Configuración de figura (Tamaño cuadrado para proporción)
    fig, ax = plt.subplots(figsize=(4, 4))
    
    # Datos geométricos
    B, H = viga.base, viga.altura
    rec = const.RECUBRIMIENTO_VIGA
    
    # --- A. ELEMENTOS ESTRUCTURALES ---
    
    # 1. Concreto (Gris Claro)
    ax.add_patch(patches.Rectangle((0, 0), B, H, fc='#E0E0E0', ec='black', lw=2, zorder=1))
    
    # 2. Estribo (Azul Punteado)
    w_est = B - 2*rec
    h_est = H - 2*rec
    ax.add_patch(patches.Rectangle((rec, rec), w_est, h_est, fc='none', ec='blue', ls='--', lw=1, zorder=2))
    
    # Función auxiliar para dibujar filas de varillas
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
            # zorder=3 para que las varillas queden encima del estribo
            ax.add_patch(patches.Circle((x, y_pos), db/2, fc=color, ec='black', zorder=3))

    # 3. Acero Inferior (Rojo)
    if d_inf and d_inf["resultado"]["cantidad"] > 0:
        cant = d_inf["resultado"]["cantidad"]
        capas = d_inf["resultado"].get("capas", 1)
        varilla = d_inf["resultado"]["varilla"]
        db = const.VARILLAS_INFO[varilla]["diam"]
        y_base = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
        
        if capas == 1:
            dibujar_fila(cant, varilla, y_base, '#D32F2F')
        else:
            c1 = d_inf["resultado"].get("max_por_capa", int(cant/2))
            c2 = cant - c1
            dibujar_fila(c1, varilla, y_base, '#D32F2F')
            dibujar_fila(c2, varilla, y_base + 35, '#D32F2F')

    # 4. Acero Superior (Verde)
    if d_sup and d_sup["resultado"]["cantidad"] > 0:
        cant = d_sup["resultado"]["cantidad"]
        varilla = d_sup["resultado"]["varilla"]
        db = const.VARILLAS_INFO[varilla]["diam"]
        y_top = H - (rec + const.DIAMETRO_ESTRIBO_DEF + db/2)
        dibujar_fila(cant, varilla, y_top, '#2E7D32')

    # --- B. COTAS (DIMENSIONES) ESTILO CAD ---
    
    def dibujar_cota(x1, y1, x2, y2, texto, offset=30, orientacion='h'):
        """Dibuja una línea de cota con texto"""
        ax.annotate("", xy=(x1, y1), xytext=(x2, y2),
                    arrowprops=dict(arrowstyle="|-|", lw=1.0, color='black'))
        
        # Posición del texto
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        if orientacion == 'h': # Horizontal (Base)
            ax.text(mid_x, y1 - offset, texto, ha='center', va='top', fontsize=10)
        else: # Vertical (Altura)
            ax.text(x1 - offset, mid_y, texto, ha='right', va='center', rotation=90, fontsize=10)

    # Cota Base (Abajo)
    dibujar_cota(0, -30, B, -30, f"b = {B/10:.0f} cm", offset=15, orientacion='h')
    
    # Cota Altura (Izquierda)
    dibujar_cota(-30, 0, -30, H, f"h = {H/10:.0f} cm", offset=15, orientacion='v')

    # --- C. AJUSTE DE CÁMARA (ZOOM) ---
    # Aumentamos los márgenes negativos para que quepan las cotas
    # Esto hace que la viga se vea más pequeña (efecto "zoom out")
    ax.set_xlim(-250, B + 50) 
    ax.set_ylim(-200, H + 50)
    ax.set_aspect('equal')
    ax.axis('off') # Sin ejes numéricos feos
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
    viga = VigaRectangular(b_cm, h_cm, fc, fy)
    viga.calcular_as(mu)

    dist_inf = viga.distribuir_acero(var_trac, viga.area_acero_traccion)
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
        
        st.markdown("### 👇 Acero Inferior")
        st.metric("As Requerido", f"{viga.area_acero_traccion:.2f} mm²")
        if dist_inf["exito"]:
            st.info(f"**{dist_inf['resultado']['cantidad']} varillas de {var_trac}\"**")
            st.caption(f"Disposición: {dist_inf['resultado']['detalle']}")
        else:
            st.error(dist_inf["mensaje"])

        st.markdown("### 👆 Acero Superior")
        if viga.area_acero_compresion > 0:
            st.metric("A's Requerido", f"{viga.area_acero_compresion:.2f} mm²")
            if dist_sup:
                if dist_sup["exito"]:
                    st.info(f"**{dist_sup['resultado']['cantidad']} varillas de {var_comp}\"**")
                else:
                    st.error(dist_sup["mensaje"])
        else:
            st.write("Solo acero mínimo constructivo.")

    with col_draw:
        st.subheader("🎨 Sección Detallada")
        figura = dibujar_viga_completa(viga, dist_inf, dist_sup)
        st.pyplot(figura)

except Exception as e:
    st.error(f"Error: {e}")