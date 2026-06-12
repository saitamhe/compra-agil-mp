-- ============================================================================
--  CompraÁgil SaaS — Esquema Supabase (multi-tenant + Auth Google)
--  Ejecutar en Supabase → SQL Editor.
--  Cada usuario (auth.users) ve SOLO sus datos gracias a Row Level Security.
--  n8n escribe con la service_role key (omite RLS).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1) PERFILES  (1 fila por usuario autenticado)
-- ----------------------------------------------------------------------------
create table if not exists public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  email         text,
  nombre_empresa text,
  created_at    timestamptz default now()
);

-- Crear perfil automáticamente al registrarse con Google
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, nombre_empresa)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name', new.email))
  on conflict (id) do nothing;
  insert into public.user_config (user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ----------------------------------------------------------------------------
-- 2) CONFIGURACIÓN POR USUARIO  (incluye el PROMPT editable desde la web)
-- ----------------------------------------------------------------------------
create table if not exists public.user_config (
  user_id        uuid primary key references public.profiles(id) on delete cascade,
  system_message text default 'Eres un asistente que evalúa compras públicas de Chile para una empresa. Devuelve SIEMPRE JSON puro.',
  que_vende      text,                                 -- lo que escribe el usuario en el onboarding
  rubros         text[]  default array[]::text[],       -- rubros elegidos (chips)
  regiones       text[]  default array[]::text[],       -- nombres de región a vigilar (ej. 'Región Metropolitana')
  monto_min      numeric default 0,
  monto_max      numeric,
  score_minimo   int     default 40,
  modelo         text    default 'gpt-4o-mini',
  activo         boolean default true,
  updated_at     timestamptz default now()
);

-- ----------------------------------------------------------------------------
-- 3) OPORTUNIDADES  (catálogo COMPARTIDO de compras ágiles; n8n lo llena)
-- ----------------------------------------------------------------------------
create table if not exists public.opportunities (
  id                uuid primary key default gen_random_uuid(),
  codigo            text unique not null,
  nombre            text,
  organismo         text,
  unidad_compra     text,
  region            text,
  monto_clp         numeric,
  fecha_publicacion date,
  fecha_cierre      date,
  url_mp            text,
  raw               jsonb,
  created_at        timestamptz default now()
);
create index if not exists ix_opp_codigo on public.opportunities(codigo);

-- ----------------------------------------------------------------------------
-- 4) SCORING + SEGUIMIENTO POR USUARIO
-- ----------------------------------------------------------------------------
create table if not exists public.user_opportunities (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references public.profiles(id) on delete cascade,
  opportunity_id      uuid not null references public.opportunities(id) on delete cascade,
  codigo              text,                          -- = opportunities.codigo (lo usa la web como clave)
  score               int,
  viabilidad          text,                          -- alta | media | baja
  accion              text,                          -- cotizar | investigar | ignorar
  resumen             text,
  justificacion       text,
  riesgo              text,
  precio_sugerido_clp numeric,
  estado_seguimiento  text,                          -- NULL = no está en el tablero; luego pendiente|cotizando|enviada|ganada|perdida
  monto_ganado        numeric,                       -- se llena al marcar "ganada"
  fecha_resultado     timestamptz,                   -- cuándo se marcó ganada/perdida
  created_at          timestamptz default now(),
  updated_at          timestamptz default now(),
  unique (user_id, opportunity_id)
);
create index if not exists ix_uo_user on public.user_opportunities(user_id);
create index if not exists ix_uo_codigo on public.user_opportunities(codigo);

-- ----------------------------------------------------------------------------
-- 5) COTIZACIONES  (calculadora de IVA; cálculo en la propia BD)
--    IVA Chile = 19 %. La ganancia neta NO incluye IVA (es pasa-a-través).
-- ----------------------------------------------------------------------------
create table if not exists public.quotes (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  opportunity_id     uuid references public.opportunities(id) on delete set null,
  codigo             text,                            -- = opportunities.codigo (clave que usa la web)
  descripcion        text,
  costo_neto         numeric not null default 0,     -- lo que TÚ pagas al proveedor (sin IVA)
  precio_venta_neto  numeric not null default 0,     -- lo que cobras al Estado (sin IVA)
  iva_pct            numeric not null default 19,

  -- columnas calculadas automáticamente
  iva_credito  numeric generated always as (round(costo_neto * iva_pct / 100))        stored, -- IVA que pagas en la compra
  iva_debito   numeric generated always as (round(precio_venta_neto * iva_pct / 100)) stored, -- IVA que cobras en la venta
  iva_a_pagar  numeric generated always as (
                 round(precio_venta_neto * iva_pct / 100) - round(costo_neto * iva_pct / 100)
               ) stored,                                                                       -- lo que enteras al SII
  costo_bruto  numeric generated always as (costo_neto + round(costo_neto * iva_pct / 100))               stored, -- desembolso real
  total_venta  numeric generated always as (precio_venta_neto + round(precio_venta_neto * iva_pct / 100)) stored, -- a facturar
  ganancia_neta numeric generated always as (precio_venta_neto - costo_neto) stored,
  margen_pct   numeric generated always as (
                 case when precio_venta_neto > 0
                   then round((precio_venta_neto - costo_neto) / precio_venta_neto * 100, 2)
                   else 0 end
               ) stored,
  created_at   timestamptz default now()
);
create index if not exists ix_quotes_user on public.quotes(user_id);

-- ----------------------------------------------------------------------------
-- 6) ROW LEVEL SECURITY  (aislamiento entre usuarios)
-- ----------------------------------------------------------------------------
alter table public.profiles           enable row level security;
alter table public.user_config        enable row level security;
alter table public.opportunities      enable row level security;
alter table public.user_opportunities enable row level security;
alter table public.quotes             enable row level security;

-- profiles: cada quien ve/edita su perfil
drop policy if exists "perfil propio" on public.profiles;
create policy "perfil propio" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

-- user_config: cada quien ve/edita su configuración y prompt
drop policy if exists "config propia" on public.user_config;
create policy "config propia" on public.user_config
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- opportunities: cualquier usuario autenticado puede LEER el catálogo;
-- escritura solo vía service_role (n8n), que omite RLS.
drop policy if exists "leer oportunidades" on public.opportunities;
create policy "leer oportunidades" on public.opportunities
  for select using (auth.role() = 'authenticated');

-- user_opportunities: cada quien ve/edita SOLO las suyas
drop policy if exists "mis oportunidades" on public.user_opportunities;
create policy "mis oportunidades" on public.user_opportunities
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- quotes: cada quien ve/edita SOLO las suyas
drop policy if exists "mis cotizaciones" on public.quotes;
create policy "mis cotizaciones" on public.quotes
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- 7) VISTA DE GANANCIAS  (para el panel "cuánto se gana")
-- ----------------------------------------------------------------------------
create or replace view public.v_ganancias as
select
  uo.user_id,
  count(*)                                                  as total_oportunidades,
  count(*) filter (where uo.estado_seguimiento = 'ganada')  as ganadas,
  count(*) filter (where uo.estado_seguimiento = 'enviada')  as enviadas,
  count(*) filter (where uo.estado_seguimiento = 'perdida')  as perdidas,
  coalesce(sum(uo.monto_ganado) filter (where uo.estado_seguimiento = 'ganada'), 0) as total_ganado_clp,
  round(
    100.0 * count(*) filter (where uo.estado_seguimiento = 'ganada')
    / nullif(count(*) filter (where uo.estado_seguimiento in ('enviada','ganada','perdida')), 0)
  , 1) as tasa_exito_pct
from public.user_opportunities uo
group by uo.user_id;
