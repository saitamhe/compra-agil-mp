FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p data/downloads logs

ENV APP_ENV=production \
    LOG_LEVEL=INFO \
    DB_PATH=./data/compra_agil.db \
    DOWNLOADS_DIR=./data/downloads \
    LOGS_DIR=./logs \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

VOLUME ["/app/data", "/app/logs"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
