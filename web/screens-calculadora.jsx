// ============================================================
// PANTALLA: Calculadora de Cotizaciones con IVA (19%)
// El usuario ingresa costo neto y precio de venta neto.
// Los cálculos finales los hace la BD (columnas calculadas);
// aquí DB.previewQuote replica la fórmula solo para la vista
// previa en vivo. Cada cifra se explica en una línea simple.
// ============================================================
const { useState: useStateCalc, useEffect: useEffectCalc } = React;

function InputCLP({ id, value, onChange, invalid }) {
  return (
    <input
      id={id}
      className={inputCls + " text-[1.15em] font-bold tabular-nums"}
      inputMode="numeric"
      placeholder="$0"
      value={value === "" ? "" : "$" + Number(value).toLocaleString("es-CL")}
      onChange={(e) => {
        const limpio = e.target.value.replace(/\D/g, "");
        onChange(limpio === "" ? "" : parseInt(limpio, 10));
      }}
      aria-invalid={invalid || undefined}
    />
  );
}

function FilaResultado({ label, valor, explicacion, destacada = false, negativo = false }) {
  return (
    <div className={`flex flex-col gap-0.5 py-3 ${destacada ? "" : "border-b border-[var(--border)]"}`}>
      <div className="flex justify-between items-baseline gap-4">
        <span className={destacada ? "font-bold text-[1.05em]" : "font-semibold"}>{label}</span>
        <span
          className={`tabular-nums font-bold ${destacada ? "text-[1.5em]" : "text-[1.1em]"}`}
          style={negativo ? { color: "var(--bad)" } : destacada ? { color: "var(--ok)" } : {}}
        >
          {valor}
        </span>
      </div>
      <p className="m-0 text-help leading-snug">{explicacion}</p>
    </div>
  );
}

function PantallaCalculadora({ codigo, irA, avisar }) {
  const [opps, setOpps] = useStateCalc([]);
  const [codigoSel, setCodigoSel] = useStateCalc(codigo || "");
  const [descripcion, setDescripcion] = useStateCalc("");
  const [costo, setCosto] = useStateCalc("");
  const [venta, setVenta] = useStateCalc("");
  const [guardadas, setGuardadas] = useStateCalc([]);
  const [guardando, setGuardando] = useStateCalc(false);

  useEffectCalc(() => {
    DB.getOpportunities().then((all) =>
      setOpps(all.filter((o) => !tiempoRestante(o.fecha_cierre).cerrada || o.ua.estado_seguimiento != null))
    );
  }, []);
  useEffectCalc(() => {
    if (codigoSel) DB.getQuotes(codigoSel).then(setGuardadas);
    else setGuardadas([]);
  }, [codigoSel]);

  const oppSel = opps.find((o) => o.codigo === codigoSel) || null;
  const listo = costo !== "" && venta !== "" && costo > 0 && venta > 0;
  const q = listo ? DB.previewQuote({ costo_neto: costo, precio_venta_neto: venta, iva_pct: 19 }) : null;
  const perdiendo = q && q.ganancia_neta < 0;
  const margenBajo = q && !perdiendo && q.margen_pct < 10;

  async function guardar() {
    setGuardando(true);
    await DB.createQuote({
      codigo: codigoSel,
      descripcion: descripcion.trim() || "Cotización",
      costo_neto: costo,
      precio_venta_neto: venta,
      iva_pct: 19,
    });
    const nuevas = await DB.getQuotes(codigoSel);
    setGuardadas(nuevas);
    setGuardando(false);
    avisar("Cotización guardada en la oportunidad ✓");
  }

  return (
    <div data-screen-label="Calculadora de cotizaciones" className="screen-enter max-w-[760px]">
      <header className="mb-5">
        <h1 className="m-0 text-[1.5em] font-bold">Calculadora de cotizaciones</h1>
        <p className="m-0 mt-1 text-[var(--text-2)]">
          Pon tu costo y tu precio de venta, y te mostramos cuánto ganas de verdad después del IVA.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 items-start">
        {/* Entradas */}
        <Card className="p-5 flex flex-col gap-5">
          <Field
            id="c-opp"
            label="¿Para qué compra es?"
            hint="Si la eliges, podrás guardar la cotización ahí."
            optional
          >
            <select id="c-opp" className={inputCls} value={codigoSel} onChange={(e) => setCodigoSel(e.target.value)}>
              <option value="">Solo quiero calcular</option>
              {opps.map((o) => (
                <option key={o.codigo} value={o.codigo}>
                  {o.nombre.length > 48 ? o.nombre.slice(0, 48) + "…" : o.nombre}
                </option>
              ))}
            </select>
          </Field>

          {oppSel && (
            <p className="m-0 text-[0.9em] rounded-[var(--radius-sm)] p-3 bg-[var(--primary-soft)]">
              {oppSel.organismo} · monto publicado {fmtCLP(oppSel.monto_clp)}
              {oppSel.ua.precio_sugerido_clp ? ` · precio sugerido ${fmtCLP(oppSel.ua.precio_sugerido_clp)}` : ""}
            </p>
          )}

          <Field id="c-desc" label="¿Qué estás cotizando?" optional>
            <input
              id="c-desc"
              className={inputCls}
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              placeholder="Ej.: 400 rollos de papel jumbo"
            />
          </Field>

          <Field
            id="c-costo"
            label={<span>Lo que te cuesta a ti (neto) <Help texto="Lo que pagas a tu proveedor SIN IVA. Si tu factura de compra dice “Neto”, es ese número." /></span>}
            hint="Sin IVA. Es tu costo total: productos, flete, todo."
          >
            <InputCLP id="c-costo" value={costo} onChange={setCosto} />
          </Field>

          <Field
            id="c-venta"
            label={<span>Tu precio de venta (neto) <Help texto="Lo que cobrarás SIN IVA. En Mercado Público los precios suelen compararse en neto; el IVA se suma aparte." /></span>}
            hint="Sin IVA. La app le suma el 19% para mostrarte el total."
          >
            <InputCLP id="c-venta" value={venta} onChange={setVenta} invalid={perdiendo} />
          </Field>

          {perdiendo && (
            <p role="alert" className="m-0 rounded-[var(--radius-sm)] p-3 font-semibold text-[0.95em]"
               style={{ background: "var(--bad-soft)", color: "var(--bad)" }}>
              Ojo: estás vendiendo más barato de lo que te cuesta. Sube tu precio de venta para no perder plata.
            </p>
          )}
          {margenBajo && (
            <p role="alert" className="m-0 rounded-[var(--radius-sm)] p-3 font-semibold text-[0.95em]"
               style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>
              Margen bajo el 10%. Revisa si te conviene: considera tu tiempo, flete y papeleo.
            </p>
          )}
        </Card>

        {/* Resultados */}
        <Card className="p-5">
          <h2 className="m-0 text-[1.1em] font-bold mb-1">Tus números, claritos</h2>
          {!q ? (
            <EmptyState
              icono="🧮"
              titulo="Te falta llenar los montos"
              texto="Escribe cuánto te cuesta y a cuánto venderás. Aquí verás el IVA y tu ganancia real, al tiro."
            ></EmptyState>
          ) : (
            <div aria-live="polite">
              <FilaResultado
                label="Total que cobrarás (con IVA)"
                valor={fmtCLP(q.total_venta)}
                explicacion="Es lo que pagará el organismo: tu precio + 19% de IVA."
              />
              <FilaResultado
                label="IVA débito"
                valor={fmtCLP(q.iva_debito)}
                explicacion="El IVA que cobras al vender. No es tuyo: se lo debes al SII."
              />
              <FilaResultado
                label="IVA crédito"
                valor={fmtCLP(q.iva_credito)}
                explicacion="El IVA que ya pagaste al comprar. Lo descuentas de lo que debes."
              />
              <FilaResultado
                label="IVA a pagar al SII"
                valor={fmtCLP(q.iva_a_pagar)}
                explicacion="La diferencia entre ambos. Resérvala: se paga al mes siguiente."
              />
              <FilaResultado
                label="Tu ganancia neta"
                valor={fmtCLP(q.ganancia_neta)}
                explicacion="Lo que te queda limpio: precio de venta menos tu costo (ambos sin IVA)."
                destacada
                negativo={perdiendo}
              />
              <FilaResultado
                label="Margen"
                valor={q.margen_pct + "%"}
                explicacion="Qué parte de cada peso vendido es ganancia. Sobre 20% es saludable."
                destacada
                negativo={perdiendo}
              />
            </div>
          )}

          <div className="mt-4 flex flex-col gap-2">
            <Btn size="lg" disabled={!q || !codigoSel || guardando} onClick={guardar} aria-busy={guardando}>
              {guardando ? "Guardando…" : "Guardar en la oportunidad"}
            </Btn>
            {!codigoSel && q && (
              <p className="m-0 text-help text-center">Para guardarla, elige arriba a qué compra pertenece.</p>
            )}
          </div>
        </Card>
      </div>

      {/* Cotizaciones guardadas */}
      {codigoSel && guardadas.length > 0 && (
        <Card className="p-5 mt-5">
          <h2 className="m-0 text-[1.1em] font-bold mb-3">Cotizaciones guardadas en esta oportunidad</h2>
          <ul className="m-0 p-0 list-none flex flex-col gap-3">
            {guardadas.map((g) => (
              <li key={g.id} className="flex flex-wrap justify-between gap-2 border-b border-[var(--border)] pb-3">
                <div>
                  <p className="m-0 font-semibold">{g.descripcion}</p>
                  <p className="m-0 text-help">
                    Venta {fmtCLP(g.precio_venta_neto)} · costo {fmtCLP(g.costo_neto)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="m-0 font-bold" style={{ color: "var(--ok)" }}>+{fmtCLP(g.ganancia_neta)}</p>
                  <p className="m-0 text-help">{g.margen_pct}% margen</p>
                </div>
              </li>
            ))}
          </ul>
          {oppSel && oppSel.ua.estado_seguimiento == null && (
            <p className="m-0 mt-3 text-help">
              Consejo: agrega esta compra a tu tablero con “Hacer seguimiento” para no perderle la pista.
            </p>
          )}
        </Card>
      )}
    </div>
  );
}

Object.assign(window, { PantallaCalculadora });
