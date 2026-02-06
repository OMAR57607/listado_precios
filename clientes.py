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

# Inicializar estado de sesión para persistencia (necesario para cambiar cantidad sin perder la búsqueda)
if 'producto_actual' not in st.session_state:
    st.session_state.producto_actual = None
if 'busqueda_actual' not in st.session_state:
    st.session_state.busqueda_actual = ""

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
            max-height: 280px; 
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

# --- 4. ESTILOS MONOLÍTICOS (SIN SEPARAR ARCHIVOS) ---
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
        
        /* INPUT MEJORADO */
        .stTextInput input {{
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            font-weight: 900 !important;
            font-size: 24px !important;
            border: 3px solid var(--accent) !important;
            text-align: center !important;
            border-radius: 10px;
            padding: 10px !important;
        }}
        
        /* PRECIO GRANDE */
        .big-price {{
            color: var(--accent) !important;
            font-size: clamp(40px, 12vw, 80px); 
            font-weight: 900;
            text-align: center;
            line-height: 1.1;
            margin: 10px 0;
            text-shadow: 2px 2px 0px black !important;
        }}

        /* BOTÓN CONSULTAR */
        .stButton button {{
            background-color: var(--accent) !important;
            color: white !important;
            border: 1px solid white;
            font-weight: bold;
            font-size: 18px;
            border-radius: 8px;
            width: 100%;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }}
        .stButton button:hover {{
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        /* SKU */
        .sku-display {{
            font-size: 32px !important;
            font-weight: 900 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* METRICAS (CANTIDAD Y TOTAL) */
        [data-testid="stMetricLabel"] {{
            font-weight: bold;
            font-size: 16px;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 24px;
            color: var(--accent) !important;
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

# --- 5. LÓGICA DE NEGOCIO Y "SELF-HEALING" ---

@st.cache_data(show_spinner=False)
def traducir_texto(texto):
    try: return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_imagen_remota(sku):
    # Intentar PartSouq
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
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
    
    # Fallback Google
    try:
        url_g = f"https://www.google.com/search?q=toyota+{sku}&tbm=isch"
        headers_g = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        r = requests.get(url_g, headers=headers_g, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.find_all('img')
            for img in imgs:
                src = img.get('src')
                if src and src.startswith('http') and 'encrypted-tbn0' in src:
                    return src
    except: pass
    return None

def buscar_producto_optimizado(sku_usuario):
    """
    Usa la nueva columna 'sku_search' para búsqueda ultra-rápida.
    """
    if not supabase: return None
    
    # 1. Limpieza CRÍTICA del input (Normalización)
    sku_limpio = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    
    try:
        # Intento 1: Búsqueda rápida indexada (Requiere haber corrido el SQL)
        response = supabase.table('catalogo_toyota').select("*").eq('sku_search', sku_limpio).execute()
        if response.data: return response.data[0]
        
        # Intento 2: Fallback por si no han corrido el SQL aún (más lento)
        response_legacy = supabase.table('catalogo_toyota').select("*").ilike('item', sku_limpio).execute()
        if response_legacy.data: return response_legacy.data[0]
        
    except Exception as e:
        # Si falla todo, retorno None
        pass
    return None

def actualizar_cache_base_datos(id_producto, nueva_desc=None, nueva_img=None):
    """
    Self-Healing: Intenta guardar los datos enriquecidos en Supabase
    para que la próxima vez sea instantáneo. Falla en silencio si no hay permisos.
    """
    updates = {}
    if nueva_desc: updates['descripcion'] = nueva_desc # O 'desc_es' si creas la columna
    if nueva_img: updates['img_url'] = nueva_img       # Requiere crear columna 'img_url'
    
    if updates:
        try:
            supabase.table('catalogo_toyota').update(updates).eq('id', id_producto).execute()
        except:
            pass # No bloqueamos al usuario si falla el update

# --- 6. INTERFAZ GRÁFICA ---

# Header
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
st.markdown("<h3 style='text-align: center; font-weight: 800;'>COTIZADOR RÁPIDO</h3>", unsafe_allow_html=True)

# FORMULARIO DE BÚSQUEDA (Mejora UX Móvil)
# Usar st.form permite que el teclado del celular envíe el formulario con "Enter/Ir"
with st.form(key='search_form'):
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        busqueda_input = st.text_input("SKU", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed")
    with col_btn:
        submit_btn = st.form_submit_button("🔍")

# LÓGICA DE PERSISTENCIA
# Si se presiona el botón, actualizamos el estado. 
if submit_btn and busqueda_input:
    st.session_state.busqueda_actual = busqueda_input
    # Reseteamos cantidad al buscar nuevo producto
    st.session_state.cantidad_sel = 1 

# --- 7. PROCESAMIENTO Y RESULTADOS ---
if st.session_state.busqueda_actual:
    busqueda = st.session_state.busqueda_actual
    
    if not supabase:
        st.error("❌ Error de conexión DB.")
    else:
        # Solo mostramos spinner si es una búsqueda nueva (opcional)
        with st.spinner("Consultando..."):
            # Buscar en DB
            producto = buscar_producto_optimizado(busqueda)
            
            if producto:
                # --- Preparación de Datos ---
                sku_val = producto.get('item', busqueda)
                desc_raw = producto.get('descripcion', 'Sin descripción')
                precio_base = float(producto.get('total_unitario', 0))
                
                # Gestión Inteligente de Imagen y Texto
                # 1. Imagen: Si ya la tuviéramos en DB la usamos, si no, scraping
                url_imagen = producto.get('img_url') # Requiere columna nueva
                if not url_imagen:
                    url_imagen = obtener_imagen_remota(sku_val)
                
                # 2. Traducción
                # Si detectamos que la descripción está en inglés (heurística simple), traducimos
                if "ASSY" in desc_raw or "GASKET" in desc_raw:
                    desc_es = traducir_texto(desc_raw)
                else:
                    desc_es = desc_raw
                
                # Intentamos guardar lo que encontramos (Self-Healing)
                # actualizar_cache_base_datos(producto['id'], nueva_desc=desc_es, nueva_img=url_imagen)
                
                try: final_unitario = precio_base * 1.16
                except: final_unitario = 0.0

                # --- VISUALIZACIÓN ---
                
                # 1. Imagen
                if url_imagen:
                    st.image(url_imagen, caption="Referencia Visual", use_container_width=True)
                else:
                    st.info("📷 Sin imagen disponible.")

                # 2. Datos Principales
                st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 10px;'>{sku_val}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 15px;'>{desc_es}</div>", unsafe_allow_html=True)
                
                # 3. PRECIO UNITARIO
                if final_unitario > 0:
                    st.markdown(f"<div class='big-price'>${final_unitario:,.2f}</div>", unsafe_allow_html=True)
                    st.markdown("<div style='text-align: center; font-size: 12px; margin-bottom: 20px;'>Precio Unitario (IVA Incluido)</div>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 4. NUEVO: CALCULADORA DE CANTIDAD
                    # Usamos columnas para que se vea ordenado
                    c1, c2 = st.columns(2)
                    with c1:
                        cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1, key="cantidad_input")
                    with c2:
                        total_calculado = final_unitario * cantidad
                        st.metric("Total a Pagar", f"${total_calculado:,.2f}")
                        
                else:
                    st.warning("Precio no disponible en sistema.")
                    
            else:
                st.error(f"❌ '{busqueda}' NO ENCONTRADO")
                st.markdown("Verifica que el código sea correcto.")

# --- 8. FOOTER LEGAL ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN COMERCIAL</strong><br>
    Precios en Moneda Nacional (MXN) incluyen 16% de IVA.
    <br><br>
    <strong>1. PRECIO TOTAL (LFPC Art. 7 Bis):</strong> El monto exhibido es el precio final a pagar por unidad o por el total calculado.
    <br><br>
    <strong>2. VIGENCIA:</strong> Válido al momento de la consulta: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M:%S")}</strong>.
    <br><br>
    <strong>3. IMÁGENES:</strong> Las ilustraciones son referenciales (Catálogos internacionales) y pueden diferir del producto físico.
</div>
""", unsafe_allow_html=True)
