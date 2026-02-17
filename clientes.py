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

# --- 1. CONFIGURACIÓN Y SECRETOS ---
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Función robusta para secretos
def get_config(key):
    return os.environ.get(key) or st.secrets.get(key)

# Sentry (Manejo de errores silencioso)
if sentry_dsn := get_config("SENTRY_DSN"):
    try: sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0)
    except: pass

# --- 2. CONEXIÓN SUPABASE (Singleton) ---
@st.cache_resource
def init_supabase():
    try:
        url = get_config("SUPABASE_URL")
        key = get_config("SUPABASE_KEY")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

supabase = init_supabase()

# --- 3. GESTIÓN DE TIEMPO (UX DINÁMICA) ---
def obtener_hora_mx():
    try: return datetime.now(pytz.timezone('America/Mexico_City'))
    except: return datetime.now()

fecha_actual = obtener_hora_mx()

# --- 4. TEMAS VISUALES (DINÁMICOS Y ADAPTATIVOS) ---
def get_theme_by_time(date):
    h = date.hour
    # TEMA DE DÍA (06:00 - 18:59) -> Fondo Claro / Texto Oscuro
    if 6 <= h < 19:
        return {
            "bg_gradient": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)",
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",             # Texto NEGRO
            "accent_color": "#eb0a1e",
            "input_bg": "#ffffff",               # Input BLANCO
            "input_text": "#000000",             # Escribes en NEGRO
            "btn_sec_bg": "#f0f0f0",             # Botón limpiar GRIS CLARO
            "btn_sec_text": "#333333",           # Icono basurero GRIS OSCURO
            "btn_border": "#cccccc"
        }
    # TEMA DE NOCHE (19:00 - 05:59) -> Fondo Oscuro / Texto Claro
    else:
        return {
            "bg_gradient": "linear-gradient(to bottom, #000000 0%, #1a1a1a 100%)",
            "card_bg": "rgba(20, 20, 20, 0.90)", # Tarjeta OSCURA
            "text_color": "#FFFFFF",             # Texto BLANCO
            "accent_color": "#ff4d4d",           # Rojo brillante
            "input_bg": "rgba(255, 255, 255, 0.1)", # Input TRANSPARENTE OSCURO
            "input_text": "#FFFFFF",             # Escribes en BLANCO
            "btn_sec_bg": "rgba(255, 255, 255, 0.1)", # Botón limpiar TRANSPARENTE
            "btn_sec_text": "#FFFFFF",           # Icono basurero BLANCO
            "btn_border": "#555555"
        }

def apply_dynamic_styles():
    theme = get_theme_by_time(fecha_actual)
    
    st.markdown(f"""
        <style>
        :root {{
            --main-text: {theme['text_color']};
            --card-bg: {theme['card_bg']};
            --accent: {theme['accent_color']};
            --input-bg: {theme['input_bg']};
            --input-text: {theme['input_text']};
            --btn-sec-bg: {theme['btn_sec_bg']};
            --btn-sec-text: {theme['btn_sec_text']};
            --btn-border: {theme['btn_border']};
        }}
        
        /* FONDO PRINCIPAL */
        .stApp {{
            background-image: {theme['bg_gradient']};
            background-attachment: fixed;
        }}
        
        /* TARJETA CONTENEDORA */
        [data-testid="stBlockContainer"] {{
            background-color: var(--card-bg);
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            max-width: 700px;
        }}
        
        /* TEXTOS (Se adaptan automáticamente) */
        h1, h2, h3, h4, p, span, div, label {{
            color: var(--main-text) !important;
            font-family: sans-serif;
        }}
        
        /* --- INPUTS (ADAPTABLES) --- */
        .stTextInput input {{
            background-color: var(--input-bg) !important;
            color: var(--input-text) !important;
            caret-color: var(--accent); /* El cursor parpadeante es rojo */
            border: 2px solid var(--accent) !important;
            border-radius: 10px;
            text-align: center;
            font-size: 24px !important;
            font-weight: bold !important;
        }}
        /* Color del placeholder (ej. "90915...") */
        .stTextInput input::placeholder {{
            color: var(--main-text) !important;
            opacity: 0.5;
        }}

        /* --- BOTÓN ROJO (BUSCAR) --- */
        button[kind="primary"] {{
            background-color: var(--accent) !important;
            color: #ffffff !important; /* Siempre blanco en el botón rojo */
            border: none !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            border-radius: 8px !important;
            height: 50px !important;
            transition: 0.2s;
        }}
        button[kind="primary"]:hover {{ opacity: 0.9; }}

        /* --- BOTÓN BASURA (LIMPIAR) --- */
        button[kind="secondary"] {{
            background-color: var(--btn-sec-bg) !important;
            color: var(--btn-sec-text) !important;
            border: 2px solid var(--btn-border) !important; /* Borde un poco más grueso */
            font-size: 26px !important; /* <--- AUMENTAR TAMAÑO PARA EL ÍCONO */
            border-radius: 10px !important;
            height: 55px !important; /* Misma altura que el botón rojo */
            padding-bottom: 5px !important; /* Ajuste para centrar el emoji verticalmente */
            line-height: 1 !important;
        }}
        button[kind="secondary"]:hover {{
            border-color: var(--accent) !important;
            transform: scale(1.05); /* Efecto pop al pasar el mouse */
        }}
        
        /* IMAGEN (Siempre fondo blanco suave para que se vea bien) */
        div[data-testid="stImage"] {{
            background-color: rgba(255,255,255, 0.95);
            border-radius: 10px;
            padding: 10px;
        }}

        /* FOOTER Y EXTRAS */
        #MainMenu, footer, header {{visibility: hidden;}}
        
        .big-price {{
            color: var(--accent);
            font-size: 50px;
            font-weight: 900;
            text-align: center;
            margin-top: 10px;
        }}
        </style>
    """, unsafe_allow_html=True)

apply_dynamic_styles()
# --- 5. LÓGICA OPTIMIZADA (CORE) ---

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_imagen_web(sku):
    """Scraping con Timeouts y selectores optimizados"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    # 1. Partsouq
    try:
        r = requests.get(f"https://partsouq.com/en/search/all?q={sku}", headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for i in soup.select('table.table img'):
                src = i.get('src', '')
                if src and ('/tesseract/' in src or '/assets/' in src) and 'no-image' not in src:
                    return "https:" + src if src.startswith("//") else ("https://partsouq.com" + src if src.startswith("/") else src)
    except: pass
    
    # 2. Google Images (Fallback)
    try:
        r = requests.get(f"https://www.google.com/search?q=toyota+{sku}&tbm=isch", headers=headers, timeout=3)
        if r.status_code == 200:
            for img in BeautifulSoup(r.text, 'html.parser').find_all('img'):
                src = img.get('src')
                if src and src.startswith('http') and 'encrypted-tbn0' in src:
                    return src
    except: pass
    return None

def traducir(texto):
    if not texto: return "Sin descripción"
    try: return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

# --- 6. INTERFAZ (UI) ---

# Header con Logo Local
c1, c2 = st.columns([1, 3])
with c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown(f"<div style='font-size:40px; text-align:center;'>🔴</div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
        <div style="text-align: right; border-bottom: 2px solid var(--accent); padding-bottom: 5px;">
            <strong style="font-size: 1.2rem;">TOYOTA LOS FUERTES</strong><br>
            <span style="font-size: 0.9rem; opacity: 0.8;">{fecha_actual.strftime("%d/%m/%Y - %H:%M")}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Estado de la sesión
if 'sku_search' not in st.session_state: st.session_state.sku_search = ""
if 'data_producto' not in st.session_state: st.session_state.data_producto = None

# Funciones de control
def ejecutar_busqueda():
    st.session_state.sku_search = st.session_state.input_val
    st.session_state.data_producto = None # Reset para nueva búsqueda

def limpiar():
    st.session_state.input_val = ""
    st.session_state.sku_search = ""
    st.session_state.data_producto = None

# Barra de Búsqueda (Input + Botones)
col_in, col_btn, col_cls = st.columns([3, 1.2, 0.6], gap="small")
with col_in:
    st.text_input("Ingrese SKU", key="input_val", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed", on_change=ejecutar_busqueda)
with col_btn:
    st.button("BUSCAR", type="primary", use_container_width=True, on_click=ejecutar_busqueda)
with col_cls:
    st.button("✖", type="secondary", use_container_width=True, on_click=limpiar)

# --- 7. RESULTADOS Y LÓGICA INTELIGENTE ---
if st.session_state.sku_search:
    sku_limpio = st.session_state.sku_search.strip().upper().replace('-', '').replace(' ', '')
    
    if not supabase:
        st.error("Error de conexión con la base de datos.")
    else:
        # Usar spinner para feedback visual
        with st.spinner("🔍 Localizando parte en sistema global..."):
            
            # 1. CONSULTA BD
            try:
                # Intento exacto (Campo optimizado sku_search)
                res = supabase.table('catalogo_toyota').select("*").eq('sku_search', sku_limpio).execute()
                # Intento flexible (LIKE)
                if not res.data:
                    res = supabase.table('catalogo_toyota').select("*").ilike('item', f"%{sku_limpio}%").limit(1).execute()
                
                producto = res.data[0] if res.data else None
            except:
                producto = None

            if producto:
                # 2. ENRIQUECIMIENTO DE DATOS (AUTO-OPTIMIZACIÓN)
                sku_real = producto.get('item')
                needs_update = False
                
                # A. Imagen: Si DB vacía -> Buscar Web -> Guardar en DB
                img_url = producto.get('img_url')
                if not img_url:
                    img_web = buscar_imagen_web(sku_real)
                    if img_web:
                        img_url = img_web
                        # Guardado asíncrono (mejora UX futura)
                        try:
                            supabase.table('catalogo_toyota').update({'img_url': img_web}).eq('item', sku_real).execute()
                        except: pass

                # B. Traducción
                desc_en = producto.get('descripcion', 'Sin descripción')
                desc_es = traducir(desc_en)
                
                # 3. RENDERIZADO DE FICHA (UX)
                st.markdown("---")
                c_img, c_detalles = st.columns([1, 1.3])
                
                with c_img:
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.markdown("""
                            <div style="height:200px; background:#f0f0f0; border-radius:15px; display:flex; align-items:center; justify-content:center; color:#999;">
                                📷 Sin Imagen Digital
                            </div>
                        """, unsafe_allow_html=True)
                
                with c_detalles:
                    st.caption(f"CÓDIGO: {sku_real}")
                    st.markdown(f"<div style='font-size:1.1rem; font-weight:bold; line-height:1.3; margin-bottom:15px;'>{desc_es}</div>", unsafe_allow_html=True)
                    
                    try:
                        precio = float(producto.get('total_unitario', 0)) * 1.16
                    except: precio = 0
                    
                    if precio > 0:
                        st.markdown(f"<div class='big-price'>${precio:,.2f}</div>", unsafe_allow_html=True)
                        st.markdown("<div style='text-align:center; font-size:0.8rem; font-weight:bold; opacity:0.7;'>IVA INCLUIDO</div>", unsafe_allow_html=True)
                    else:
                        st.warning("Precio no disponible por el momento.")

                # 4. CALCULADORA DINÁMICA
                if precio > 0:
                    st.markdown("---")
                    c_qty, c_tot = st.columns([1, 2])
                    with c_qty:
                        qty = st.number_input("Cantidad", min_value=1, value=1, step=1)
                    with c_tot:
                        total = precio * qty
                        st.markdown(f"""
                            <div class="total-card">
                                <span style="font-size:0.8rem; font-weight:bold;">TOTAL NETO ({qty} Pzas)</span><br>
                                <span style="font-size:1.8rem; font-weight:900;">${total:,.2f}</span>
                            </div>
                        """, unsafe_allow_html=True)

            else:
                st.error(f"❌ El código '{st.session_state.sku_search}' no se encuentra en el catálogo actual.")

# --- 8. FOOTER LEGAL (CUMPLIMIENTO PROFECO / LFPC) ---
st.markdown("---")
st.markdown(f"""
    <style>
        .legal-footer {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            color: var(--text-color); /* Se adapta al tema dinámico */
            opacity: 0.8;
            text-align: justify;
            line-height: 1.5;
            padding-top: 20px;
            margin-top: 10px;
        }}
        .legal-footer strong {{
            font-weight: 700;
            text-transform: uppercase;
        }}
    </style>

    <div class="legal-footer">
        <strong>MARCO LEGAL Y PROTECCIÓN AL CONSUMIDOR</strong><br>
        La información presentada en este cotizador digital cumple con las disposiciones de la <strong>Ley Federal de Protección al Consumidor (LFPC)</strong> y las Normas Oficiales Mexicanas vigentes:
        <br><br>
        <strong>1. EXHIBICIÓN DE PRECIOS (Art. 7 Bis LFPC):</strong> El monto exhibido representa el <strong>PRECIO TOTAL A PAGAR</strong>. Incluye costo del producto, Impuesto al Valor Agregado (IVA del 16%) y gastos administrativos. No existen costos ocultos ni cargos adicionales no desglosados al momento de la consulta.
        <br><br>
        <strong>2. VIGENCIA Y EXACTITUD (NOM-174-SCFI-2007):</strong> Debido a la naturaleza dinámica del mercado automotriz, el precio es válido exclusivamente al momento de la emisión de este reporte (<strong>{fecha_actual.strftime("%d/%m/%Y a las %H:%M horas")}</strong>). Toyota Los Fuertes garantiza el respeto al precio mostrado durante la transacción inmediata, salvo error evidente de sistema o agiotaje.
        <br><br>
        <strong>3. INFORMACIÓN COMERCIAL (Art. 32 LFPC):</strong> Las imágenes mostradas tienen fines ilustrativos y de referencia técnica visual; provienen de catálogos globales y pueden diferir ligeramente de la presentación física del producto en inventario. La compatibilidad debe verificarse mediante número de serie (VIN).
    </div>
""", unsafe_allow_html=True)
