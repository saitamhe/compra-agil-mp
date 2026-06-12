#!/bin/bash
# ============================================================
# Setup SaaS — CompraÁgil mp.heforge.cl
# Ejecutar como root desde /opt/compra-agil-mp
# ============================================================
set -e
cd /opt/compra-agil-mp

echo "=== 1. Copiar docker-compose SaaS ==="
cp docker-compose.saas.yml docker-compose.yml

echo "=== 2. Copiar .env de ejemplo si no existe .env ==="
if [ ! -f .env ]; then
  cp .env.saas.example .env
  echo "⚠️  Edita .env con tus claves reales antes de continuar:"
  echo "   - JWT_SECRET (genera con: python3 -c \"import secrets; print(secrets.token_hex(32))\")"
  echo "   - OPENAI_API_KEY"
  echo "   - TELEGRAM_BOT_TOKEN"
  read -p "Presiona Enter cuando hayas editado .env..."
fi

echo "=== 3. Actualizar requirements.txt ==="
cp requirements.saas.txt requirements.txt

echo "=== 4. Levantar PostgreSQL ==="
docker compose up -d postgres
echo "Esperando que PostgreSQL esté listo..."
sleep 8
docker compose exec postgres pg_isready -U saas_mp -d mp_saas

echo "=== 5. Reconstruir y levantar API ==="
docker compose up -d --build compra-agil

echo "=== 6. Verificar health ==="
sleep 5
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "✅ SaaS desplegado en http://localhost:8000"
echo "   Docs API: http://localhost:8000/docs"
echo "   Frontend: https://mp.heforge.cl"
