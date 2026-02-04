import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from deep_translator import GoogleTranslator
import pytz
import sentry_sdk
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN DE SECRETOS Y SENTRY ---
def get_secret(key):
    val = os.environ.get(key)
    if val: return val
    try:
        if key in st.secrets: return st.secrets[key]
    except: pass
    return None

sentry_dsn = get_secret("SENTRY_DSN")
if sentry_dsn:
    try:
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0, profiles_sample_rate=1.0)
    except: pass

st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 1.5 FIX CRÍTICO MÓVILES ---
st.markdown("""
    <script>
        document.documentElement.lang = 'es';
        document.documentElement.setAttribute('translate', 'no');
    </script>
    <style>
        .goog-te-banner-frame { display: none !important; }
        div[data-testid="stImage"] img { 
            border-radius: 10px; 
            max-height: 250px; 
            object-fit: contain; 
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN SUPABASE ---
@st.cache_resource
def init_supabase():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

try:
    supabase = init_supabase()
except:
    supabase = None

# --- 3. TEMAS VISUALES ---
try: tz_cdmx = pytz.timezone('America/Mexico_City')
except: tz_cdmx = None

def obtener_hora_mx():
    return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

def get_theme_by_time(date):
    h = date.hour
    if 6 <= h < 12: 
        return {"css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)", "card_bg": "rgba(255, 255, 255, 0.95)", "text_color": "#000000", "text_shadow": "none", "accent_color": "#eb0a1e", "footer_border": "#000000"}
    elif 12 <= h < 19:
        return {"css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)", "card_bg": "rgba(255, 255, 255, 1)", "text_color": "#000000", "text_shadow": "none", "accent_color": "#eb0a1e", "footer_border": "#000000"}
    else:
        return {"css_bg": "radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 4px), linear-gradient(to bottom, #000000 0%, #0c0c0c 100%)", "bg_size": "550px 550px, 100% 100%", "bg_pos": "0 0, 0 0", "card_bg": "rgba(0, 0, 0, 0.9)", "text_color": "#FFFFFF", "text_shadow": "0px 2px 4px #000000", "accent_color": "#ff4d4d", "footer_border": "#FFFFFF"}

theme = get_theme_by_time(obtener_hora_mx())
st.markdown(f"""
    <style>
    .stApp {{ background-image: {theme['css_bg']} !important; background-attachment: fixed; }}
    [data-testid="stBlockContainer"] {{ background-color: var(--card-bg); border-radius: 15px; padding: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin-top: 20px; }}
    h1, h2, h3, p, div, span {{ color: {theme['text_color']} !important; text-shadow: {theme['text_shadow']}; }}
    .stTextInput input {{ background-color: white !important; color: black !important; font-size: 24px !important; font-weight: 900 !important; text-align: center !important; border: 3px solid {theme['accent_color']} !important; border-radius: 10px; }}
    .big-price {{ color: {theme['accent_color']} !important; font-size: 60px; font-weight: 900; text-align: center; margin: 10px 0; text-shadow: 2px 2px 0px black !important; }}
    .stButton button {{ background-color: {theme['accent_color']} !important; color: white !important; font-weight: bold; font-size: 18px; border-radius: 8px; width: 100%; }}
    .legal-footer {{ border-top: 1px solid {theme['footer_border']}; font-size: 11px; margin-top: 40px; padding-top: 20px; text-align: justify; opacity: 0.9; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES AUXILIARES ---

@st.cache_data(show_spinner=False)
def traducir_texto(texto):
    try: return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

# --- NUEVA FUNCIÓN: SCRAPING DE IMÁGENES ---
@st.cache_data(ttl=3600, show_spinner=False) # Guardamos la imagen 1 hora en caché
def obtener_imagen_remota(sku):
    """
    Busca la imagen del SKU en parts.elmhursttoyota.com
    """
    # 1. URL de búsqueda directa en el sitio
    url_busqueda = f"https://parts.elmhursttoyota.com/search?search_str={sku}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # 2. Hacemos la petición a la web
        response = requests.get(url_busqueda, headers=headers, timeout=3)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 3. Buscamos la etiqueta de imagen. 
            # En RevolutionParts suelen usar 'img' dentro de un link de producto o clase específica.
            # Intentamos encontrar la imagen principal del primer resultado.
            imagen = soup.find("img", {"class": "product-image"}) 
            
            # Si no, intentamos un selector más genérico dentro de resultados
            if not imagen:
                contenedor = soup.find("div", {"class": "product-item"})
                if contenedor:
                    imagen = contenedor.find("img")
            
            if imagen and 'src' in imagen.attrs:
                src = imagen['src']
                # A veces la URL viene relativa (empieza con /), hay que completarla
                if src.startswith("//"):
                    return "https:" + src
                if src.startswith("/"):
                    return "https://parts.elmhursttoyota.com" + src
                return src
    except:
        pass
    
    return None

def buscar_producto_supabase(sku_usuario):
    if not supabase: return None
    sku_limpio = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    try:
        response = supabase.table('catalogo_toyota').select("*").ilike('item', sku_limpio).execute()
        if response.data: return response.data[0]
        if '-' in sku_usuario:
             response2 = supabase.table('catalogo_toyota').select("*").ilike('item', sku_usuario.strip().upper()).execute()
             if response2.data: return response2.data[0]
    except: pass
    return None

# --- 5. INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    else: st.markdown("<h1 style='text-align: center;'>TOYOTA</h1>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div style='text-align: right; font-size: 12px; font-weight: bold;'>LOS FUERTES<br>{obtener_hora_mx().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h3 style='text-align: center; font-weight: 800;'>VERIFICADOR DE PRECIOS</h3>", unsafe_allow_html=True)

busqueda = st.text_input("Ingresa SKU:", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed").strip()
btn = st.button("🔍 CONSULTAR PRECIO")

if busqueda or btn:
    if not supabase:
        st.error("❌ Sin conexión.")
    else:
        with st.spinner('Buscando información...'):
            producto = buscar_producto_supabase(busqueda)
            # Buscamos la imagen en paralelo/segundo plano
            url_imagen = obtener_imagen_remota(busqueda)

        if producto:
            sku_real = producto.get('item', busqueda)
            desc_real = producto.get('descripcion', 'Sin descripción')
            precio_db = producto.get('total_unitario', 0)
            desc_es = traducir_texto(desc_real)
            
            try: precio_final = float(precio_db) * 1.16
            except: precio_final = 0.0
            
            # --- MOSTRAR IMAGEN SI LA ENCONTRAMOS ---
            if url_imagen:
                st.image(url_imagen, caption="Ilustración Referencial (Catálogo USA)", use_container_width=True)
            else:
                st.info("📷 Imagen no disponible en catálogo digital.")

            st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 10px;'>{sku_real}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
            
            if precio_final > 0:
                st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
                st.markdown("<div style='text-align: center; font-size: 14px; font-weight: bold;'>Precio Neto (IVA Incluido). M.N.</div>", unsafe_allow_html=True)
            else:
                st.warning("Precio no disponible.")
        else:
            st.error("❌ CÓDIGO NO ENCONTRADO")

st.markdown("---")
st.markdown("<div class='legal-footer'><strong>INFORMACIÓN OFICIAL</strong><br>Precios en Moneda Nacional incluyen IVA. Las imágenes mostradas son ilustrativas y provienen de catálogos internacionales (Elmhurst Toyota Parts), pueden diferir del producto real.</div>", unsafe_allow_html=True)
