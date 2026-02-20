import os
from datetime import datetime

import pandas as pd
import pytz
import requests
import sentry_sdk
import streamlit as st
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from supabase import Client, create_client

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def get_secret(key: str):
    val = os.environ.get(key)
    if val:
        return val
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return None

# Inicializar Sentry (Manejo de errores silencioso)
sentry_dsn = get_secret("SENTRY_DSN")
if sentry_dsn:
    try:
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0)
    except Exception:
        pass

# --- 2. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_supabase():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception:
    supabase = None

# --- 3. ESTADO Y TIEMPO ---
if 'sku_search' not in st.session_state:
    st.session_state.sku_search = ""
if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def obtener_hora_mx() -> datetime:
    try:
        return datetime.now(pytz.timezone('America/Mexico_City'))
    except Exception:
        return datetime.now()

fecha_actual = obtener_hora_mx()

# --- 4. TEMAS VISUALES (DINÁMICOS Y ADAPTATIVOS) ---
def get_theme_by_time(date: datetime) -> dict:
    h = date.hour
    
    # TEMA DE DÍA (06:00 - 18:59) -> Fondo Claro / Texto Oscuro
    if 6 <= h < 19:
        return {
            "bg_gradient": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)",
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",             
            "accent_color": "#eb0a1e",           
            "input_bg": "#ffffff",               
            "input_text": "#000000",             
            "btn_sec_bg": "#f0f0f0",             
            "btn_sec_text": "#333333",           
            "btn_border": "#cccccc",
            "shadow": "0 10px 30px rgba(0,0,0,0.1)"
        }
    # TEMA DE NOCHE (19:00 - 05:59) -> Fondo Oscuro / Texto Claro
    else:
        return {
            "bg_gradient": "linear-gradient(to bottom, #000000 0%, #1a1a1a 100%)",
            "card_bg": "#121212",                
            "text_color": "#FFFFFF",             
            "accent_color": "#ff4d4d",           
            "input_bg": "#1e1e1e",               
            "input_text": "#FFFFFF",             
            "btn_sec_bg": "#2d2d2d",             
            "btn_sec_text": "#FFFFFF",           
            "btn_border": "#444444",
            "shadow": "0 10px 30px rgba(0,0,0,0.8)",
            "scheme": "dark"
        }

def apply_dynamic_styles():
    theme = get_theme_by_time(fecha_actual)
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800;900&display=swap');

        :root {{
            --main-text: {theme['text_color']};
            --card-bg: {theme['card_bg']};
            --accent: {theme['accent_color']};
            --input-bg: {theme['input_bg']};
            --input-text: {theme['input_text']};
            --btn-sec-bg: {theme['btn_sec_bg']};
            --btn-sec-text: {theme['btn_sec_text']};
            --btn-border: {theme['btn_border']};
            --shadow: {theme['shadow']};
        }}
        
        /* TIPOGRAFÍA CORPORATIVA */
        h1, h2, h3, h4, p, span, div, label, input, button {{
            font-family: 'Montserrat', sans-serif !important;
        }}

        /* ANIMACIÓN DE ENTRADA SUAVE */
        @keyframes slideUpFade {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .resultado-container {{
            animation: slideUpFade 0.4s ease-out forwards;
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
            box-shadow: var(--shadow);
            max-width: 700px;
            margin-top: 20px;
        }}
        
        /* TEXTOS */
        h1, h2, h3, h4, p, span, div, label {{
            color: var(--main-text) !important;
        }}
        
        /* --- INPUTS --- */
        .stTextInput input {{
            background-color: var(--input-bg) !important;
            color: var(--input-text) !important;
            caret-color: var(--accent);
            border: 2px solid var(--accent) !important;
            border-radius: 10px;
            text-align: center;
            font-size: 24px !important;
            font-weight: 900 !important;
            padding: 10px;
        }}
        .stTextInput input::placeholder {{
            color: var(--main-text) !important;
            opacity: 0.5;
        }}

        /* --- BOTONES --- */
        button[kind="primary"] {{
            background-color: var(--accent) !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            border-radius: 10px !important;
            height: 55px !important;
            transition: 0.2s;
        }}
        button[kind="primary"]:hover {{ opacity: 0.9; transform: scale(0.99); }}

        button[kind="secondary"] {{
            background-color: var(--btn-sec-bg) !important;
            color: var(--btn-sec-text) !important; 
            border: 1px solid var(--btn-border) !important;
            font-size: 22px !important;
            border-radius: 10px !important;
            height: 55px !important;
        }}
        button[kind="secondary"]:hover {{
            border-color: var(--accent) !important;
            color: var(--accent) !important;
        }}

        /* IMAGEN */
        div[data-testid="stImage"] {{
            background-color: #ffffff;
            border-radius: 15px;
            padding: 15px;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.05);
        }}
        
        /* PRECIO GRANDE */
        .big-price {{
            color: var(--accent);
            font-size: clamp(40px, 5vw, 60px);
            font-weight: 900;
            text-align: center;
            margin-top: 15px;
            line-height: 1;
        }}

        #MainMenu, footer, header {{visibility: hidden;}}
        
        /* FOOTER LEGAL */
        .legal-footer {{
            font-size: 11px;
            opacity: 0.7;
            text-align: justify;
            margin-top: 30px;
            border-top: 1px solid var(--btn-border);
            padding-top: 15px;
        }}
        </style>
    """, unsafe_allow_html=True)

apply_dynamic_styles()

# --- 5. LÓGICA DE NEGOCIO ---

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_imagen_web(sku: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. Toyota OEM Parts Online (Prioridad 1)
    try:
        r = requests.get(f"https://toyota.oempartsonline.com/search?search_str={sku}", headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos la imagen del catálogo
            imagen = soup.find('img', class_='img-responsive') 
            if imagen and imagen.get('src'):
                src = imagen.get('src')
                # Si la ruta es relativa, le agregamos el dominio principal
                if src.startswith('/'):
                    return f"https://toyota.oempartsonline.com{src}"
                return src
    except Exception:
        pass

    # 2. Partsouq (Prioridad 2)
    try:
        r = requests.get(f"https://partsouq.com/en/search/all?q={sku}", headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for i in soup.select('table.table img'):
                src = i.get('src', '')
                if src and ('/tesseract/' in src or '/assets/' in src) and 'no-image' not in src:
                    return "https:" + src if src.startswith("//") else ("https://partsouq.com" + src if src.startswith("/") else src)
    except Exception:
        pass
    
    # 3. Google Fallback (Prioridad 3)
    try:
        r = requests.get(f"https://www.google.com/search?q=toyota+{sku}&tbm=isch", headers=headers, timeout=3)
        if r.status_code == 200:
            for img in BeautifulSoup(r.text, 'html.parser').find_all('img'):
                src = img.get('src')
                if src and src.startswith('http') and 'encrypted-tbn0' in src:
                    return src
    except Exception:
        pass
    
    return None

def traducir(texto: str) -> str:
    if not texto:
        return "Sin descripción"
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except Exception:
        return texto
# --- 6. INTERFAZ GRÁFICA ---

# Header
c1, c2 = st.columns([1.5, 3])

with c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<div style='font-size:60px; text-align:center;'>🔴</div>", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <style>
        .header-title {{
            text-align: right;
            padding-top: 15px;
        }}
        @media (max-width: 768px) {{
            .header-title {{
                text-align: center !important; 
                margin-top: -10px;         
                padding-bottom: 10px;
            }}
        }}
        </style>
        <div class="header-title">
            <strong style="font-size: 2.5rem; text-transform:uppercase; line-height: 1;">VERIFICADOR DIGITAL DE PRECIOS TOYOTA</strong><br>
            <span style="font-size: 1.1rem; opacity: 0.8;">{fecha_actual.strftime("%d/%m/%Y - %H:%M")}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Funciones de control
def ejecutar_busqueda():
    st.session_state.sku_search = st.session_state.input_val

def limpiar():
    st.session_state.input_val = ""
    st.session_state.sku_search = ""

# BARRA DE BÚSQUEDA
col_in, col_btn, col_cls = st.columns([3, 1.2, 0.6], gap="small")

with col_in:
    st.text_input(
        "Ingrese SKU", 
        key="input_val", 
        placeholder="🔍 Ej. 90915-YZZD1", 
        label_visibility="collapsed", 
        on_change=ejecutar_busqueda
    )

with col_btn:
    st.button("🔍 BUSCAR", type="primary", use_container_width=True, on_click=ejecutar_busqueda)

with col_cls:
    st.button("🗑️", type="secondary", use_container_width=True, on_click=limpiar)


# --- 7. RESULTADOS Y ESTADO VACÍO ---
if not st.session_state.sku_search:
    # ESTADO VACÍO (Welcome Screen)
    st.markdown("""
        <div style='text-align: center; opacity: 0.5; margin-top: 50px; margin-bottom: 50px;'>
            <h1 style='font-size: 4rem; margin-bottom: 0;'>🔍</h1>
            <h3>Listo para buscar</h3>
            <p>Ingresa un código de pieza (SKU) para consultar precio e imagen.</p>
        </div>
    """, unsafe_allow_html=True)

elif st.session_state.sku_search:
    sku_limpio = st.session_state.sku_search.strip().upper().replace('-', '').replace(' ', '')
    
    if not supabase:
        st.error("⚠️ Sin conexión a base de datos.")
    else:
        with st.spinner("Buscando en catálogo..."):
            try:
                res = supabase.table('catalogo_toyota').select("*").eq('sku_search', sku_limpio).execute()
                if not res.data:
                    res = supabase.table('catalogo_toyota').select("*").ilike('item', f"%{sku_limpio}%").limit(1).execute()
                
                producto = res.data[0] if res.data else None
            except Exception:
                producto = None

            if producto:
                # Contenedor con animación
                st.markdown("<div class='resultado-container'>", unsafe_allow_html=True)
                
                sku_real = producto.get('item')
                img_url = producto.get('img_url')
                
                if not img_url:
                    img_web = buscar_imagen_web(sku_real)
                    if img_web:
                        img_url = img_web
                        try:
                            supabase.table('catalogo_toyota').update({'img_url': img_web}).eq('item', sku_real).execute()
                            # NOTIFICACIÓN TOAST
                            st.toast("✨ Nueva imagen indexada al catálogo local", icon="🤖")
                        except Exception:
                            pass
                
                desc_en = producto.get('descripcion', 'Sin descripción')
                desc_es = traducir(desc_en)
                
                try: 
                    precio = float(producto.get('total_unitario', 0)) * 1.16
                except Exception: 
                    precio = 0

                st.markdown("---")
                c_img, c_det = st.columns([1, 1.3])
                
                with c_img:
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.markdown("""
                            <div style="height:200px; background:#f0f0f0; border-radius:15px; display:flex; align-items:center; justify-content:center; color:#999;">
                                📷 Imagen no disponible
                            </div>
                        """, unsafe_allow_html=True)
                
                with c_det:
                    st.caption(f"CÓDIGO: {sku_real}")
                    st.markdown(f"<div style='font-size:1.1rem; font-weight:bold; line-height:1.3;'>{desc_es}</div>", unsafe_allow_html=True)
                    
                    if precio > 0:
                        st.markdown(f"<div class='big-price'>${precio:,.2f}</div>", unsafe_allow_html=True)
                        st.markdown("<div style='text-align:center; font-size:0.8rem; font-weight:bold; opacity:0.7;'>IVA INCLUIDO</div>", unsafe_allow_html=True)
                    else:
                        st.warning("Precio no disponible.")

                if precio > 0:
                    st.markdown("---")
                    c_q, c_t = st.columns([1, 2])
                    with c_q:
                        qty = st.number_input("Cantidad", min_value=1, value=1, step=1)
                    with c_t:
                        total = precio * qty
                        st.markdown(f"""
                            <div style="background-color: rgba(128,128,128,0.1); border-left: 5px solid var(--accent); padding: 10px; border-radius: 5px; text-align: center;">
                                <span style="font-weight: bold; font-size: 0.8rem;">TOTAL NETO ({qty} Pzas)</span><br>
                                <span style="font-size: 1.8rem; font-weight: 900;">${total:,.2f}</span>
                            </div>
                        """, unsafe_allow_html=True)
                
                # Cerramos el div de la animación
                st.markdown("</div>", unsafe_allow_html=True)

            else:
                st.error(f"❌ El código '{st.session_state.sku_search}' no se encuentra en el catálogo.")

# --- 8. FOOTER LEGAL ---
st.markdown("---")
st.markdown(f"""
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
