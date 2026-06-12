// ============================================================
// PANTALLA: Tablero de Seguimiento (Kanban)
// - Escritorio: arrastrar tarjetas entre columnas.
// - Siempre disponible (y en celular): botón "Mover a…" con
//   opciones grandes — a prueba de errores y 100% teclado.
// - Al pasar a "Ganada" se pide el monto ganado.
// ============================================================
const { useState: useStateKan, useEffect: useEffectKan } = React;

const COLUMNAS = [
  { id: "pendiente", titulo: "Pendiente", hint: "Te interesa, pero aún no empiezas la cotización." },
  { id: "cotizando", titulo: "Cotizando", hint: "Estás armando el precio y los documentos." },
  { id: "enviada", titulo: "Enviada", hint: "Ya ofertaste en Mercado Público. A esperar." },
  { id: "ganada", titulo: "Ganada 🎉", hint: "¡Te la adjudicaron!" },
  { id: "perdida", titulo: "Perdida", hint: "No resultó esta vez. Sirve para aprender." },
];

function TarjetaKanban({ opp, quote, onVer, onMover, onQuitar }) {
  const t = tiempoRestante(opp.fecha_cierre);
  const esGanada = opp.ua.estado_seguimiento === "ganada";
  const esCerrada = ["ganada", "perdida"].includes(opp.ua.estado_seguimiento);
  return (
    <div
      className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-sm)] shadow-[var(--shadow)] p-4 flex flex-col gap-2 cursor-grab active:cursor-grabbing"
      draggable="true"
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", opp.codigo);
        e.dataTransfer.effectAllowed = "move";
        e.currentTarget.classList.add("dragging");
      }}
      onDragEnd={(e) => e.currentTarget.classList.remove("dragging")}
      aria-label={`${opp.nombre}, ${fmtCLP(opp.monto_clp)}`}
    >
      <button
        type="button"
        onClick={() => onVer(opp.codigo)}
        className="text-left font-bold leading-snug hover:text-[var(--primary)] hover:underline"
      >
        {opp.nombre}
      </button>
      <p className="m-0 text-[0.85em] text-[var(--text-2)]">{opp.organismo}</p>
      <div className="flex flex-col gap-0.5 text-[0.92em]">
        <span className="font-bold tabular-nums">{fmtCLP(opp.monto_clp)}</span>
        {esGanada ? (
          <span className="font-semibold" style={{ color: "var(--ok)" }}>
            Ganaste: {fmtCLP(opp.ua.monto_ganado)}
          </span>
        ) : quote ? (
          <span className="font-semibold" style={{ color: "var(--ok)" }}>
            Ganancia est.: {fmtCLP(quote.ganancia_neta)}
          </span>
        ) : (
          <span className="text-help">Sin cotización aún</span>
        )}
        {!esCerrada && (
          <span style={{ color: t.urgente ? "var(--bad)" : "var(--text-2)" }} className="text-[0.92em]">
            ⏱ {t.texto}
          </span>
        )}
      </div>
      <div className="flex gap-2 mt-1 flex-wrap">
        <Btn variant="secondary" size="sm" onClick={() => onMover(opp)} className="flex-1">
          Mover a…
        </Btn>
        <button
          type="button"
          onClick={() => onQuitar(opp)}
          aria-label={`Quitar ${opp.nombre} del tablero`}
          className="min-h-[44px] min-w-[44px] rounded-[10px] grid place-items-center text-[var(--text-2)]
                     hover:bg-[var(--bad-soft)] hover:text-[var(--bad)]"
          title="Quitar del tablero"
        >
          🗑
        </button>
      </div>
    </div>
  );
}

function PantallaSeguimiento({ irA, avisar }) {
  const [opps, setOpps] = useStateKan(null);
  const [quotes, setQuotes] = useStateKan([]);
  const [moviendo, setMoviendo] = useStateKan(null);      // opp en modal "Mover a…"
  const [pidiendoMonto, setPidiendoMonto] = useStateKan(null); // {opp} al pasar a ganada
  const [montoGanado, setMontoGanado] = useStateKan("");
  const [errorMonto, setErrorMonto] = useStateKan("");
  const [quitando, setQuitando] = useStateKan(null);
  const [dropCol, setDropCol] = useStateKan(null);

  async function cargar() {
    const [o, q] = await Promise.all([DB.getOpportunities(), DB.getAllQuotes()]);
    setOpps(o);
    setQuotes(q);
  }
  useEffectKan(() => { cargar(); }, []);

  const enTablero = (opps || []).filter((o) => o.ua.estado_seguimiento != null);
  const quoteDe = (codigo) => {
    const qs = quotes.filter((q) => q.codigo === codigo);
    return qs.length ? qs[qs.length - 1] : null;
  };

  async function mover(opp, estado) {
    if (estado === "ganada") {
      const q = quoteDe(opp.codigo);
      setMontoGanado(String(q ? q.precio_venta_neto : opp.ua.precio_sugerido_clp || opp.monto_clp));
      setErrorMonto("");
      setPidiendoMonto(opp);
      setMoviendo(null);
      return;
    }
    await DB.updateSeguimiento(opp.codigo, estado);
    setMoviendo(null);
    await cargar();
    avisar(`Movida a “${COLUMNAS.find((c) => c.id === estado).titulo.replace(" 🎉", "")}” ✓`);
  }

  async function confirmarGanada() {
    const n = parseInt(String(montoGanado).replace(/\D/g, ""), 10);
    if (!n || n <= 0) {
      setErrorMonto("Escribe el monto en pesos, solo números. Ej.: 1500000");
      return;
    }
    await DB.updateSeguimiento(pidiendoMonto.codigo, "ganada", n);
    setPidiendoMonto(null);
    await cargar();
    avisar("¡Felicitaciones! Quedó registrada como ganada 🎉");
  }

  return (
    <div data-screen-label="Tablero de seguimiento" className="screen-enter">
      <header className="mb-5">
        <h1 className="m-0 text-[1.5em] font-bold">Tu tablero de seguimiento</h1>
        <p className="m-0 mt-1 text-[var(--text-2)]">
          Arrastra las tarjetas o usa “Mover a…” para avanzar cada compra hasta ganarla.
        </p>
      </header>

      {opps === null ? (
        <p role="status" aria-live="polite" className="py-10 text-center font-semibold">Cargando tu tablero…</p>
      ) : enTablero.length === 0 ? (
        <Card>
          <EmptyState
            icono="📋"
            titulo="Tu tablero está vacío"
            texto="Cuando encuentres una compra que te interese, toca “Hacer seguimiento” en su detalle y aparecerá aquí, en la columna Pendiente."
          >
            <Btn onClick={() => irA("feed")}>Ver oportunidades</Btn>
          </EmptyState>
        </Card>
      ) : (
        <div className="kanban-scroll flex gap-4 overflow-x-auto pb-4 items-start" role="list" aria-label="Columnas del tablero">
          {COLUMNAS.map((col) => {
            const tarjetas = enTablero.filter((o) => o.ua.estado_seguimiento === col.id);
            return (
              <section
                key={col.id}
                role="listitem"
                aria-label={`Columna ${col.titulo}: ${tarjetas.length} tarjetas`}
                className={`min-w-[270px] w-[270px] shrink-0 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--border)] p-3 flex flex-col gap-3 ${dropCol === col.id ? "drop-target" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setDropCol(col.id); }}
                onDragLeave={() => setDropCol(null)}
                onDrop={async (e) => {
                  e.preventDefault();
                  setDropCol(null);
                  const codigo = e.dataTransfer.getData("text/plain");
                  const opp = enTablero.find((o) => o.codigo === codigo);
                  if (opp && opp.ua.estado_seguimiento !== col.id) await mover(opp, col.id);
                }}
              >
                <div className="flex items-center justify-between px-1">
                  <h2 className="m-0 text-[0.95em] font-bold">{col.titulo}</h2>
                  <span className="text-[0.85em] font-bold text-[var(--text-2)] bg-[var(--surface)] rounded-full min-w-[28px] h-[28px] grid place-items-center px-2" aria-hidden="true">
                    {tarjetas.length}
                  </span>
                </div>
                {tarjetas.length === 0 ? (
                  <p className="m-0 p-2 text-[0.85em] text-[var(--text-2)] leading-snug">{col.hint}</p>
                ) : (
                  tarjetas.map((o) => (
                    <TarjetaKanban
                      key={o.codigo}
                      opp={o}
                      quote={quoteDe(o.codigo)}
                      onVer={(codigo) => irA("detalle", { codigo })}
                      onMover={setMoviendo}
                      onQuitar={setQuitando}
                    />
                  ))
                )}
              </section>
            );
          })}
        </div>
      )}

      {/* Modal Mover a… */}
      {moviendo && (
        <Modal title="¿A qué columna la movemos?" onClose={() => setMoviendo(null)}>
          <p className="mt-0 text-help">{moviendo.nombre}</p>
          <div className="flex flex-col gap-2 mt-3">
            {COLUMNAS.map((c) => (
              <Btn
                key={c.id}
                variant={c.id === moviendo.ua.estado_seguimiento ? "ghost" : "secondary"}
                disabled={c.id === moviendo.ua.estado_seguimiento}
                onClick={() => mover(moviendo, c.id)}
                className="justify-start"
              >
                {c.titulo} {c.id === moviendo.ua.estado_seguimiento ? "(está aquí)" : ""}
              </Btn>
            ))}
          </div>
        </Modal>
      )}

      {/* Modal monto ganado */}
      {pidiendoMonto && (
        <Modal title="¡Buena! ¿Por cuánto la ganaste?" onClose={() => setPidiendoMonto(null)}>
          <p className="mt-0">
            Escribe el monto adjudicado (neto, sin IVA). Lo usaremos en tu panel de ganancias.
          </p>
          <Field id="monto-ganado" label="Monto ganado" error={errorMonto}>
            <input
              id="monto-ganado"
              className={inputCls + " text-[1.2em] font-bold tabular-nums"}
              inputMode="numeric"
              value={montoGanado ? "$" + Number(String(montoGanado).replace(/\D/g, "") || 0).toLocaleString("es-CL") : ""}
              onChange={(e) => setMontoGanado(e.target.value.replace(/\D/g, ""))}
              aria-invalid={!!errorMonto}
            />
          </Field>
          <div className="flex flex-col sm:flex-row gap-3 mt-5">
            <Btn className="flex-1" onClick={confirmarGanada}>Guardar como ganada 🎉</Btn>
            <Btn variant="secondary" className="flex-1" onClick={() => setPidiendoMonto(null)}>Cancelar</Btn>
          </div>
        </Modal>
      )}

      {/* Confirmación de quitar */}
      {quitando && (
        <Modal title="¿Quitar del tablero?" onClose={() => setQuitando(null)}>
          <p className="mt-0">
            <strong>{quitando.nombre}</strong> saldrá de tu tablero, pero seguirá apareciendo en tus oportunidades. No se borra nada más.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mt-5">
            <Btn
              variant="danger"
              className="flex-1"
              onClick={async () => {
                await DB.updateSeguimiento(quitando.codigo, null);
                setQuitando(null);
                await cargar();
                avisar("Quitada del tablero");
              }}
            >
              Sí, quitar
            </Btn>
            <Btn variant="secondary" className="flex-1" onClick={() => setQuitando(null)}>No, dejarla</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

Object.assign(window, { PantallaSeguimiento, COLUMNAS });
