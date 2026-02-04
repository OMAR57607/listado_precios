import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
# Librería para la traducción automática (NOM-050)
from deep_translator import GoogleTranslator
import pytz
import sentry_sdk
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN INICIAL Y FECHA (CRÍTICO: ESTO VA PRIMERO) ---
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

# Definimos la hora inmediatamente para evitar NameError
try: tz_cdmx = pytz.timezone('America/Mexico_City')
except: tz_cdmx = None

def obtener_hora_mx():
    return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

fecha_actual = obtener_hora_mx() # <--- AQUI SE CALCULA ANTES DE USARSE

# --- 2. FIX NUCLEAR PARA MÓVILES ---
st.markdown("""
    <script>
        document.documentElement.lang = 'es';
        document.documentElement.setAttribute('translate', 'no');
        document.body.classList.add('notranslate');
    </script>
    <style>
        .goog-te-banner-frame { display: none !important; }
        .notranslate { transform: translateZ(0); }
        div[data-testid="stImage"] img { 
            border-radius: 12px; 
            max-height: 280px; 
            object-fit: contain; 
            margin: auto;
            display: block;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .sku-display { font-size: 32px !important; font-weight: 900 !important; text-transform: uppercase; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. CONEXIÓN SUPABASE ---
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

# --- 4. TEMAS VISUALES ---
def get_theme_by_time(date):
    h = date.hour
    # 🌅 MAÑANA
    if 6 <= h < 12:
        return {"css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)", "card_bg": "rgba(255, 255, 255, 0.95)", "text_color": "#000000", "text_shadow": "none", "accent_color": "#eb0a1e", "footer_border": "#000000"}
    # ☀️ TARDE
    elif 12 <= h < 19:
        return {"css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)", "card_bg": "rgba(255, 255, 255, 1)", "text_color": "#000000", "text_shadow": "none", "accent_color": "#eb0a1e", "footer_border": "#000000"}
    # 🌌 NOCHE
    else:
        return {"css_bg": "radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 4px), linear-gradient(to bottom, #000000 0%, #0c0c0c 100%)", "bg_size": "550px 550px, 100% 100%", "bg_pos": "0 0, 0 0", "card_bg": "rgba(0, 0, 0, 0.9)", "text_color": "#FFFFFF", "text_shadow": "0px 2px 4px #000000", "accent_color": "#ff4d4d", "footer_border": "#FFFFFF"}

def apply_dynamic_styles():
    theme = get_theme_by_time(fecha_actual)
    bg_extra_css = f"background-size: {theme.get('bg_size', 'auto')}; background-position: {theme.get('bg_pos', 'center')};" if "bg_size" in theme else ""
    
    st.markdown(f"""
        <style>
        :root {{ --text-color: {theme['text_color']}; --card-bg: {theme['card_bg']}; --accent: {theme['accent_color']}; }}
        .stApp {{ background-image: {theme['css_bg']} !important; {bg_extra_css} background-attachment: fixed; }}
        [data-testid="stBlockContainer"] {{ background-color: var(--card-bg); border-radius: 15px; padding: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin-top: 20px; }}
        h1, h2, h3, p, div, span {{ color: {theme['text_color']} !important; text-shadow: {theme['text_shadow']}; }}
        .stTextInput input {{ background-color: white !important; color: black !important; font-size: 24px !important; font-weight: 900 !important; text-align: center !important; border: 3px solid {theme['accent_color']} !important; border-radius: 10px; }}
        .big-price {{ color: {theme['accent_color']} !important; font-size: 60px; font-weight: 900; text-align: center; margin: 10px 0; text-shadow: 2px 2px 0px black !important; }}
        .stButton button {{ background-color: {theme['accent_color']} !important; color: white !important; font-weight: bold; font-size: 18px; border-radius: 8px; width: 100%; }}
        .legal-footer {{ border-top: 1px solid {theme['footer_border']}; font-size: 11px; margin-top: 40px; padding-top: 20px; text-align: justify; opacity: 0.9; }}
        </style>
    """, unsafe_allow_html=True)

apply_dynamic_styles()

# --- 5. FUNCIONES AUXILIARES ---

@st.cache_data(show_spinner=False)
def traducir_texto(texto):
    try: return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

@st.cache_data(ttl=3600, show_spinner=False) 
def obtener_imagen_remota(sku):
    """ MOTOR HÍBRIDO: Busca en Elmhurst y luego en PartSouq """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9"
    }
    
    # 1. ELMHURST
    try:
        url1 = f"https://parts.elmhursttoyota.com/search?search_str={sku}"
        r = requests.get(url1, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            img = soup.find("img", {"class": "product-image"})
            if not img: img = soup.select_one('.product-item img')
            if img:
                src = img.get('data-src') or img.get('src')
                if src and ('jpg' in src or 'png' in src) and 'logo' not in src:
                    if src.startswith("//"): return "https:" + src
                    if src.startswith("/"): return "https://parts.elmhursttoyota.com" + src
                    return src
    except: pass
    
    # 2. PARTSOUQ
    try:
        url2 = f"https://partsouq.com/es/search/all?q={sku}"
        r = requests.get(url2, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.select('table.table img')
            for i in imgs:
                src = i.get('src', '')
                if src and ('/tesseract/' in src or '/assets/' in src) and 'no-image' not in src:
                    if src.startswith("//"): return "https:" + src
                    if src.startswith("/"): return "https://partsouq.com" + src
                    return src
    except: pass
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

# --- 6. INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # FECHA ARRIBA DEL LOGO
    st.markdown(f"""
    <div style="text-align: center; font-size: 14px; font-weight: bold; margin-bottom: 5px;">
        LOS FUERTES<br>
        {fecha_actual.strftime("%d/%m/%Y")} - {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)
    
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True) 
    else:
        st.markdown("<h1 style='text-align: center;'>TOYOTA</h1>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h3 style='text-align: center; font-weight: 800;'>VERIFICADOR DE PRECIOS</h3>", unsafe_allow_html=True)

busqueda = st.text_input("Ingresa SKU:", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed").strip()
btn = st.button("🔍 CONSULTAR PRECIO")

# --- 7. LÓGICA DE RESULTADOS ---
if busqueda or btn:
    if not supabase:
        st.error("❌ Sin conexión.")
    else:
        aviso = st.empty()
        aviso.info("⏳ Consultando bases de datos...")
        
        producto = buscar_producto_supabase(busqueda)
        url_imagen = obtener_imagen_remota(busqueda)
        
        aviso.empty()

        if producto:
            sku_val = producto.get('item', busqueda)
            desc = producto.get('descripcion', 'Sin descripción')
            precio = producto.get('total_unitario', 0)
            desc_es = traducir_texto(desc)
            
            try: final = float(precio) * 1.16
            except: final = 0.0
            
            # IMAGEN
            if url_imagen:
                st.image(url_imagen, caption="Ilustración Referencial", use_container_width=True)
            else:
                st.info("📷 Imagen no disponible digitalmente.")

            # DATOS
            st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 10px;'>{sku_val}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
            
            if final > 0:
                st.markdown(f"<div class='big-price'>${final:,.2f}</div>", unsafe_allow_html=True)
                st.markdown("<div style='text-align: center; font-size: 14px; font-weight: bold;'>Precio Neto (IVA Incluido). M.N.</div>", unsafe_allow_html=True)
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
    <strong>3. INFORMACIÓN COMERCIAL (NOM-050-SCFI-2004):</strong> La descripción y especificaciones de las partes cumplen con los requisitos de información comercial general para productos destinados a consumidores en el territorio nacional. Las imágenes mostradas son ilustrativas y provienen de catálogos internacionales (PartSouq / Elmhurst), pueden diferir del producto real.
</div>
""", unsafe_allow_html=True)
