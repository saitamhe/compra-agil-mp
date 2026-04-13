#!/usr/bin/env bash
# =============================================================================
# Script de instalación para VPS (Ubuntu/Debian)
# Ejecutar como root: bash deploy/install.sh
# =============================================================================
set -euo pipefail

APP_DIR="/opt/compra-agil-mp"
APP_USER="compra-agil"
REPO_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Instalando CompraÁgil API en $APP_DIR ==="

# 1. Crear usuario del sistema (sin shell de login)
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
    echo "✓ Usuario '$APP_USER' creado"
fi

# 2. Instalar dependencias del sistema
apt-get update -qq
apt-get install -y -qq \
    python3.11 python3.11-venv python3.11-dev \
    build-essential curl wget git nginx \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxdamage1 libxkbcommon0 libgbm1 \
    libpangocairo-1.0-0 libgtk-3-0 libxss1 \
    fonts-liberation libasound2
echo "✓ Dependencias del sistema instaladas"

# 3. Copiar código fuente
if [ -d "$APP_DIR" ]; then
    echo "Directorio existente, actualizando..."
    rsync -av --exclude='.git' --exclude='data/' --exclude='logs/' \
        "$REPO_SRC/" "$APP_DIR/"
else
    cp -r "$REPO_SRC" "$APP_DIR"
fi

# 4. Crear estructura de directorios
mkdir -p "$APP_DIR"/{data/downloads,logs}
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 750 "$APP_DIR"

# 5. Crear entorno virtual Python
python3.11 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q
echo "✓ Virtualenv y dependencias Python instaladas"

# 6. Instalar Playwright (navegador Chromium)
"$APP_DIR/.venv/bin/playwright" install chromium
"$APP_DIR/.venv/bin/playwright" install-deps chromium
echo "✓ Playwright/Chromium instalado"

# 7. Crear .env si no existe
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    # Generar API key aleatoria
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/CHANGE_ME_IN_PRODUCTION/$SECRET/" "$APP_DIR/.env"
    echo "✓ Archivo .env creado — EDITA $APP_DIR/.env con tus valores"
else
    echo "✓ .env existente, no se sobrescribe"
fi

# 8. Instalar servicio systemd
cp "$APP_DIR/deploy/compra-agil.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable compra-agil
systemctl restart compra-agil
echo "✓ Servicio systemd instalado y arrancado"

# 9. Nginx
if [ -f "$APP_DIR/deploy/nginx.conf" ]; then
    cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/compra-agil
    ln -sf /etc/nginx/sites-available/compra-agil /etc/nginx/sites-enabled/compra-agil
    nginx -t && systemctl reload nginx
    echo "✓ Nginx configurado"
fi

echo ""
echo "============================================================"
echo "  Instalación completada."
echo "  API disponible en: http://$(curl -s ifconfig.me):8000"
echo "  Docs:              http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "  Próximos pasos:"
echo "  1. Edita $APP_DIR/.env (especialmente API_SECRET_KEY)"
echo "  2. En deploy/nginx.conf cambia 'tu-dominio.com'"
echo "  3. Para HTTPS: certbot --nginx -d tu-dominio.com"
echo "  4. Ver logs: journalctl -u compra-agil -f"
echo "============================================================"
