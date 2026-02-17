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

def get_config(key):
    """Obtiene configuración de entorno o st.secrets de forma segura"""
    return os.environ.get(key) or st.secrets.get(key)

# Inicializar Sentry (Manejo de errores silencioso)
sentry_dsn = get_config("SENTRY_DSN")
if sentry_dsn:
    try:
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.5, profiles_sample_rate=0.5)
    except Exception:
        pass

# --- 2. GESTIÓN DE ESTADO (SESSION STATE) ---
if 'producto_actual' not in st.session_state:
    st.session_state.producto_actual = None
if 'busqueda_activa' not in st.session_state:
    st.session_state.busqueda_activa = ""

# --- 3. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_supabase():
    try:
        url = get_config("SUPABASE_URL")
        key = get_config("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        print(f"Error Supabase: {e}")
        return None

supabase = init_supabase()

# --- 4. LÓGICA DE NEGOCIO Y SCRAPING ---

def obtener_hora_mx():
    try:
        return datetime.now(pytz.timezone('America/Mexico_City'))
    except:
        return datetime.now()

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_imagen_externa(sku):
    """Scraping optimizado con Timeouts para no congelar la app"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Intento 1: Partsouq
    try:
        url = f"https://partsouq.com/en/search/all?q={sku}"
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.select('table.table img')
            for i in imgs:
                src = i.get('src', '')
                if src and ('/tesseract/' in src or '/assets/' in src) and 'no-image' not in src:
                    return "https:" + src if src.startswith("//") else ("https://partsouq.com" + src if src.startswith("/") else src)
    except Exception:
        pass

    # Intento 2: Google Images (Fallback)
    try:
        url_g = f"https://www.google.com/search?q=toyota+{sku}&tbm=isch"
        r = requests.get(url_g, headers=headers, timeout=3)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            imgs = soup.find_all('img')
            for img in imgs:
                src = img.get('src')
                if src and src.startswith('http') and 'encrypted-tbn0' in src:
                    return src
    except Exception:
        pass
        
    return None

def traducir_texto(texto):
    """Traduce y maneja errores de red"""
    if not texto or texto == "Sin descripción": return texto
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except:
        return texto

def actualizar_base_datos(sku_real, data_update):
    """Guarda imagen y traducción en BD para futuros usuarios (mejora rendimiento)"""
    if supabase and data_update:
        try:
            supabase.table('catalogo_toyota').update(data_update).eq('item', sku_real).execute()
        except Exception:
            pass

def buscar_producto(sku_usuario):
    if not supabase: return None
    
    sku_limpio = sku_usuario.strip().upper().replace('-', '').replace(' ', '')
    
    try:
        # Búsqueda exacta por columna de búsqueda optimizada
        response = supabase.table('catalogo_toyota').select("*").eq('sku_search', sku_limpio).execute()
        
        # Fallback: búsqueda flexible
        if not response.data:
            response = supabase.table('catalogo_toyota').select("*").ilike('item', f"%{sku_limpio}%").limit(1).execute()
            
        if response.data:
            prod = response.data[0]
            
            # --- LÓGICA DE ENRIQUECIMIENTO DE DATOS ---
            # Si faltan datos (imagen o traducción), los buscamos y guardamos
            updates = {}
            sku_real = prod.get('item')
            
            # 1. Imagen
            if not prod.get('img_url'):
                img = obtener_imagen_externa(sku_real)
                if img:
                    prod['img_url'] = img
                    updates['img_url'] = img
            
            # 2. Traducción (Asumimos que hay un campo 'descripcion_es' en la BD, si no, usa 'descripcion')
            desc_en = prod.get('descripcion', '')
            desc_es = prod.get('descripcion_es') # Campo hipotético nuevo
            
            if not desc_es and desc_en:
                traduccion = traducir_texto(desc_en)
                prod['descripcion_es'] = traduccion # Usamos este para mostrar
                updates['descripcion_es'] = traduccion # Guardaríamos si existiera la columna
            elif not desc_es:
                prod['descripcion_es'] = desc_en # Fallback

            # Guardar cambios en segundo plano si hubo actualizaciones
            if updates:
                actualizar_base_datos(sku_real, updates)
                
            return prod
            
    except Exception as e:
        st.error(f"Error de conexión: {e}")
    
    return None

# --- 5. ESTILOS Y TEMA ---
def inject_css(hora_actual):
    """Inyecta todo el CSS basado en la hora"""
    h = hora_actual.hour
    
    # Definición de temas
    if 6 <= h < 18:
        theme = {
            "bg": "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)", # Gris azulado claro profesional
            "card": "rgba(255, 255, 255, 0.95)",
            "text": "#1a1a1a",
            "accent": "#eb0a1e", # Toyota Red
            "shadow": "0 8px 32px 0 rgba(31, 38, 135, 0.15)"
        }
    else:
        theme = {
            "bg": "linear-gradient(to bottom, #0f2027, #203a43, #2c5364)", # Dark professional
            "card": "rgba(20, 20, 20, 0.9)",
            "text": "#ffffff",
            "accent": "#ff4d4d",
            "shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.5)"
        }

    st.markdown(f"""
        <style>
            /* Reset y Base */
            .stApp {{
                background-image: {theme['bg']};
                background-attachment: fixed;
                background-size: cover;
            }}
            
            /* Contenedor Principal */
            [data-testid="stBlockContainer"] {{
                background-color: {theme['card']};
                border-radius: 20px;
                padding: 2rem;
                box-shadow: {theme['shadow']};
                border: 1px solid rgba(255,255,255,0.1);
            }}
            
            /* Tipografía */
            h1, h2, h3, p, div, label, span {{
                color: {theme['text']} !important;
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }}

            /* Inputs */
            .stTextInput input {{
                font-size: 20px !important;
                font-weight: bold;
                text-align: center;
                color: #000 !important;
                border: 2px solid #ddd;
                border-radius: 10px;
            }}
            .stTextInput input:focus {{
                border-color: {theme['accent']} !important;
                box-shadow: 0 0 0 2px rgba(235, 10, 30, 0.2);
            }}

            /* Botones */
            button[kind="primary"] {{
                background-color: {theme['accent']} !important;
                border: none !important;
                transition: all 0.3s ease;
                font-weight: 800 !important;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            button[kind="primary"]:hover {{
                opacity: 0.9;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(235, 10, 30, 0.4);
            }}
            
            button[kind="secondary"] {{
                border: 2px solid #999 !important;
                color: #555 !important;
            }}

            /* Imagen */
            div[data-testid="stImage"] {{
                background: white;
                border-radius: 15px;
                padding: 10px;
                display: flex;
                justify_content: center;
            }}
            div[data-testid="stImage"] img {{
                max-height: 250px;
                object-fit: contain;
            }}

            /* Precio */
            .price-tag {{
                font-size: clamp(3rem, 5vw, 4rem);
                font-weight: 900;
                color: {theme['accent']};
                text-align: center;
                margin: 10px 0;
                line-height: 1;
            }}

            /* Tarjeta Total */
            .total-card {{
                background: rgba(128,128,128,0.1);
                border-left: 5px solid {theme['accent']};
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }}
            
            /* Ocultar elementos de Streamlit */
            #MainMenu, footer, header {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

# --- 6. INTERFAZ GRÁFICA ---

fecha_actual = obtener_hora_mx()
inject_css(fecha_actual)

# Header
c_logo, c_info = st.columns([1, 3])
with c_info:
    st.markdown(f"""
        <div style="text-align: right; font-size: 0.8rem; opacity: 0.8;">
            <b>TOYOTA LOS FUERTES</b><br>
            {fecha_actual.strftime("%d/%m/%Y %H:%M")}
        </div>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; font-weight: 800; margin-bottom: 30px;'>COTIZADOR DE PARTES</h2>", unsafe_allow_html=True)

# Funciones de Callback para el Formulario
def ejecutar_busqueda():
    st.session_state.busqueda_activa = st.session_state.sku_input

def limpiar_todo():
    st.session_state.sku_input = ""
    st.session_state.busqueda_activa = ""
    st.session_state.producto_actual = None

# Área de Búsqueda
with st.container():
    col_in, col_btn, col_clr = st.columns([3, 1.3, 0.7], gap="small")
    
    with col_in:
        # Vinculamos el input al session_state
        st.text_input("SKU", 
                      placeholder="Ej. 90915-YZZD1", 
                      label_visibility="collapsed", 
                      key="sku_input",
                      on_change=ejecutar_busqueda) # Enter activa la búsqueda
    
    with col_btn:
        st.button("BUSCAR 🔍", 
                  type="primary", 
                  use_container_width=True, 
                  on_click=ejecutar_busqueda)
        
    with col_clr:
        st.button("🗑️", 
                  type="secondary", 
                  use_container_width=True, 
                  on_click=limpiar_todo)

# Área de Resultados
if st.session_state.busqueda_activa:
    with st.spinner("Buscando en catálogo global..."):
        producto = buscar_producto(st.session_state.busqueda_activa)
        
    if producto:
        st.markdown("---")
        
        # Datos del producto
        sku_val = producto.get('item')
        # Preferimos la descripción en español si la generamos, sino la original
        desc = producto.get('descripcion_es', producto.get('descripcion', 'Sin descripción'))
        precio_base = float(producto.get('total_unitario', 0))
        img_url = producto.get('img_url')
        
        # Cálculo IVA
        try:
            precio_final = precio_base * 1.16
        except:
            precio_final = 0.0

        # Layout de Ficha Técnica
        col_img, col_det = st.columns([1, 1.5])
        
        with col_img:
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.markdown("""
                    <div style="background:#eee; height:200px; border-radius:15px; display:flex; align-items:center; justify-content:center; color:#888;">
                        📸 Sin Imagen
                    </div>
                """, unsafe_allow_html=True)
                
        with col_det:
            st.markdown(f"<div style='font-size: 1.2rem; font-weight: bold; color: #eb0a1e;'>{sku_val}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 1.1rem; margin-bottom: 10px;'>{desc}</div>", unsafe_allow_html=True)
            
            if precio_final > 0:
                st.markdown(f"<div class='price-tag'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
                st.caption("Precio Unitario (IVA Incluido)")
            else:
                st.warning("Precio no disponible en catálogo")

        # Calculadora de Cantidad
        if precio_final > 0:
            st.markdown("---")
            c_cant, c_total = st.columns([1, 2])
            with c_cant:
                cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
            
            with c_total:
                total = precio_final * cantidad
                st.markdown(f"""
                <div class="total-card">
                    <span style="font-size:0.9rem; text-transform:uppercase;">Total Neto ({cantidad} pzas)</span><br>
                    <span style="font-size:1.8rem; font-weight:900;">${total:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
                
    else:
        st.error(f"❌ El código '{st.session_state.busqueda_activa}' no se encontró en la base de datos.")

# Footer Legal
st.markdown("---")
st.markdown(f"""
    <div style="font-size: 10px; text-align: justify; opacity: 0.6; line-height: 1.4;">
        <strong>TÉRMINOS Y CONDICIONES:</strong> Precios en MXN incluyen IVA (16%). 
        Válido al {fecha_actual.strftime("%d/%m/%Y %H:%M")}. Las imágenes son ilustrativas (Fuente: Catálogos externos).
        Toyota Los Fuertes no se hace responsable por errores tipográficos.
    </div>
""", unsafe_allow_html=True)
