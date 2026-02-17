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

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

def get_secret(key):
    val = os.environ.get(key)
    if val: return val
    try:
        if key in st.secrets: return st.secrets[key]
    except: pass
    return None

# Inicializar Sentry
sentry_dsn = get_secret("SENTRY_DSN")
if sentry_dsn:
    try:
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0, profiles_sample_rate=1.0)
    except: pass

# --- 2. CONEXIÓN A SUPABASE ---
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

# --- 3. FUNCIONES DE TIEMPO Y ESTADO ---
if 'producto_actual' not in st.session_state:
    st.session_state.producto_actual = None
if 'busqueda_activa' not in st.session_state:
    st.session_state.busqueda_activa = ""
if 'sku_input' not in st.session_state:
    st.session_state.sku_input = ""

def obtener_hora_mx():
    try:
        tz = pytz.timezone('America/Mexico_City')
        return datetime.now(tz)
    except:
        return datetime.now()

fecha_actual = obtener_hora_mx()

# --- 4. ESTILOS CSS ---
def inject_css():
    st.markdown("""
        <style>
            /* Reset básico */
            .stApp {
                background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                background-attachment: fixed;
            }
            
            /* Contenedor Principal estilo Tarjeta */
            div[data-testid="stBlockContainer"] {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                max-width: 700px;
                margin-top: 10px;
            }

            /* Inputs Grandes y Claros */
            .stTextInput input {
                font-size: 22px !important;
                font-weight: 800 !important;
                text-align: center !important;
                color: #000000 !important; /* Texto negro forzoso */
                background-color: #ffffff !important;
                border: 2px solid #eb0a1e !important; /* Borde Rojo Toyota */
                border-radius: 10px;
                padding: 10px !important;
            }

            /* Botones */
            button[kind="primary"] {
                background-color: #eb0a1e !important;
                color: white !important;
                font-weight: bold !important;
                font-size: 18px !important;
                border: none !important;
                border-radius: 8px !important;
                text-transform: uppercase;
                height: 50px;
            }
            button[kind="secondary"] {
                background-color: #f0f0f0 !important;
                color: #333 !important;
                border: 1px solid #ccc !important;
                font-size: 20px !important;
                height: 50px;
            }

            /* Imágenes */
            div[data-testid="stImage"] {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                display: flex;
                justify-content: center;
                border: 1px solid #eee;
            }
            div[data-testid="stImage"] img {
                max-height: 250px;
                object-fit: contain;
            }

            /* Precios */
            .precio-grande {
                color: #eb0a1e;
                font-size: 50px;
                font-weight: 900;
                text-align: center;
                line-height: 1;
                margin: 10px 0;
            }
            
            /* Footer */
            footer {visibility: hidden;}
            .legal-text {
                font-size: 10px;
                color: #666;
                text-align: justify;
                margin-top: 20px;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

inject_css()

# --- 5. LÓGICA DE NEGOCIO (IMAGEN Y TRADUCCIÓN) ---

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_imagen_web(sku):
    """Busca imagen en web solo si no existe en BD"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        # Intento 1: Partsouq
        url = f"https://partsouq.com/en/search/all?q={sku}"
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.select('table.table img')
            for i in imgs:
                src = i.get('src', '')
                if src and ('/tesseract/' in src or '/assets/' in src) and 'no-image' not in src:
                    return "https:" + src if src.startswith("//") else "https://partsouq.com" + src
        
        # Intento 2: Google (Fallback)
        url_g = f"https://www.google.com/search?q=toyota+{sku}&tbm=isch"
        r = requests.get(url_g, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.find_all('img')
            for img in imgs:
                src = img.get('src')
                if src and src.startswith('http') and 'encrypted-tbn0' in src:
                    return src
    except:
        pass
    return None

def traducir_texto(texto):
    try: return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

# --- 6. HEADER CON LOGO (CORREGIDO) ---
col_logo, col_titulo = st.columns([1, 3])

with col_logo:
    # LÓGICA DEL LOGO: Busca el archivo local
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        # Fallback si no hay logo
        st.markdown("<h1 style='text-align: center;'>🔴</h1>", unsafe_allow_html=True)

with col_titulo:
    st.markdown(f"""
        <div style="text-align: right; padding-top: 10px;">
            <h3 style="margin:0; color:black;">TOYOTA LOS FUERTES</h3>
            <span style="font-size: 14px; color: #555;">
                {fecha_actual.strftime("%d/%m/%Y")} - {fecha_actual.strftime("%H:%M")}
            </span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h3 style='text-align: center; font-weight: 800; color: #333;'>COTIZADOR DIGITAL</h3>", unsafe_allow_html=True)

# --- 7. FORMULARIO DE BÚSQUEDA ---
def limpiar_busqueda():
    st.session_state.sku_input = ""
    st.session_state.busqueda_activa = ""

# Contenedor para inputs
c_in, c_go, c_del = st.columns([3, 1.2, 0.6], gap="small")

with c_in:
    sku_val = st.text_input("SKU", key="sku_input", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed")

with c_go:
    if st.button("BUSCAR 🔍", type="primary", use_container_width=True):
        st.session_state.busqueda_activa = sku_val

with c_del:
    st.button("🗑️", type="secondary", use_container_width=True, on_click=limpiar_busqueda)


# --- 8. RESULTADOS ---
if st.session_state.busqueda_activa and supabase:
    sku_search = st.session_state.busqueda_activa.strip().upper()
    sku_clean = sku_search.replace('-', '').replace(' ', '')
    
    with st.spinner("Consultando catálogo..."):
        # 1. Buscar producto
        try:
            # Primero busca exacto en sku_search
            resp = supabase.table('catalogo_toyota').select("*").eq('sku_search', sku_clean).execute()
            if not resp.data:
                # Intenta like
                resp = supabase.table('catalogo_toyota').select("*").ilike('item', f"%{sku_clean}%").limit(1).execute()
            
            datos = resp.data[0] if resp.data else None
        except Exception as e:
            datos = None
            st.error(f"Error de conexión: {e}")

    if datos:
        # Extraer datos básicos
        sku_real = datos.get('item', sku_search)
        desc_raw = datos.get('descripcion', 'Sin descripción')
        precio_base = float(datos.get('total_unitario', 0))
        
        # --- LÓGICA DE IMAGEN (CORREGIDA) ---
        # 1. Intentar obtener img_url directo de Supabase
        url_imagen = datos.get('img_url')

        # 2. Si NO hay imagen en base de datos, buscar en web
        if not url_imagen:
            url_imagen = buscar_imagen_web(sku_real)
            # 3. Si encontramos imagen nueva, guardarla en Supabase para el futuro
            if url_imagen:
                try:
                    supabase.table('catalogo_toyota').update({'img_url': url_imagen}).eq('item', sku_real).execute()
                except: pass
        
        # Traducción
        desc_es = traducir_texto(desc_raw)
        
        # Mostrar Ficha
        c_img, c_data = st.columns([1, 1.5])
        
        with c_img:
            if url_imagen:
                st.image(url_imagen, use_container_width=True)
            else:
                st.info("📷 Sin imagen disponible")

        with c_data:
            st.markdown(f"**SKU:** {sku_real}")
            st.markdown(f"<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>{desc_es}</div>", unsafe_allow_html=True)
            
            try: precio_final = precio_base * 1.16
            except: precio_final = 0.0
            
            if precio_final > 0:
                st.markdown(f"<div class='precio-grande'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
                st.markdown("<div style='text-align: center; font-size: 12px; font-weight: bold;'>Precio Unitario (IVA Incluido)</div>", unsafe_allow_html=True)
            else:
                st.warning("Precio no disponible")

        # Calculadora rápida
        if precio_final > 0:
            st.markdown("---")
            col_qty, col_tot = st.columns([1, 2])
            with col_qty:
                qty = st.number_input("Cantidad", min_value=1, value=1)
            with col_tot:
                total = precio_final * qty
                st.markdown(f"""
                    <div style="background-color: #f8f9fa; border-left: 5px solid #eb0a1e; padding: 10px; border-radius: 5px; text-align: center;">
                        <span style="font-weight: bold;">TOTAL NETO ({qty} Pzas)</span><br>
                        <span style="font-size: 24px; font-weight: 900;">${total:,.2f}</span>
                    </div>
                """, unsafe_allow_html=True)

    else:
        st.error(f"❌ El código {sku_search} no fue encontrado.")

# --- 9. FOOTER ---
st.markdown(f"""
    <div class="legal-text">
        <strong>INFORMACIÓN LEGAL:</strong> Precios válidos al {fecha_actual.strftime("%d/%m/%Y %H:%M")}. 
        Incluye IVA (16%). Las imágenes son referenciales obtenidas de catálogos internacionales.
        Verificar compatibilidad física antes de la compra.
    </div>
""", unsafe_allow_html=True)
