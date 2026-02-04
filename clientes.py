import streamlit as st
import pandas as pd
import os
# import zipfile  <-- Ya no lo necesitamos porque usamos Supabase
from datetime import datetime
# Librería para la traducción automática (NOM-050)
from deep_translator import GoogleTranslator
import pytz
import sentry_sdk
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN DE SECRETOS Y SENTRY (HÍBRIDO) ---
def get_secret(key):
    # Primero busca en Railway (Variables de Entorno)
    val = os.environ.get(key)
    if val: return val
    # Si no, busca en local (.streamlit/secrets.toml)
    try:
        if key in st.secrets: return st.secrets[key]
    except: pass
    return None

sentry_dsn = get_secret("SENTRY_DSN")
if sentry_dsn:
    try:
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0, profiles_sample_rate=1.0)
    except: pass

# Configuración de página
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 2. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_supabase():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    # st.error(f"Error: {e}") # Opcional: comentar para producción
    supabase = None

# --- 3. LÓGICA DE TEMAS VISUALES (TU CÓDIGO ORIGINAL RESTAURADO) ---
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
    
    # 🌅 MAÑANA (6 AM - 12 PM): Amanecer Limpio
    if 6 <= h < 12:
        return {
            "css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)", # Azul muy pálido a blanco
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    
    # ☀️ TARDE (12 PM - 7 PM): Día Soleado (Alto Contraste)
    elif 12 <= h < 19:
        return {
            "css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)", # Azul cielo sólido
            "card_bg": "rgba(255, 255, 255, 1)", # Blanco total
            "text_color": "#000000", # Negro puro
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    
    # 🌌 NOCHE (7 PM - 6 AM): Cielo Estrellado "Natural" (CSS Puro)
    else:
        return {
            # Técnica de Gradientes Radiales para simular estrellas sin imágenes
            "css_bg": """
                radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 4px),
                radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 3px),
                radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 4px),
                linear-gradient(to bottom, #000000 0%, #0c0c0c 100%)
            """,
            "bg_size": "550px 550px, 350px 350px, 250px 250px, 100% 100%", # Capas de estrellas
            "bg_pos": "0 0, 40px 60px, 130px 270px, 0 0", # Posiciones para que se vea natural
            "card_bg": "rgba(0, 0, 0, 0.9)", # Fondo negro casi sólido
            "text_color": "#FFFFFF", # Blanco puro
            "text_shadow": "0px 2px 4px #000000", # Sombra para resaltar
            "accent_color": "#ff4d4d", # Rojo brillante
            "footer_border": "#FFFFFF"
        }

def apply_dynamic_styles():
    now = obtener_hora_mx()
    theme = get_theme_by_time(now)
    
    # Ajustes CSS condicionales para el fondo complejo de noche
    bg_extra_css = ""
    if "bg_size" in theme:
        bg_extra_css = f"background-size: {theme['bg_size']}; background-position: {theme['bg_pos']};"
    
    st.markdown(f"""
        <style>
        /* --- VARIABLES --- */
        :root {{
            --text-color: {theme['text_color']};
            --card-bg: {theme['card_bg']};
            --accent: {theme['accent_color']};
        }}

        /* 1. FONDO DE PANTALLA (Natural) */
        .stApp {{
            background-image: {theme['css_bg']} !important;
            {bg_extra_css}
            background-attachment: fixed;
        }}
        
        /* 2. TARJETA CENTRAL */
        [data-testid="stBlockContainer"] {{
            background-color: var(--card-bg) !important;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            max-width: 700px;
            margin-top: 20px;
            border: 1px solid rgba(128,128,128, 0.3);
        }}

        /* 3. TEXTOS (Alto Contraste Forzado) */
        h1, h2, h3, h4, h5, h6, p, div, span, label, li {{
            color: var(--text-color) !important;
            text-shadow: {theme['text_shadow']} !important;
            font-family: sans-serif;
        }}
        
        /* 4. INPUT (Blanco con letras Negras SIEMPRE) */
        .stTextInput input {{
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            font-weight: 900 !important;
            font-size: 24px !important;
            border: 3px solid var(--accent) !important;
            text-align: center !important;
            border-radius: 10px;
        }}
        
        /* 5. PRECIO */
        .big-price {{
            color: var(--accent) !important;
            font-size: clamp(50px, 15vw, 100px); 
            font-weight: 900;
            text-align: center;
            line-height: 1.1;
            margin: 10px 0;
            text-shadow: 2px 2px 0px black !important;
        }}

        /* 6. BOTÓN */
        .stButton button {{
            background-color: var(--accent) !important;
            color: white !important;
            border: 1px solid white;
            font-weight: bold;
            font-size: 18px;
            border-radius: 8px;
            width: 100%;
        }}
        
        /* 7. TEXTOS GRANDES */
        .sku-display {{
            font-size: 32px !important;
            font-weight: 900 !important;
            text-transform: uppercase;
        }}
        
        /* 8. KIOSCO */
        #MainMenu, footer, header {{visibility: hidden;}}
        
        /* 9. FOOTER LEGAL (Línea divisora adaptable) */
        .legal-footer {{
            border-top: 1px solid {theme['footer_border']} !important;
            opacity: 0.9;
            font-size: 11px;
            margin-top: 40px;
            padding-top: 20px;
            text-align: justify;
        }}
        
        div[data-testid="stImage"] {{ display: block; margin: auto; }}
        </style>
    """, unsafe_allow_html=True)

apply_dynamic_styles()
fecha_actual = obtener_hora_mx()

# --- 4. FUNCIÓN DE BÚSQUEDA EN SUPABASE (LÓGICA ACTUALIZADA) ---
def buscar_producto_supabase(sku_usuario):
    """
    Busca en Supabase usando las columnas: 'item' y 'catalogo_toyota'
    Incluye limpieza de guiones y búsqueda flexible.
    """
    if not supabase:
        return None

    # Limpieza: quitamos guiones y espacios, todo a mayúsculas
    sku_limpio = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    
    try:
        # Intento 1: Búsqueda flexible (ilike) sobre la columna 'item' usando el SKU limpio
        # Esto encuentra "90915YZZD1" incluso si en la DB está así y el usuario pone guiones
        response = supabase.table('catalogo_toyota') \
            .select("*") \
            .ilike('item', sku_limpio) \
            .execute()
            
        if response.data and len(response.data) > 0:
            return response.data[0]
            
        # Intento 2: Por si acaso en tu DB el 'item' SÍ tiene guiones (ej. '90915-YZZD1')
        if '-' in sku_usuario:
             response2 = supabase.table('catalogo_toyota') \
                .select("*") \
                .ilike('item', sku_usuario.strip().upper()) \
                .execute()
             if response2.data and len(response2.data) > 0:
                 return response2.data[0]

        return None
    except Exception as e:
        if sentry_dsn: sentry_sdk.capture_exception(e)
        st.error(f"Error técnico consultando DB: {e}")
        return None


# --- 5. INTERFAZ (RESTO DEL CÓDIGO ORIGINAL) ---
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

# --- 6. BUSCADOR ---
st.markdown("<h3 style='text-align: center; font-weight: 800;'>VERIFICADOR DE PRECIOS</h3>", unsafe_allow_html=True)

busqueda_input = st.text_input("Ingresa SKU:", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed").strip()
boton_consultar = st.button("🔍 CONSULTAR PRECIO")

# --- 7. RESULTADOS ---
if (busqueda_input or boton_consultar):
    if not supabase:
        st.error("❌ Error de conexión: No se pudo conectar a Supabase.")
    else:
        with st.spinner('Consultando sistema...'):
            producto = buscar_producto_supabase(busqueda_input)

        if producto:
            # MAPEO DE COLUMNAS CORRECTO (SEGÚN TU BASE DE DATOS)
            # 'item' = SKU
            # 'descripcion' = Descripción
            # 'total_unitario' = Precio
            
            sku_val = producto.get('item', busqueda_input)
            desc_original = producto.get('descripcion', 'Sin descripción')
            precio_db = producto.get('total_unitario', 0)
            
            # Traducción
            try:
                desc_es = GoogleTranslator(source='auto', target='es').translate(desc_original)
            except:
                desc_es = desc_original

            # Cálculo de IVA (Asumiendo que 'total_unitario' es el precio base)
            # Si en tu DB el precio YA TIENE IVA, elimina el "* 1.16"
            try:
                precio_final = float(precio_db) * 1.16
            except:
                precio_final = 0.0

            # Visualización (Usa tus clases CSS originales)
            st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 20px;'>{sku_val}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
            
            if precio_final > 0:
                st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; font-size: 14px; font-weight: bold; margin-top: 5px;'>Precio por Unidad. Neto (Incluye IVA). Moneda Nacional.</div>", unsafe_allow_html=True)
            else:
                st.warning("Precio no disponible al público.")
                
        else:
            st.error("❌ CÓDIGO NO ENCONTRADO")

# --- 8. FOOTER LEGAL ROBUSTO (TU CÓDIGO ORIGINAL RESTAURADO) ---
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
