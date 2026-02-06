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

# --- 1. CONFIGURACIÓN INICIAL ---

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

# Inicializar estado de sesión
if 'producto_actual' not in st.session_state:
    st.session_state.producto_actual = None
if 'busqueda_activa' not in st.session_state:
    st.session_state.busqueda_activa = ""
if 'imagen_cache' not in st.session_state:
    st.session_state.imagen_cache = None

try: 
    tz_cdmx = pytz.timezone('America/Mexico_City')
except: 
    tz_cdmx = None

def obtener_hora_mx():
    return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

fecha_actual = obtener_hora_mx()

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
            max-height: 320px; 
            object-fit: contain; 
            margin: auto;
            display: block;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONEXIÓN A SUPABASE ---
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
    if 6 <= h < 12:
        return {
            "css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)",
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000",
            "total_card_bg": "rgba(240, 242, 246, 0.9)" 
        }
    elif 12 <= h < 19:
        return {
            "css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)",
            "card_bg": "rgba(255, 255, 255, 1)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000",
            "total_card_bg": "rgba(240, 242, 246, 0.9)"
        }
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
            "footer_border": "#FFFFFF",
            "total_card_bg": "rgba(255, 255, 255, 0.1)"
        }

def apply_dynamic_styles():
    theme = get_theme_by_time(fecha_actual)
    bg_extra_css = ""
    if "bg_size" in theme:
        bg_extra_css = f"background-size: {theme['bg_size']}; background-position: {theme['bg_pos']};"
    
    st.markdown(f"""
        <style>
        :root {{
            --text-color: {theme['text_color']};
            --card-bg: {theme['card_bg']};
            --accent: {theme['accent_color']};
            --total-bg: {theme['total_card_bg']};
            color-scheme: light; /* Fuerza modo claro en inputs */
        }}
        
        .stApp {{
            background-image: {theme['css_bg']} !important;
            {bg_extra_css}
            background-attachment: fixed;
        }}
        
        [data-testid="stBlockContainer"] {{
            background-color: var(--card-bg) !important;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            max-width: 700px;
            margin-top: 20px;
            border: 1px solid rgba(128,128,128, 0.3);
        }}
        
        h1, h2, h3, h4, h5, h6, p, div, span, label, li {{
            color: var(--text-color) !important;
            text-shadow: {theme['text_shadow']} !important;
            font-family: sans-serif;
        }}
        
        /* INPUT GIGANTE */
        .stTextInput input {{
            background-color: #ffffff !important;
            color: #000000 !important;
            font-weight: 900 !important;
            font-size: 24px !important;
            border: 4px solid var(--accent) !important;
            text-align: center !important;
            border-radius: 12px;
            padding: 12px !important;
        }}
        
        .big-price {{
            color: var(--accent) !important;
            font-size: clamp(40px, 12vw, 80px); 
            font-weight: 900;
            text-align: center;
            line-height: 1.1;
            margin: 10px 0;
            text-shadow: 2px 2px 0px black !important;
        }}
        
        /* --- BOTÓN PRIMARIO (BUSCAR) - ESTILO BLINDADO --- */
        /* Eliminamos apariencia nativa para que iPhone/Android no lo cambien */
        button[kind="primary"] {{
            appearance: none !important;
            -webkit-appearance: none !important;
            background-color: #eb0a1e !important;
            color: #ffffff !important;
            border: 2px solid white !important; /* Borde blanco para resaltar en negro */
            font-weight: 900 !important;
            font-size: 18px !important;
            border-radius: 10px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
            transition: transform 0.1s;
            height: 55px !important; /* Altura fija para alineación */
        }}
        button[kind="primary"]:active {{
            transform: scale(0.96);
            background-color: #cc0000 !important;
        }}
        
        /* --- BOTÓN SECUNDARIO (LIMPIAR) --- */
        button[kind="secondary"] {{
            appearance: none !important;
            -webkit-appearance: none !important;
            background-color: #f0f2f6 !important;
            color: #31333F !important;
            border: 2px solid #ccc !important;
            font-weight: 900 !important;
            font-size: 22px !important;
            border-radius: 10px !important;
            height: 55px !important;
        }}
        button[kind="secondary"]:hover {{
            border-color: #eb0a1e !important;
            color: #eb0a1e !important;
        }}

        /* TARJETA TOTAL */
        .total-card {{
            background-color: var(--total-bg);
            border-left: 6px solid var(--accent);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-top: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .total-label {{
            font-size: 16px;
            font-weight: bold;
            color: var(--text-color) !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
        }}
        .total-value {{
            font-size: 32px;
            font-weight: 900;
            color: var(--text-color) !important;
            margin-top: 5px;
        }}
        
        #MainMenu, footer, header {{visibility: hidden;}}
        .legal-footer {{
            border-top: 1px solid {theme['footer_border']} !important;
            opacity: 0.9;
            font-size: 11px;
            margin-top: 40px;
            padding-top: 20px;
            text-align: justify;
            line-height: 1.4;
        }}
        </style>
    """, unsafe_allow_html=True)


apply_dynamic_styles()

# --- 5. LÓGICA DE NEGOCIO ---

@st.cache_data(show_spinner=False)
def traducir_texto(texto):
    try: return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_imagen_clasica(sku):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    # 1. PARTSOUQ
    try:
        url = f"https://partsouq.com/en/search/all?q={sku}"
        r = requests.get(url, headers=headers, timeout=5)
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
    
    # 2. GOOGLE
    try:
        url_g = f"https://www.google.com/search?q=toyota+{sku}&tbm=isch"
        r = requests.get(url_g, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.find_all('img')
            for img in imgs:
                src = img.get('src')
                if src and src.startswith('http') and 'encrypted-tbn0' in src:
                    return src
    except: pass
    return None

def buscar_producto_smart(sku_usuario):
    if not supabase: return None
    sku_limpio = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    try:
        response = supabase.table('catalogo_toyota').select("*").eq('sku_search', sku_limpio).execute()
        if response.data: return response.data[0]
        response_legacy = supabase.table('catalogo_toyota').select("*").ilike('item', sku_limpio).execute()
        if response_legacy.data: return response_legacy.data[0]
    except: pass
    return None

def guardar_datos_enriquecidos(sku_producto, img_url=None):
    if img_url:
        try:
            supabase.table('catalogo_toyota').update({'img_url': img_url}).eq('item', sku_producto).execute()
        except Exception:
            pass 

# --- 6. INTERFAZ: HEADER ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
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
st.markdown("<h3 style='text-align: center; font-weight: 800;'>COTIZADOR DIGITAL</h3>", unsafe_allow_html=True)

# --- 7. BUSCADOR ADAPTATIVO CON LIMPIEZA ---

# Callback para borrar el texto
def limpiar_busqueda():
    st.session_state.sku_input = ""
    st.session_state.busqueda_activa = ""

with st.form(key='search_form'):
    # Layout responsivo: Input grande, Buscar mediano, Basura pequeño
    c_input, c_search, c_clear = st.columns([3, 1.5, 0.7])
    
    with c_input:
        # Vinculamos el input a session_state con 'key'
        busqueda_input = st.text_input("SKU", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed", key="sku_input")
        
    with c_search:
        # Type="primary" activa el estilo Rojo Toyota definido en CSS
        submit_btn = st.form_submit_button("BUSCAR 🔍", type="primary", use_container_width=True)
        
    with c_clear:
        # Type="secondary" activa el estilo Gris/Blanco. 
        # on_click ejecuta la limpieza.
        clear_btn = st.form_submit_button("🗑️", type="secondary", use_container_width=True, on_click=limpiar_busqueda)

if submit_btn and busqueda_input:
    st.session_state.busqueda_activa = busqueda_input
    st.session_state.imagen_cache = None

# --- 8. RESULTADOS ---
if st.session_state.busqueda_activa:
    busqueda = st.session_state.busqueda_activa
    
    if not supabase:
        st.error("❌ Sin conexión a base de datos.")
    else:
        with st.spinner("Consultando sistema..."):
            producto = buscar_producto_smart(busqueda)
            
            if producto:
                sku_val = producto.get('item', busqueda) 
                desc_raw = producto.get('descripcion', 'Sin descripción')
                precio_base = float(producto.get('total_unitario', 0))
                
                url_imagen = producto.get('img_url') 
                if not url_imagen:
                    if not st.session_state.imagen_cache:
                        url_imagen = obtener_imagen_clasica(sku_val)
                        st.session_state.imagen_cache = url_imagen
                        guardar_datos_enriquecidos(sku_val, url_imagen)
                    else:
                        url_imagen = st.session_state.imagen_cache
                
                if any(x in desc_raw for x in ["ASSY", "GASKET", "PLATE", "SHOCK"]):
                    desc_es = traducir_texto(desc_raw)
                else:
                    desc_es = desc_raw
                
                try: final_unitario = precio_base * 1.16
                except: final_unitario = 0.0

                if url_imagen:
                    st.image(url_imagen, caption="Ilustración Referencial", use_container_width=True)
                else:
                    st.info("📷 Imagen no disponible digitalmente.")

                st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 10px;'>{sku_val}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
                
                if final_unitario > 0:
                    st.markdown(f"<div class='big-price'>${final_unitario:,.2f}</div>", unsafe_allow_html=True)
                    st.markdown("<div style='text-align: center; font-size: 14px; font-weight: bold;'>Precio Unitario (IVA Incluido)</div>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                        cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
                    with c2:
                        total_calculado = final_unitario * cantidad
                        st.markdown(f"""
                        <div class="total-card">
                            <div class="total-label">Total Neto ({int(cantidad)} Pzas)</div>
                            <div class="total-value">${total_calculado:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("Precio no disponible.")
            else:
                st.error("❌ CÓDIGO NO ENCONTRADO")

# --- 9. FOOTER ---
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
    <strong>3. INFORMACIÓN COMERCIAL (NOM-050-SCFI-2004):</strong> La descripción y especificaciones de las partes cumplen con los requisitos de información comercial general para productos destinados a consumidores en el territorio nacional. Las imágenes mostradas son ilustrativas y provienen de catálogos internacionales (PartSouq / Google / eBay), pueden diferir del producto real.
</div>
""", unsafe_allow_html=True)
