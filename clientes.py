import streamlit as st
import pandas as pd
import os
from datetime import datetime
from deep_translator import GoogleTranslator
import pytz
import sentry_sdk
from supabase import create_client, Client

# --- 1. FUNCIÓN DE SEGURIDAD HÍBRIDA ---
def get_secret(key):
    # 1. Busca en Railway (Variables del sistema)
    val = os.environ.get(key)
    if val:
        return val
    # 2. Busca en Local (secrets.toml)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return None

# --- 2. CONFIGURACIÓN DE SENTRY ---
sentry_dsn = get_secret("SENTRY_DSN")

if sentry_dsn:
    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
    except:
        pass

# Configuración de página
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 3. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_supabase():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    
    if not url or not key:
        return None
        
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    supabase = None

# --- 4. TEMAS VISUALES ---
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
    if 6 <= h < 12: # Mañana
        return {
            "css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)",
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    elif 12 <= h < 19: # Tarde
        return {
            "css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)",
            "card_bg": "rgba(255, 255, 255, 1)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    else: # Noche
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

# --- 5. FUNCIÓN DE BÚSQUEDA ---
def buscar_producto_supabase(sku_usuario):
    if not supabase:
        return None
    
    # Limpiamos el SKU ingresado para quitar guiones y espacios
    sku_clean = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    
    try:
        # AQUÍ ESTÁ EL CAMBIO: Usamos 'catalogo_toyota'
        # IMPORTANTE: Supabase busca en la columna 'sku_clean'
        response = supabase.table('catalogo_toyota') \
            .select("*") \
            .eq('sku_clean', sku_clean) \
            .execute()
            
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        if sentry_dsn: sentry_sdk.capture_exception(e)
        st.error(f"Error consultando DB: {e}")
        return None

# --- 6. INTERFAZ ---
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

# --- 7. RESULTADOS ---
if (busqueda_input or boton_consultar):
    if not supabase:
        st.error("❌ Error: No hay conexión a la base de datos.")
    else:
        with st.spinner('Buscando...'):
            producto = buscar_producto_supabase(busqueda_input)

        if producto:
            # MAPEO DE COLUMNAS 
            # Si en tu Excel la columna del SKU se llama diferente (ej: 'Material'), cambia 'sku' por 'Material'
            sku_val = producto.get('sku', busqueda_input) 
            desc_original = producto.get('descripcion', 'Descripción no disponible')
            precio_base = producto.get('precio', 0)
            
            try:
                desc_es = GoogleTranslator(source='auto', target='es').translate(desc_original)
            except:
                desc_es = desc_original

            try:
                precio_final = float(precio_base) * 1.16 
            except:
                precio_final = 0.0

            st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 20px;'>{sku_val}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
            
            if precio_final > 0:
                st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; font-size: 14px; font-weight: bold; margin-top: 5px;'>Precio por Unidad. Neto (Incluye IVA). Moneda Nacional.</div>", unsafe_allow_html=True)
            else:
                st.warning("Precio no disponible.")
        else:
            st.error("❌ CÓDIGO NO ENCONTRADO")

# --- 8. FOOTER LEGAL ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN COMERCIAL Y MARCO LEGAL</strong><br>
    La información de precios mostrada en este verificador digital cumple estrictamente con las disposiciones legales vigentes en los Estados Unidos Mexicanos:
    <br><br>
    <strong>1. PRECIO TOTAL A PAGAR (LFPC Art. 7 Bis):</strong> En cumplimiento con la Ley Federal de Protección al Consumidor, el precio exhibido representa el monto final e inequívoco a pagar por el consumidor. Este importe incluye el costo del producto, el Impuesto al Valor Agregado (IVA del 16%) y cualquier cargo administrativo aplicable, evitando prácticas comerciales engañosas.
    <br><br>
    <strong>2. VIGENCIA Y EXACTITUD (NOM-174-SCFI-2007):</strong> El precio mostrado es válido exclusivamente al momento de la consulta (Timbre digital: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M:%S")}</strong>). Toyota Los Fuertes garantiza el respeto al precio exhibido al momento de la transacción conforme a lo dispuesto en las Normas Oficiales Mexicanas sobre prácticas comerciales en transacciones electrónicas y de información.
    <br><br>
    <strong>3. INFORMACIÓN COMERCIAL (NOM-050-SCFI-2004):</strong> La descripción y especificaciones de las partes cumplen con los requisitos de información comercial general para productos destinados a consumidores en el territorio nacional.
</div>
""", unsafe_allow_html=True)
