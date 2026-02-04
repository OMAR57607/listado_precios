import streamlit as st
import pandas as pd
from datetime import datetime
from deep_translator import GoogleTranslator
import pytz
import sentry_sdk
import os
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN DE SENTRY (Monitoreo de Errores) ---
# Esto debe ir antes de cualquier otra cosa
if "SENTRY_DSN" in st.secrets:
    sentry_sdk.init(
        dsn=st.secrets["SENTRY_DSN"],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Configuración de página
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 2. CONEXIÓN A SUPABASE ---
# Usamos st.cache_resource para mantener la conexión abierta
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    supabase = None

# --- 3. LÓGICA DE TEMAS VISUALES (Tu código original) ---
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

def get_theme_by_time(date):
    h = date.hour
    # 🌅 MAÑANA (6 AM - 12 PM)
    if 6 <= h < 12:
        return {
            "css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)",
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    # ☀️ TARDE (12 PM - 7 PM)
    elif 12 <= h < 19:
        return {
            "css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)",
            "card_bg": "rgba(255, 255, 255, 1)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    # 🌌 NOCHE (7 PM - 6 AM)
    else:
        return {
            "css_bg": """
                radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 4px),
                radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 3px),
                radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 4px),
                linear-gradient(to bottom, #000000 0%, #0c0c0c 100%)
            """,
            "bg_size": "550px 550px, 350px 350px, 250px 250px, 100% 100%",
            "bg_pos": "0 0, 40px 60px, 130px 270px, 0 0",
            "card_bg": "rgba(0, 0, 0, 0.9)",
            "text_color": "#FFFFFF",
            "text_shadow": "0px 2px 4px #000000",
            "accent_color": "#ff4d4d",
            "footer_border": "#FFFFFF"
        }

def apply_dynamic_styles():
    now = obtener_hora_mx()
    theme = get_theme_by_time(now)
    bg_extra_css = ""
    if "bg_size" in theme:
        bg_extra_css = f"background-size: {theme['bg_size']}; background-position: {theme['bg_pos']};"
    
    st.markdown(f"""
        <style>
        :root {{ --text-color: {theme['text_color']}; --card-bg: {theme['card_bg']}; --accent: {theme['accent_color']}; }}
        .stApp {{ background-image: {theme['css_bg']} !important; {bg_extra_css} background-attachment: fixed; }}
        [data-testid="stBlockContainer"] {{ background-color: var(--card-bg) !important; border-radius: 15px; padding: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); max-width: 700px; margin-top: 20px; border: 1px solid rgba(128,128,128, 0.3); }}
        h1, h2, h3, h4, h5, h6, p, div, span, label, li {{ color: var(--text-color) !important; text-shadow: {theme['text_shadow']} !important; font-family: sans-serif; }}
        .stTextInput input {{ background-color: #ffffff !important; color: #000000 !important; -webkit-text-fill-color: #000000 !important; font-weight: 900 !important; font-size: 24px !important; border: 3px solid var(--accent) !important; text-align: center !important; border-radius: 10px; }}
        .big-price {{ color: var(--accent) !important; font-size: clamp(50px, 15vw, 100px); font-weight: 900; text-align: center; line-height: 1.1; margin: 10px 0; text-shadow: 2px 2px 0px black !important; }}
        .stButton button {{ background-color: var(--accent) !important; color: white !important; border: 1px solid white; font-weight: bold; font-size: 18px; border-radius: 8px; width: 100%; }}
        .sku-display {{ font-size: 32px !important; font-weight: 900 !important; text-transform: uppercase; }}
        #MainMenu, footer, header {{visibility: hidden;}}
        .legal-footer {{ border-top: 1px solid {theme['footer_border']} !important; opacity: 0.9; font-size: 11px; margin-top: 40px; padding-top: 20px; text-align: justify; }}
        div[data-testid="stImage"] {{ display: block; margin: auto; }}
        </style>
    """, unsafe_allow_html=True)

apply_dynamic_styles()
fecha_actual = obtener_hora_mx()

# --- 4. FUNCIÓN DE BÚSQUEDA EN SUPABASE ---
def buscar_producto_supabase(sku_usuario):
    """
    Busca un SKU en Supabase.
    Asume que tienes una tabla llamada 'lista_precios' con columnas:
    - 'sku' (o 'numero_parte')
    - 'descripcion'
    - 'precio'
    """
    if not supabase:
        return None

    # Limpiamos el input del usuario igual que antes
    sku_clean = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    
    try:
        # Hacemos la consulta a Supabase
        # IMPORTANTE: Cambia 'lista_precios' por el nombre real de tu tabla en Supabase
        # Y asegúrate de que la columna donde buscas se llama 'sku_clean' o similar
        response = supabase.table('lista_precios') \
            .select("*") \
            .eq('sku_clean', sku_clean) \
            .execute()
            
        if response.data and len(response.data) > 0:
            return response.data[0] # Retorna el primer resultado
        return None
    except Exception as e:
        st.error(f"Error consultando DB: {e}")
        # Enviamos el error a Sentry silenciosamente
        sentry_sdk.capture_exception(e)
        return None

# --- 5. INTERFAZ ---
col_vacia, col_logo, col_fecha = st.columns([1, 2, 1])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True) 
    else:
        st.markdown("<h1 style='text-align: center;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    st.markdown(f"""
    <div style="text-align: right; font-size: 12px; font-weight: bold;">
        LOS FUERTES<br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h3 style='text-align: center; font-weight: 800;'>VERIFICADOR DE PRECIOS</h3>", unsafe_allow_html=True)

busqueda_input = st.text_input("Ingresa SKU:", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed").strip()
boton_consultar = st.button("🔍 CONSULTAR PRECIO")

# --- 6. LÓGICA DE RESULTADOS ---
if (busqueda_input or boton_consultar):
    with st.spinner('Buscando en la nube...'):
        producto = buscar_producto_supabase(busqueda_input)

    if producto:
        # Mapeo de columnas (AJUSTA ESTOS NOMBRES SEGÚN TU TABLA EN SUPABASE)
        # Si en tu tabla se llaman diferente, cámbialo aquí abajo:
        sku_val = producto.get('sku', busqueda_input) 
        desc_original = producto.get('descripcion', 'Sin descripción')
        precio_base = producto.get('precio', 0)
        
        # Traducción
        try:
            desc_es = GoogleTranslator(source='auto', target='es').translate(desc_original)
        except:
            desc_es = desc_original

        # Cálculo de IVA (Asumiendo que el precio en DB es sin IVA)
        # Si el precio en DB ya tiene IVA, quita la multiplicación * 1.16
        try:
            precio_final = float(precio_base) * 1.16 
        except:
            precio_final = 0.0

        # Mostrar Resultados
        st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 20px;'>{sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; font-size: 14px; font-weight: bold; margin-top: 5px;'>Precio por Unidad. Neto (Incluye IVA). Moneda Nacional.</div>", unsafe_allow_html=True)
        else:
            st.warning("Precio no disponible.")
    
    else:
        st.error("❌ CÓDIGO NO ENCONTRADO O ERROR DE CONEXIÓN")


# --- 7. FOOTER LEGAL ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN COMERCIAL Y MARCO LEGAL</strong><br>
    ... (Mismo footer que tenías) ...
    Timbre digital: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M:%S")}</strong>
</div>
""", unsafe_allow_html=True)
