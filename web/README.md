# OportunIA — Web (frontend)

App web para pymes que venden por **Compra Ágil** de Mercado Público: feed de
oportunidades puntuadas por IA, tablero de seguimiento (Kanban), calculadora de
cotizaciones con IVA y panel de ganancias.

Diseño generado con Claude Design e integrado al backend **Supabase** de este
repo (ver [`../supabase/schema.sql`](../supabase/schema.sql)).

## Cómo funciona

- **Modo DEMO** (por defecto): si `config.js` no tiene una `anon key` real, la app
  corre con datos de ejemplo guardados en el navegador (localStorage). Sirve para
  ver y probar todas las pantallas sin backend.
- **Modo SUPABASE** (real): al pegar tu `anon key` en `config.js`, la app usa
  `@supabase/supabase-js`, login con Google y tus tablas reales. Las reglas RLS
  hacen que cada usuario vea solo lo suyo.

La capa de datos única está en [`db.js`](db.js); cambia de modo sola según
`config.js`. No se usa nunca la `service_role` en el frontend.

## Probar en local

Es un sitio estático (no necesita compilar). Cualquiera de estas opciones:

```bash
# Opción A: servidor estático en el puerto 3000 (ya está en los Redirect URLs de Supabase)
npx serve compra-agil-mp/web -l 3000

# Opción B: con Python
python -m http.server 3000 --directory compra-agil-mp/web
```

Luego abre `http://localhost:3000`. En modo demo también puedes abrir
`index.html` directo con doble clic.

> Para que el **login con Google** funcione en local, el origen
> (`http://localhost:3000`) debe estar en Supabase → Authentication →
> URL Configuration → Redirect URLs.

## Pasar a modo real (Supabase)

1. En [`config.js`](config.js) pega tu `SUPABASE_ANON_KEY` (Project Settings → API).
   La URL ya está puesta (`ugbyawltzcahjjjgnkid.supabase.co`).
2. Asegúrate de haber ejecutado [`../supabase/schema.sql`](../supabase/schema.sql).
3. Sirve la web y entra con Google.

## Desplegar en producción (mp.heforge.cl)

Sube el contenido de esta carpeta `web/` a tu hosting estático (o sirve los
archivos con nginx/Apache). Agrega `https://mp.heforge.cl` a los Redirect URLs de
Supabase. No hay paso de build.

## Mapa de archivos

| Archivo | Qué es |
|---|---|
| `index.html` | Punto de entrada (carga todo) |
| `config.js` | URL + anon key de Supabase / interruptor demo |
| `db.js` | Capa de datos (demo + Supabase) |
| `mock-data.js` | Datos de ejemplo del modo demo |
| `styles.css` | Tokens de diseño (claro/oscuro, foco visible) |
| `ui.jsx` | Componentes accesibles reutilizables |
| `screens-acceso.jsx` | Login + onboarding (aquí se arma el `system_message`) |
| `screens-feed.jsx` | Feed + detalle de oportunidad |
| `screens-seguimiento.jsx` | Tablero Kanban |
| `screens-calculadora.jsx` | Calculadora de IVA |
| `screens-ganancias.jsx` | Panel de ganancias |
| `app.jsx` | Shell, navegación, sesión, tema |
| `tweaks-panel.jsx` | Panel de apariencia/accesibilidad |

## Nota sobre n8n (modo real)

Para que el tablero y el feed se comporten bien con datos reales, el workflow de
n8n (nodo *Guardar Scoring*) debe, al insertar en `user_opportunities`:

- incluir `codigo` (= `opportunities.codigo`), que la web usa como clave; y
- **no** fijar `estado_seguimiento` (dejarlo `NULL`): así la oportunidad aparece
  en el feed pero NO en el tablero hasta que el usuario toca "Hacer seguimiento".
