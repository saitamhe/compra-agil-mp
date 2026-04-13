FROM python:3.11-slim

# Dependencias del sistema para Playwright + Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright
RUN playwright install chromium && playwright install-deps chromium

# Copiar código fuente
COPY app/ ./app/

# Crear directorios necesarios
RUN mkdir -p data/downloads logs

# Variables de entorno por defecto
ENV APP_ENV=production \
    LOG_LEVEL=INFO \
    DB_PATH=./data/compra_agil.db \
    DOWNLOADS_DIR=./data/downloads \
    LOGS_DIR=./logs \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

# Volúmenes para datos persistentes
VOLUME ["/app/data", "/app/logs"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
