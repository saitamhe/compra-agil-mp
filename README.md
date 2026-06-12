# CompraÁgil SaaS — mp.heforge.cl

Plataforma SaaS multi-tenant para monitoreo automatizado de **Compras Ágiles de Mercado Público Chile**.  
Cada usuario registra su empresa, genera un prompt personalizado con IA, y recibe recomendaciones automáticas cada 2 horas con scoring por GPT-4o mini.

---

## Arquitectura

```
https://mp.heforge.cl
        │
        ▼ nginx (HestiaCP)
        │
        ▼ Apache :8443 (proxy via apache2.ssl.conf_saas)
        │
        ▼ FastAPI :8000  (Docker: compra-agil-api)
        │
        ├── PostgreSQL :5432 (nativo en VPS, accesible por el container via host network)
        │
        ├── MP API  →  api2.mercadopublico.cl/v2/compra-agil
        │
        └── OpenAI GPT-4o-mini  (scoring + generador de prompts)
                │
                └── Telegram Bot  (notificaciones por usuario)
```

---

## ¿Qué se construyó?

### Backend FastAPI (`/opt/compra-agil-mp/`)

| Archivo | Descripción |
|---|---|
| `app/main.py` | App FastAPI v2.0 con lifespan, CORS, routers |
| `app/config.py` | Configuración vía `.env` (PostgreSQL, OpenAI, JWT, Telegram) |
| `app/database.py` | ORM SQLAlchemy — PostgreSQL multi-tenant |
| `app/auth.py` | JWT access/refresh tokens + bcrypt |
| `app/mp_api.py` | Fetch MP API v2 + pipeline multi-tenant (fetch→score→notify) |
| `app/prompt_ai.py` | GPT-4o-mini: genera system prompts + hace scoring |
| `app/notifications.py` | Envía alertas Telegram por usuario |
| `app/scheduler.py` | APScheduler — ejecuta el pipeline cada 2 horas |
| `app/routers/auth.py` | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| `app/routers/users.py` | `GET/PUT /users/me`, `/users/me/config`, `POST /users/me/generate-prompt` |
| `app/routers/opportunities.py` | Dashboard de oportunidades por usuario |
| `app/routers/admin.py` | Admin endpoints (pipeline, usuarios activos, guardar oportunidades) |
| `app/static/index.html` | Frontend SPA (registro, configuración, dashboard) |

### Base de datos PostgreSQL (`mp_saas`)

| Tabla | Descripción |
|---|---|
| `users` | Usuarios registrados |
| `user_configs` | Prompt, filtros, config Telegram por usuario |
| `mp_items` | Caché de ítems de Mercado Público (compartido) |
| `user_opportunities` | Oportunidades valoradas por usuario |
| `notification_log` | Log de notificaciones enviadas |
| `run_log` | Log de ejecuciones del pipeline |
| `refresh_tokens` | Tokens JWT de refresh |

### Infraestructura

| Archivo | Descripción |
|---|---|
| `docker-compose.yml` | Container `compra-agil-api` con `network_mode: host` |
| `migrations/001_saas_schema.sql` | Schema PostgreSQL completo |
| `/home/heforge/conf/web/mp.heforge.cl/apache2.ssl.conf_saas` | Apache proxy → FastAPI :8000 |
| `n8n_workflow_saas_multitenant.json` | Workflow n8n multi-tenant actualizado |

---

## Endpoints principales

### Públicos
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del sistema |
| `GET` | `/` | Frontend SPA |
| `GET` | `/docs` | Swagger UI |

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/register` | Registrar usuario |
| `POST` | `/auth/login` | Login → JWT |
| `POST` | `/auth/refresh` | Renovar token |
| `POST` | `/auth/logout` | Revocar refresh token |

### Usuario (requiere Bearer token)
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/users/me` | Perfil del usuario |
| `GET/PUT` | `/users/me/config` | Leer/actualizar configuración |
| `POST` | `/users/me/generate-prompt` | **Generar prompt con GPT-4o-mini** |
| `GET` | `/opportunities` | Dashboard de oportunidades |
| `GET` | `/opportunities/stats` | Estadísticas |
| `PATCH` | `/opportunities/{id}` | Actualizar estado de seguimiento |

### Admin (requiere `X-API-Key: mercadopublcio2025`)
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/admin/scrape` | Disparar pipeline inmediato |
| `GET` | `/admin/status` | Estado del scheduler |
| `GET` | `/admin/users/active` | **Usuarios activos con config (para n8n)** |
| `POST` | `/admin/save-opportunity` | **Guardar oportunidad desde n8n** |
| `PATCH` | `/admin/opportunity/{id}/notified` | Marcar como notificado |

---

## Flujo del usuario final

```
1. Entra a https://mp.heforge.cl
2. Se registra con email + contraseña
3. En "Configurar":
   a. Escribe descripción de su empresa
   b. Hace clic en "Generar prompt con IA" (GPT-4o-mini crea el prompt)
   c. Revisa/edita el prompt generado
   d. Configura su Chat ID de Telegram
   e. Guarda
4. Cada 2 horas (automático):
   → Sistema fetches Compras Ágiles de MP
   → Scorea cada ítem con el prompt del usuario
   → Guarda oportunidades con score ≥ min_score
   → Envía alerta por Telegram si está habilitado
5. El usuario ve su dashboard con oportunidades rankeadas
```

---

## Flujo del workflow n8n (multi-tenant)

Ver archivo `n8n_workflow_saas_multitenant.json`. Importar en n8n y configurar:
- Credencial OpenAI (HEFORGE)
- Credencial Telegram (HE FORGE bot)
- El workflow llama a `http://127.0.0.1:8000/admin/users/active` para obtener todos los usuarios activos con sus prompts, y procesa por usuario.

---

## Estado actual del sistema

```
✅ API FastAPI v2.0 corriendo en :8000
✅ PostgreSQL conectado (native, host network)
✅ Schema de BD creado (7 tablas)
✅ https://mp.heforge.cl → sirve el frontend SaaS
✅ Apache proxy → FastAPI configurado
✅ Scheduler activo (cada 2h)
✅ Auth JWT funcionando (register/login/refresh)
✅ Dashboard de oportunidades funcional
```

---

## ⚠️ Pendiente — DEBES completar esto

### 1. Claves secretas en `.env`

```bash
nano /opt/compra-agil-mp/.env
```

Reemplaza estas tres líneas:

```env
# Genera la clave JWT con:
# python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=REEMPLAZAR_CON_CLAVE_ALEATORIA_256BIT

# Tu clave de OpenAI (sk-...)
OPENAI_API_KEY=REEMPLAZAR_CON_TU_KEY_sk-...

# Token del bot de Telegram (del BotFather)
TELEGRAM_BOT_TOKEN=REEMPLAZAR_CON_TOKEN_BOT
```

Después reinicia el container:
```bash
docker restart compra-agil-api
```

### 2. Configurar tu perfil en mp.heforge.cl

1. Ve a https://mp.heforge.cl
2. Inicia sesión con `matias@heforge.cl` / `HEForge2025`
3. Clic en "⚙️ Configurar"
4. Describe tu empresa → "✨ Generar prompt con IA"
5. Configura tu Chat ID de Telegram: `8594675819`
6. Activa "Notificaciones Telegram"
7. Guarda

### 3. Importar workflow n8n multi-tenant

1. Abre n8n en https://n8n.heforge.cl
2. Importa el archivo `n8n_workflow_saas_multitenant.json`
3. Configura las credenciales OpenAI y Telegram
4. Activa el workflow

### 4. Cambiar contraseña del usuario de prueba

```bash
# El usuario matias@heforge.cl fue creado con contraseña temporal "HEForge2025"
# Cámbiala desde la API o el frontend
```

---

## Comandos útiles

```bash
# Ver logs en tiempo real
docker logs compra-agil-api -f

# Estado del sistema
curl http://localhost:8000/health

# Ver usuarios activos con config (para depurar n8n)
curl -H "X-API-Key: mercadopublcio2025" http://localhost:8000/admin/users/active

# Disparar pipeline ahora (sin esperar el cron)
curl -X POST -H "X-API-Key: mercadopublcio2025" http://localhost:8000/admin/scrape

# Reiniciar container
docker restart compra-agil-api

# Ver schema PostgreSQL
PGPASSWORD='SaasMP2025!SecurePass' psql -h 127.0.0.1 -U saas_mp -d mp_saas -c "\dt"

# Contar registros
PGPASSWORD='SaasMP2025!SecurePass' psql -h 127.0.0.1 -U saas_mp -d mp_saas \
  -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM mp_items; SELECT COUNT(*) FROM user_opportunities;"
```

---

## Agregar nuevos usuarios

Los usuarios se registran solos en https://mp.heforge.cl. También puedes crearlos por API:

```bash
curl -X POST https://mp.heforge.cl/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cliente@empresa.cl",
    "password": "Clave2025!",
    "name": "Nombre Cliente",
    "company_name": "Empresa S.A."
  }'
```

---

## Seguridad en producción

- [ ] Cambiar `API_SECRET_KEY` en `.env` (actualmente `mercadopublcio2025`)
- [ ] Cambiar `DB_PASSWORD` en `.env` y en PostgreSQL
- [ ] Revisar CORS en `main.py` (actualmente permite `mp.heforge.cl`)
- [ ] Activar rate limiting en nginx/Apache
- [ ] Configurar backups de PostgreSQL

---

## Tecnologías usadas

- **FastAPI** 0.115 + **Uvicorn** — API REST
- **PostgreSQL** 14 — Base de datos multi-tenant
- **SQLAlchemy** 2.0 — ORM
- **python-jose** — JWT tokens
- **bcrypt** — Hashing de contraseñas
- **OpenAI** `gpt-4o-mini` — Scoring + generación de prompts
- **APScheduler** — Cron en Python
- **Docker** + `network_mode: host` — Despliegue
- **HestiaCP** / **Apache** / **nginx** — Proxy inverso
- **n8n** — Workflow alternativo multi-tenant
