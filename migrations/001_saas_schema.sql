-- ============================================================
-- SaaS Schema: mp.heforge.cl — Compras Ágiles Multi-Tenant
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USUARIOS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name        VARCHAR(255),
    company_name VARCHAR(255),
    rut         VARCHAR(20),
    plan        VARCHAR(20) DEFAULT 'free',   -- free | basic | pro
    is_active   BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================
-- CONFIGURACIÓN POR USUARIO (prompt, filtros, notificaciones)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_configs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    -- Descripción del negocio (input libre para que la IA genere el prompt)
    business_description TEXT,
    -- Prompt del sistema generado/editado por el usuario
    system_prompt       TEXT NOT NULL DEFAULT '',
    -- Filtros de búsqueda
    regions             TEXT[] DEFAULT ARRAY['10','11','9'],
    min_amount_clp      BIGINT DEFAULT 0,
    max_amount_clp      BIGINT,
    min_score           INTEGER DEFAULT 60,
    keywords_include    TEXT[],     -- palabras clave que DEBEN aparecer
    keywords_exclude    TEXT[],     -- palabras clave que descartan la compra
    -- Notificaciones
    telegram_chat_id    VARCHAR(50),
    telegram_enabled    BOOLEAN DEFAULT false,
    email_notifications BOOLEAN DEFAULT true,
    webhook_url         TEXT,
    -- Estado
    is_active           BOOLEAN DEFAULT true,
    last_run_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ITEMS DE MERCADO PÚBLICO (caché compartido entre usuarios)
-- ============================================================
CREATE TABLE IF NOT EXISTS mp_items (
    codigo          VARCHAR(50) PRIMARY KEY,
    nombre          TEXT,
    organismo       TEXT,
    unidad_compra   TEXT,
    region          TEXT,
    monto_clp       BIGINT,
    fecha_cierre    DATE,
    estado          VARCHAR(50) DEFAULT 'publicada',
    url_mp          TEXT,
    raw_data        JSONB,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mp_items_fecha ON mp_items(fecha_cierre);
CREATE INDEX IF NOT EXISTS idx_mp_items_monto ON mp_items(monto_clp);
CREATE INDEX IF NOT EXISTS idx_mp_items_region ON mp_items(region);

-- ============================================================
-- OPORTUNIDADES POR USUARIO (scoring personalizado)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_opportunities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    mp_codigo           VARCHAR(50) REFERENCES mp_items(codigo),
    -- Resultado IA
    score               INTEGER,
    viabilidad          VARCHAR(10),          -- alta | media | baja
    accion              VARCHAR(20),          -- cotizar | investigar | ignorar
    resumen             TEXT,
    justificacion       TEXT,
    riesgo              TEXT,
    precio_sugerido_clp BIGINT,
    -- Seguimiento del usuario
    estado_seguimiento  VARCHAR(30) DEFAULT 'pendiente',  -- pendiente | cotizando | ganado | perdido | ignorado
    notificado_telegram BOOLEAN DEFAULT false,
    notificado_email    BOOLEAN DEFAULT false,
    user_notes          TEXT,
    scored_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, mp_codigo)
);

CREATE INDEX IF NOT EXISTS idx_uo_user_id ON user_opportunities(user_id);
CREATE INDEX IF NOT EXISTS idx_uo_score ON user_opportunities(score DESC);
CREATE INDEX IF NOT EXISTS idx_uo_accion ON user_opportunities(accion);

-- ============================================================
-- LOG DE NOTIFICACIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    opportunity_id  UUID REFERENCES user_opportunities(id),
    channel         VARCHAR(20),   -- telegram | email | webhook
    status          VARCHAR(20),   -- sent | failed
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    error_message   TEXT
);

-- ============================================================
-- LOG DE EJECUCIONES DEL SCRAPER
-- ============================================================
CREATE TABLE IF NOT EXISTS run_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at              TIMESTAMPTZ DEFAULT NOW(),
    finished_at             TIMESTAMPTZ,
    items_fetched           INTEGER DEFAULT 0,
    items_new               INTEGER DEFAULT 0,
    users_processed         INTEGER DEFAULT 0,
    opportunities_created   INTEGER DEFAULT 0,
    status                  VARCHAR(20) DEFAULT 'running',  -- running | completed | failed
    error_msg               TEXT
);

-- ============================================================
-- TOKENS DE REFRESH JWT
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(64) UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rt_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_rt_token ON refresh_tokens(token_hash);

-- ============================================================
-- FUNCIÓN: actualizar updated_at automáticamente
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_configs_updated_at
    BEFORE UPDATE ON user_configs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_mp_items_updated_at
    BEFORE UPDATE ON mp_items
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_opportunities_updated_at
    BEFORE UPDATE ON user_opportunities
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
