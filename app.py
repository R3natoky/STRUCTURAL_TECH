import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Importamos tu lógica de negocio (POO)
from analisis_estructural import VigaRectangular
import constantes as const

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="VigaCalc Pro", layout="wide")

st.title("🏗️ VigaCalc Pro: Diseño de Vigas de Concreto")
st.markdown("---")

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("1. Geometría y Materiales")
    
    # Dimensiones
    col1, col2 = st.columns(2)
    b_cm = col1.number_input("Base (cm)", min_value=15.0, value=30.0, step=5.0)
    h_cm = col2.number_input("Altura (cm)", min_value=20.0, value=50.0, step=5.0)
    
    # Materiales
    fc_input = st.selectbox("Concreto f'c (kg/cm²)", [210, 280, 350, 420])
    fy_input = st.number_input("Acero fy (kg/cm²)", value=4200, step=100)
    
    st.header("2. Cargas")
    # CAMBIO 1: Usamos number_input para mayor precisión, igual que el acero
    mu_input = st.number_input("Momento Último Mu (Tn-m)", min_value=0.1, value=15.0, step=0.1, format="%.2f")

    st.header("3. Detallado")
    lista_varillas = list(const.VARILLAS_INFO.keys())
    # Seleccionamos un índice por defecto más común (ej. 5/8" o 3/4")
    index_defecto = lista_varillas.index("3/4") if "3/4" in lista_varillas else 0
    varilla_sel = st.selectbox("Diámetro de Varilla", lista_varillas, index=index_defecto)

# --- LÓGICA DE CONTROL (POO) ---

# 1. Instanciar
viga = VigaRectangular(b_cm, h_cm, fc_input, fy_input)

# 2. Calcular
viga.calcular_as(mu_input)

# 3. Distribuir (Control de errores)
try:
    info_distribucion = viga.distribuir_acero(varilla_sel)
except ValueError as e:
    st.error(f"Error de Datos: {e}")
    st.stop()

# --- INTERFAZ PRINCIPAL (OUTPUTS) ---

col_resultados, col_grafico = st.columns([1, 1.5]) # Ajusté la proporción de columnas

with col_resultados:
    st.subheader("📊 Resultados")
    
    # Métricas grandes
    st.metric("Acero Requerido (As)", f"{viga.area_acero:.2f} mm²")
    
    # Estado con colores
    if "OK" in viga.mensaje or "Dúctil" in viga.mensaje:
        st.success(f"**Estado:** {viga.mensaje}")
    else:
        st.error(f"**Estado:** {viga.mensaje}")
    
    st.markdown("---")
    st.markdown("### 🛠️ Armado Propuesto")
    
    if info_distribucion["exito"]:
        st.info(f"✅ **{info_distribucion['mensaje']}**")
        
        # Tabla de detalles simple
        datos = info_distribucion['resultado']
        st.write(f"**Disposición:** {datos['detalle']}")
        st.write(f"**Cantidad Total:** {datos['cantidad']} varillas")
        st.write(f"**Área Provista:** {datos['area_real']:.1f} mm²")
        
        # Ratio de eficiencia
        ratio = datos['area_real'] / viga.area_acero if viga.area_acero > 0 else 0
        st.progress(min(ratio, 1.0) if ratio < 2 else 1.0)
        st.caption(f"Eficiencia: Cubres el {ratio*100:.1f}% del As requerido")
        
    else:
        st.warning(f"⚠️ **{info_distribucion['mensaje']}**")
        st.write(f"Se requieren {info_distribucion['resultado']['cantidad']} varillas.")
        st.write("Intenta aumentar el diámetro o la sección.")

# --- FUNCIÓN DE DIBUJO ---
def dibujar_seccion(viga_obj, datos_dist):
    # CAMBIO 2: Reducimos figsize de (6,6) a (4,4) para que no se vea gigante
    fig, ax = plt.subplots(figsize=(4, 4))
    
    B = viga_obj.base
    H = viga_obj.altura
    rec = const.RECUBRIMIENTO_VIGA
    
    # Concreto
    concreto = patches.Rectangle((0, 0), B, H, linewidth=2, edgecolor='black', facecolor='#E0E0E0')
    ax.add_patch(concreto)
    
    # Estribo
    w_estribo = B - 2*rec
    h_estribo = H - 2*rec
    estribo = patches.Rectangle((rec, rec), w_estribo, h_estribo, 
                                linewidth=1.5, edgecolor='blue', facecolor='none', linestyle='--')
    ax.add_patch(estribo)
    
    # Varillas
    if datos_dist["exito"] or datos_dist["resultado"]["cantidad"] > 0:
        n_total = datos_dist["resultado"]["cantidad"]
        capas = datos_dist["resultado"]["capas"]
        info_v = const.VARILLAS_INFO[datos_dist["resultado"]["varilla"]]
        db = info_v["diam"]
        
        # Recalcular max_por_capa visualmente si no viene en el dict
        b_util = w_estribo - 2*const.DIAMETRO_ESTRIBO_DEF
        separacion_norma = max(const.SEPARACION_MINIMA_CONCRETO, db)
        ancho_ocupado = db + separacion_norma
        max_por_capa = int((b_util + separacion_norma) / ancho_ocupado)
        
        # Distribución visual simplificada
        vars_c1 = min(n_total, max_por_capa)
        vars_c2 = n_total - vars_c1
        
        # Coordenada Y
        y_c1 = rec + const.DIAMETRO_ESTRIBO_DEF + db/2
        
        # Dibujar Capa 1
        start_x = rec + const.DIAMETRO_ESTRIBO_DEF
        # Centrado visual de las varillas
        espacio_libre = b_util - (vars_c1 * db)
        sep_real = espacio_libre / (vars_c1 - 1) if vars_c1 > 1 else 0
        
        # Si es solo 1 varilla, centrarla
        offset_x = 0
        if vars_c1 == 1:
            offset_x = b_util/2 - db/2
            sep_real = 0

        for i in range(vars_c1):
            x = start_x + offset_x + i*(db + sep_real) 
            circ = patches.Circle((x, y_c1), db/2, facecolor='#D32F2F', edgecolor='black')
            ax.add_patch(circ)
            
        # Dibujar Capa 2
        if vars_c2 > 0:
            y_c2 = y_c1 + db + 25
            espacio_libre_2 = b_util - (vars_c2 * db)
            sep_real_2 = espacio_libre_2 / (vars_c2 - 1) if vars_c2 > 1 else 0
            offset_x_2 = 0
            if vars_c2 == 1:
                offset_x_2 = b_util/2 - db/2
                sep_real_2 = 0

            for i in range(vars_c2):
                x = start_x + offset_x_2 + i*(db + sep_real_2)
                circ = patches.Circle((x, y_c2), db/2, facecolor='#D32F2F', edgecolor='black')
                ax.add_patch(circ)

    # Ajustes finales del gráfico
    ax.set_xlim(-50, B + 50)
    ax.set_ylim(-50, H + 50)
    ax.set_aspect('equal')
    ax.axis('off') # Quita los ejes numéricos para que se vea más limpio ("arquitectónico")
    plt.title(f"Sección: {viga_obj.base/10:.0f}x{viga_obj.altura/10:.0f} cm", fontsize=10)
    plt.tight_layout() # Elimina bordes blancos
    return fig

with col_grafico:
    figura = dibujar_seccion(viga, info_distribucion)
    st.pyplot(figura, use_container_width=False) # False evita que se estire al 100% de la columna