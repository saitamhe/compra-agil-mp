// ============================================================
// PANTALLAS: Feed de Oportunidades y Detalle de Oportunidad
// ============================================================
const { useState: useStateFeed, useEffect: useEffectFeed, useMemo } = React;

const ACCION_INFO = {
  cotizar: { label: "Cotizar", color: "var(--ok)", soft: "var(--ok-soft)" },
  investigar: { label: "Investigar", color: "var(--warn)", soft: "var(--warn-soft)" },
  ignorar: { label: "Ignorar", color: "var(--bad)", soft: "var(--bad-soft)" },
};

const ESTADOS_SEGUIMIENTO = {
  pendiente: "Pendiente",
  cotizando: "Cotizando",
  enviada: "Enviada",
  ganada: "Ganada",
  perdida: "Perdida",
};

function AccionChip({ accion }) {
  const info = ACCION_INFO[accion] || ACCION_INFO.investigar;
  return (
    <span
      className="inline-flex items-center px-3 py-1 rounded-full text-[0.85em] font-bold"
      style={{ color: info.color, background: info.soft }}
    >
      Sugerencia: {info.label}
    </span>
  );
}

function CierreChip({ fecha }) {
  const t = tiempoRestante(fecha);
  return (
    <span
      className="inline-flex items-center gap-1 text-[0.9em] font-semibold"
      style={{ color: t.urgente ? "var(--bad)" : "var(--text-2)" }}
    >
      <span aria-hidden="true">⏱</span> {t.texto}
    </span>
  );
}

// ---------- Tarjeta de oportunidad ----------
function TarjetaOportunidad({ opp, onVer }) {
  const enSeguimiento = opp.ua.estado_seguimiento != null;
  return (
    <Card className="p-5 flex gap-4 items-start hover:border-[var(--border-strong)] transition-colors">
      <ScoreBadge score={opp.ua.score} />
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <h3 className="m-0 text-[1.05em] font-bold leading-snug">{opp.nombre}</h3>
        <p className="m-0 text-[0.95em] text-[var(--text-2)]">
          {opp.organismo} · {opp.region}
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="font-bold text-[1.1em] tabular-nums">{fmtCLP(opp.monto_clp)}</span>
          <CierreChip fecha={opp.fecha_cierre} />
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-1">
          <AccionChip accion={opp.ua.accion} />
          {enSeguimiento && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-[0.85em] font-semibold bg-[var(--primary-soft)] text-[var(--primary)]">
              En seguimiento: {ESTADOS_SEGUIMIENTO[opp.ua.estado_seguimiento]}
            </span>
          )}
        </div>
        <div className="mt-2">
          <Btn variant="secondary" size="sm" onClick={() => onVer(opp.codigo)}>
            Ver detalle →
          </Btn>
        </div>
      </div>
    </Card>
  );
}

// ---------- Feed ----------
function PantallaFeed({ irA }) {
  const [opps, setOpps] = useStateFeed(null); // null = cargando
  const [region, setRegion] = useStateFeed("todas");
  const [score, setScore] = useStateFeed("todos");
  const [monto, setMonto] = useStateFeed("todos");
  const [estado, setEstado] = useStateFeed("todas");
  const [orden, setOrden] = useStateFeed("score");

  useEffectFeed(() => {
    let vivo = true;
    // pequeña pausa para mostrar el estado "buscando"
    (async () => {
      await new Promise((r) => setTimeout(r, 600));
      const data = await DB.getOpportunities();
      if (vivo) setOpps(data);
    })();
    return () => { vivo = false; };
  }, []);

  const abiertas = useMemo(() => (opps || []).filter((o) => !tiempoRestante(o.fecha_cierre).cerrada), [opps]);
  const regionesDisponibles = useMemo(() => [...new Set(abiertas.map((o) => o.region))], [abiertas]);

  const filtradas = useMemo(() => {
    let list = abiertas;
    if (region !== "todas") list = list.filter((o) => o.region === region);
    if (score === "verde") list = list.filter((o) => o.ua.score >= 80);
    if (score === "amarillo") list = list.filter((o) => o.ua.score >= 60 && o.ua.score < 80);
    if (score === "rojo") list = list.filter((o) => o.ua.score < 60);
    if (monto === "chico") list = list.filter((o) => o.monto_clp < 1000000);
    if (monto === "medio") list = list.filter((o) => o.monto_clp >= 1000000 && o.monto_clp <= 3000000);
    if (monto === "grande") list = list.filter((o) => o.monto_clp > 3000000);
    if (estado === "nuevas") list = list.filter((o) => o.ua.estado_seguimiento == null);
    if (estado === "seguimiento") list = list.filter((o) => o.ua.estado_seguimiento != null);
    return [...list].sort((a, b) =>
      orden === "score" ? b.ua.score - a.ua.score : new Date(a.fecha_cierre) - new Date(b.fecha_cierre)
    );
  }, [abiertas, region, score, monto, estado, orden]);

  const hayFiltros = region !== "todas" || score !== "todos" || monto !== "todos" || estado !== "todas";

  const selCls = inputCls + " min-h-[44px] py-0 text-[0.95em]";

  return (
    <div data-screen-label="Feed de oportunidades" className="screen-enter">
      <header className="mb-5">
        <h1 className="m-0 text-[1.5em] font-bold">Oportunidades para ti</h1>
        <p className="m-0 mt-1 text-[var(--text-2)]">
          Compras del Estado que calzan con tu negocio, ordenadas por nota.
        </p>
      </header>

      {/* Filtros */}
      <Card className="p-4 mb-5">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3" role="group" aria-label="Filtros de oportunidades">
          <div className="flex flex-col gap-1">
            <label htmlFor="f-region" className="text-[0.85em] font-semibold text-[var(--text-2)]">Región</label>
            <select id="f-region" className={selCls} value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="todas">Todas</option>
              {regionesDisponibles.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="f-score" className="text-[0.85em] font-semibold text-[var(--text-2)]">Nota</label>
            <select id="f-score" className={selCls} value={score} onChange={(e) => setScore(e.target.value)}>
              <option value="todos">Todas</option>
              <option value="verde">🟢 Buenas (80 o más)</option>
              <option value="amarillo">🟡 Para revisar (60–79)</option>
              <option value="rojo">🔴 No convienen (menos de 60)</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="f-monto" className="text-[0.85em] font-semibold text-[var(--text-2)]">Monto</label>
            <select id="f-monto" className={selCls} value={monto} onChange={(e) => setMonto(e.target.value)}>
              <option value="todos">Todos</option>
              <option value="chico">Hasta $1 millón</option>
              <option value="medio">$1 a $3 millones</option>
              <option value="grande">Más de $3 millones</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="f-estado" className="text-[0.85em] font-semibold text-[var(--text-2)]">Estado</label>
            <select id="f-estado" className={selCls} value={estado} onChange={(e) => setEstado(e.target.value)}>
              <option value="todas">Todas</option>
              <option value="nuevas">Nuevas (sin seguimiento)</option>
              <option value="seguimiento">En seguimiento</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="f-orden" className="text-[0.85em] font-semibold text-[var(--text-2)]">Ordenar por</label>
            <select id="f-orden" className={selCls} value={orden} onChange={(e) => setOrden(e.target.value)}>
              <option value="score">Mejor nota primero</option>
              <option value="cierre">Cierran antes primero</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Resultados */}
      {opps === null ? (
        <div className="flex flex-col items-center gap-3 py-14" role="status" aria-live="polite">
          <div className="text-[2em]" aria-hidden="true">🔎</div>
          <p className="m-0 font-semibold">Buscando compras que calcen con tu negocio…</p>
          <p className="m-0 text-help">El asistente está revisando las últimas publicaciones de Compra Ágil.</p>
        </div>
      ) : filtradas.length === 0 ? (
        <Card>
          <EmptyState
            titulo={hayFiltros ? "Nada con estos filtros" : "Aún no hay oportunidades"}
            texto={
              hayFiltros
                ? "Prueba quitando algún filtro. Por ejemplo, muestra todas las regiones o todas las notas."
                : "Cuando aparezcan compras que calcen con tu negocio, las verás aquí como tarjetas con una nota de 0 a 100."
            }
          >
            {hayFiltros && (
              <Btn variant="secondary" onClick={() => { setRegion("todas"); setScore("todos"); setMonto("todos"); setEstado("todas"); }}>
                Quitar todos los filtros
              </Btn>
            )}
          </EmptyState>
        </Card>
      ) : (
        <div className="flex flex-col gap-4" role="list" aria-label={`${filtradas.length} oportunidades`}>
          <p className="m-0 text-help" aria-live="polite">
            {filtradas.length} {filtradas.length === 1 ? "oportunidad" : "oportunidades"}
          </p>
          {filtradas.map((o) => (
            <div role="listitem" key={o.codigo}>
              <TarjetaOportunidad opp={o} onVer={(codigo) => irA("detalle", { codigo })} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------- Detalle ----------
function PantallaDetalle({ codigo, irA, avisar }) {
  const [opp, setOpp] = useStateFeed(null);
  const [confirmando, setConfirmando] = useStateFeed(false);

  useEffectFeed(() => {
    DB.getOpportunity(codigo).then(setOpp);
  }, [codigo]);

  if (!opp) {
    return (
      <div className="py-14 text-center" role="status" aria-live="polite">
        <p className="m-0 font-semibold">Cargando oportunidad…</p>
      </div>
    );
  }

  const t = tiempoRestante(opp.fecha_cierre);
  const enSeguimiento = opp.ua.estado_seguimiento != null;

  async function hacerSeguimiento() {
    await DB.updateSeguimiento(opp.codigo, "pendiente");
    avisar("Agregada a tu tablero de seguimiento ✓");
    irA("seguimiento");
  }

  return (
    <div data-screen-label="Detalle de oportunidad" className="screen-enter max-w-[760px]">
      <button
        type="button"
        onClick={() => irA("feed")}
        className="min-h-[44px] inline-flex items-center gap-2 font-semibold text-[var(--primary)] hover:underline mb-4"
      >
        ← Volver a oportunidades
      </button>

      <Card className="p-6 flex flex-col gap-5">
        {/* Cabecera */}
        <div className="flex flex-col sm:flex-row gap-5 sm:items-start">
          <ScoreBadge score={opp.ua.score} size="lg" />
          <div className="flex-1">
            <p className="m-0 text-help font-semibold">N° {opp.codigo}</p>
            <h1 className="m-0 mt-1 text-[1.35em] font-bold leading-snug">{opp.nombre}</h1>
            <p className="m-0 mt-2 text-[var(--text-2)]">{opp.organismo} · {opp.region}</p>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-3">
              <span className="font-bold text-[1.25em] tabular-nums">{fmtCLP(opp.monto_clp)}</span>
              <CierreChip fecha={opp.fecha_cierre} />
              <span className="text-[0.9em] text-[var(--text-2)]">Cierra el {fmtFecha(opp.fecha_cierre)}</span>
            </div>
            <div className="mt-3"><AccionChip accion={opp.ua.accion} /></div>
          </div>
        </div>

        {/* Análisis del asistente */}
        <div className="flex flex-col gap-4">
          <section className="rounded-[var(--radius-sm)] p-4 bg-[var(--primary-soft)]">
            <h2 className="m-0 text-[1em] font-bold flex items-center gap-2">
              En resumen
              <Help texto="Tu asistente leyó la publicación completa y la resumió en lenguaje simple, pensando en tu negocio." />
            </h2>
            <p className="m-0 mt-2 leading-relaxed">{opp.ua.resumen}</p>
          </section>

          <section>
            <h2 className="m-0 text-[1em] font-bold">¿Por qué esta nota?</h2>
            <p className="m-0 mt-1 leading-relaxed text-[var(--text-2)]">{opp.ua.justificacion}</p>
          </section>

          <section className="rounded-[var(--radius-sm)] p-4" style={{ background: "var(--warn-soft)" }}>
            <h2 className="m-0 text-[1em] font-bold" style={{ color: "var(--warn)" }}>Ojo con esto</h2>
            <p className="m-0 mt-1 leading-relaxed">{opp.ua.riesgo}</p>
          </section>

          {opp.ua.precio_sugerido_clp && (
            <section className="flex items-center gap-2 flex-wrap">
              <h2 className="m-0 text-[1em] font-bold">Precio sugerido:</h2>
              <span className="font-bold text-[1.15em] tabular-nums">{fmtCLP(opp.ua.precio_sugerido_clp)}</span>
              <Help texto="Precio de venta total estimado para ser competitivo, según compras parecidas. Es solo una referencia: tú decides tu precio." />
            </section>
          )}
        </div>

        {/* Acciones */}
        <div className="flex flex-col gap-3 pt-2 border-t border-[var(--border)]">
          {enSeguimiento ? (
            <div className="rounded-[var(--radius-sm)] p-4 bg-[var(--ok-soft)] flex items-center gap-2 flex-wrap">
              <span className="font-semibold" style={{ color: "var(--ok)" }}>
                ✓ Ya está en tu tablero ({ESTADOS_SEGUIMIENTO[opp.ua.estado_seguimiento]})
              </span>
              <Btn variant="ghost" size="sm" onClick={() => irA("seguimiento")}>Ir al tablero →</Btn>
            </div>
          ) : (
            <Btn size="lg" onClick={() => setConfirmando(true)}>★ Hacer seguimiento</Btn>
          )}
          <div className="flex flex-col sm:flex-row gap-3">
            <Btn variant="secondary" className="flex-1" onClick={() => irA("calculadora", { codigo: opp.codigo })}>
              🧮 Calcular mi ganancia
            </Btn>
            <a
              href={opp.url_mp}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 min-h-[48px] inline-flex items-center justify-center gap-2 px-5 font-semibold rounded-[10px]
                         text-[var(--text)] bg-[var(--surface)] border-2 border-[var(--border-strong)]
                         hover:border-[var(--primary)] hover:text-[var(--primary)] no-underline"
            >
              Ver en Mercado Público ↗
            </a>
          </div>
          <p className="m-0 text-help text-center">
            La oferta se envía siempre en el portal oficial de Mercado Público. Aquí solo la preparas y le haces seguimiento.
          </p>
        </div>
      </Card>

      {confirmando && (
        <Modal title="¿Hacer seguimiento a esta compra?" onClose={() => setConfirmando(false)}>
          <p className="mt-0">
            Se agregará a tu tablero en la columna <strong>“Pendiente”</strong> para que no se te pase la fecha.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mt-5">
            <Btn className="flex-1" onClick={hacerSeguimiento}>Sí, hacer seguimiento</Btn>
            <Btn variant="secondary" className="flex-1" onClick={() => setConfirmando(false)}>Ahora no</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

Object.assign(window, { PantallaFeed, PantallaDetalle, ACCION_INFO, ESTADOS_SEGUIMIENTO, AccionChip, CierreChip });
