# 1. Usamos una versión ligera de Python
FROM python:3.9-slim

# 2. Evita archivos caché y logs innecesarios
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Directorio de trabajo
WORKDIR /app

# 4. Instalar dependencias del sistema (necesarias para compilar algunas libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 5. Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- INICIO DEL HACK (TU LOGO EN LA CARGA) ---
# Copiamos el logo a la carpeta de trabajo
COPY logo.png . 
# Lo movemos al lugar interno de Streamlit para reemplazar el default
RUN cp logo.png /usr/local/lib/python3.9/site-packages/streamlit/static/boot_logo.png

# Modificamos el HTML interno de Streamlit para forzar tu logo en la pantalla de carga
RUN sed -i 's|</head>|<style>#stAppLoading { background-image: url("boot_logo.png"); background-repeat: no-repeat; background-position: center; background-size: 150px; } #stAppLoading > svg { display: none; }</style></head>|' /usr/local/lib/python3.9/site-packages/streamlit/static/index.html
# --- FIN DEL HACK ---

# 6. COPIAR TUS ARCHIVOS
# Copiamos explícitamente solo lo necesario para evitar el error de memoria (4GB)
# Asegúrate de copiar el logo también para que la app lo use en la interfaz, no solo en la carga
COPY logo.png .
COPY clientes.py .

# 7. EJECUTAR LA APP
# IMPORTANTE: Aquí puse "clientes.py" porque es el nombre que salió en tu error anterior.
CMD sh -c "streamlit run clientes.py --server.port=$PORT --server.address=0.0.0.0"
