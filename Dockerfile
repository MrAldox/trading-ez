# Trading EZ - Dockerfile Optimizado Multi-Etapa para Producción y Render
FROM python:3.13-slim

# Evitar escritura de bytecode y buffers de salida en logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Instalar dependencias de compilación mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo del terminal
COPY config/ ./config/
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Asegurar directorios de persistencia de caché, modelos y base de datos SQLite
RUN mkdir -p data/cache/daily data/cache/intraday data/models data/db

# Exponer el puerto configurado (Render inyecta su propio $PORT en runtime)
EXPOSE 8000

# Comando de arranque del servidor Uvicorn
CMD ["python", "-m", "src.api.main"]
