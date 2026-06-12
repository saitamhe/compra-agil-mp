// ============================================================
// PANTALLAS: Acceso (login) y Onboarding "Configura tu negocio"
// El onboarding es un editor GUIADO: el usuario escribe en
// lenguaje simple y la app arma el "asistente" (system_message)
// mostrando una vista previa legible — nunca JSON ni jerga.
// ============================================================
const { useState: useStateAcc } = React;

// ---------- Acceso ----------
function PantallaAcceso({ onEntrar }) {
  const [cargando, setCargando] = useStateAcc(false);
  return (
    <div data-screen-label="Acceso" className="min-h-screen grid place-items-center p-5 screen-enter">
      <div className="w-full max-w-[420px] flex flex-col gap-6">
        <div className="text-center flex flex-col items-center gap-3">
          <div
            className="w-[64px] h-[64px] rounded-2xl grid place-items-center text-[1.8em] font-black text-[var(--on-primary)]"
            style={{ background: "var(--primary)" }}
            aria-hidden="true"
          >
            O
          </div>
          <h1 className="m-0 text-[1.7em] font-bold leading-tight">OportunIA</h1>
          <p className="m-0 text-[var(--text-2)] text-balance">
            Encuentra compras del Estado que calzan con tu negocio, cotiza con confianza y sigue tus ventas.
          </p>
        </div>

        <Card className="p-6 flex flex-col gap-4">
          <Btn
            size="lg"
            onClick={async () => {
              setCargando(true);
              await new Promise((r) => setTimeout(r, 700));
              await DB.signInWithGoogle();
              onEntrar();
            }}
            disabled={cargando}
            aria-busy={cargando}
          >
            {cargando ? (
              "Entrando…"
            ) : (
              <span className="inline-flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="w-[26px] h-[26px] rounded-full grid place-items-center bg-white text-[0.85em] font-black"
                  style={{ color: "#4285F4" }}
                >
                  G
                </span>
                Entrar con Google
              </span>
            )}
          </Btn>
          <p className="m-0 text-help text-center">
            Usamos tu cuenta de Google solo para identificarte. No publicamos nada en tu nombre.
          </p>
        </Card>

        <p className="m-0 text-center text-help">
          Pensado para pymes y emprendedores que venden por <strong>Compra Ágil</strong> de Mercado Público.
        </p>
      </div>
    </div>
  );
}

// ---------- Onboarding ----------
function PantallaOnboarding({ configInicial, perfil, onListo, editar = false }) {
  const [paso, setPaso] = useStateAcc(0);
  const [nombre, setNombre] = useStateAcc(perfil?.nombre_empresa || "");
  const [queVende, setQueVende] = useStateAcc(configInicial?.que_vende || "");
  const [rubros, setRubros] = useStateAcc(configInicial?.rubros || []);
  const [regiones, setRegiones] = useStateAcc(configInicial?.regiones || []);
  const [montoMin, setMontoMin] = useStateAcc(configInicial?.monto_min ?? 300000);
  const [montoMax, setMontoMax] = useStateAcc(configInicial?.monto_max ?? 6000000);
  const [errores, setErrores] = useStateAcc({});
  const [guardando, setGuardando] = useStateAcc(false);

  const pasos = ["Tu negocio", "Dónde y cuánto", "Revisa y confirma"];

  // El "asistente" en lenguaje simple. Internamente es el system_message.
  const vistaPrevia = [
    `Buscaré compras del Estado para ${nombre || "tu empresa"}.`,
    queVende ? `Tu negocio vende: ${queVende.trim()}` : null,
    rubros.length ? `Me fijaré sobre todo en: ${rubros.join(", ")}.` : null,
    regiones.length
      ? `Buscaré en: ${regiones.join(", ")}.`
      : "Buscaré en todo Chile.",
    `Te mostraré compras entre ${fmtCLP(montoMin)} y ${fmtCLP(montoMax)}.`,
    "A cada una le pondré una nota de 0 a 100 según lo bien que calce con tu negocio, y te diré si conviene cotizarla.",
  ].filter(Boolean);

  function validarPaso(p) {
    const e = {};
    if (p === 0) {
      if (!nombre.trim()) e.nombre = "Escribe el nombre de tu empresa o emprendimiento.";
      if (queVende.trim().length < 15)
        e.queVende = "Cuéntanos un poco más (al menos una frase). Ej.: “Vendo artículos de aseo y papelería”.";
      if (rubros.length === 0) e.rubros = "Elige al menos un rubro tocando las opciones.";
    }
    if (p === 1) {
      if (regiones.length === 0) e.regiones = "Elige al menos una región (puedes cambiarla después).";
      if (montoMax <= montoMin) e.montos = "El monto máximo debe ser mayor que el mínimo.";
    }
    setErrores(e);
    return Object.keys(e).length === 0;
  }

  async function guardar() {
    setGuardando(true);
    const system_message = vistaPrevia.join(" ");
    await DB.saveConfig(
      {
        user_id: perfil?.id || "demo-user",
        que_vende: queVende.trim(),
        rubros,
        regiones,
        monto_min: montoMin,
        monto_max: montoMax,
        score_minimo: configInicial?.score_minimo ?? 40,
        modelo: configInicial?.modelo ?? "estandar",
        activo: true,
        system_message,
      },
      nombre.trim()
    );
    await new Promise((r) => setTimeout(r, 500));
    onListo();
  }

  return (
    <div data-screen-label="Onboarding" className="min-h-screen p-5 screen-enter">
      <div className="max-w-[640px] mx-auto flex flex-col gap-6 pb-10">
        <header className="pt-4">
          <p className="m-0 text-help font-semibold uppercase tracking-wide">
            {editar ? "Mi negocio" : `Paso ${paso + 1} de 3`}
          </p>
          <h1 className="m-0 mt-1 text-[1.6em] font-bold leading-tight">
            {editar ? "Edita tu negocio" : "Configura tu negocio"}
          </h1>
          {/* Barra de progreso */}
          <div className="flex gap-2 mt-4" role="progressbar" aria-valuenow={paso + 1} aria-valuemin={1} aria-valuemax={3} aria-label={`Paso ${paso + 1} de 3: ${pasos[paso]}`}>
            {pasos.map((p, i) => (
              <div key={p} className="flex-1 h-[8px] rounded-full" style={{ background: i <= paso ? "var(--primary)" : "var(--border)" }}></div>
            ))}
          </div>
        </header>

        {paso === 0 && (
          <Card className="p-6 flex flex-col gap-6">
            <Field id="ob-nombre" label="¿Cómo se llama tu empresa o emprendimiento?" error={errores.nombre}>
              <input
                id="ob-nombre"
                className={inputCls}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Ej.: Aseo Total SpA"
                aria-invalid={!!errores.nombre}
                aria-describedby={errores.nombre ? "ob-nombre-error" : undefined}
              />
            </Field>

            <Field
              id="ob-vende"
              label="¿Qué vendes? Cuéntalo con tus palabras"
              hint="Como se lo contarías a un cliente. Mientras más detalle, mejores serán las recomendaciones."
              error={errores.queVende}
            >
              <textarea
                id="ob-vende"
                className={inputCls + " py-3 min-h-[120px] resize-y"}
                value={queVende}
                onChange={(e) => setQueVende(e.target.value)}
                placeholder="Ej.: Vendemos artículos de aseo: papel higiénico, detergentes, bolsas de basura…"
                aria-invalid={!!errores.queVende}
              />
            </Field>

            <Field id="ob-rubros" label="Elige tus rubros" hint="Toca todos los que correspondan." error={errores.rubros}>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Rubros">
                {RUBROS_CL.map((r) => (
                  <ChipToggle
                    key={r}
                    checked={rubros.includes(r)}
                    onChange={(on) => setRubros(on ? [...rubros, r] : rubros.filter((x) => x !== r))}
                  >
                    {r}
                  </ChipToggle>
                ))}
              </div>
            </Field>
          </Card>
        )}

        {paso === 1 && (
          <Card className="p-6 flex flex-col gap-6">
            <Field id="ob-reg" label="¿En qué regiones puedes vender o despachar?" hint="Toca todas las que te sirvan." error={errores.regiones}>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Regiones">
                {REGIONES_CL.map((r) => (
                  <ChipToggle
                    key={r}
                    checked={regiones.includes(r)}
                    onChange={(on) => setRegiones(on ? [...regiones, r] : regiones.filter((x) => x !== r))}
                  >
                    {r}
                  </ChipToggle>
                ))}
              </div>
            </Field>

            <div className="flex flex-col gap-2">
              <p className="m-0 font-semibold flex items-center gap-2">
                ¿De qué tamaño te acomodan las ventas?
                <Help texto="Es el monto total de la compra en pesos. Compra Ágil llega hasta unos $7 millones aprox. Solo te mostraremos compras dentro de este rango." />
              </p>
              {errores.montos && (
                <p role="alert" className="m-0 text-[0.9em] font-semibold" style={{ color: "var(--bad)" }}>{errores.montos}</p>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-1">
                <Field id="ob-min" label="Desde">
                  <select id="ob-min" className={inputCls} value={montoMin} onChange={(e) => setMontoMin(+e.target.value)}>
                    {[100000, 300000, 500000, 1000000, 2000000].map((v) => (
                      <option key={v} value={v}>{fmtCLP(v)}</option>
                    ))}
                  </select>
                </Field>
                <Field id="ob-max" label="Hasta">
                  <select id="ob-max" className={inputCls} value={montoMax} onChange={(e) => setMontoMax(+e.target.value)}>
                    {[1000000, 2000000, 4000000, 6000000, 8000000].map((v) => (
                      <option key={v} value={v}>{fmtCLP(v)}</option>
                    ))}
                  </select>
                </Field>
              </div>
            </div>
          </Card>
        )}

        {paso === 2 && (
          <Card className="p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <h2 className="m-0 text-[1.15em] font-bold">Así te ayudará tu asistente</h2>
              <Help texto="Este es el resumen de lo que configuraste. El asistente usará estas instrucciones para buscar y puntuar compras. Puedes cambiarlas cuando quieras en “Mi negocio”." />
            </div>
            <div className="rounded-[var(--radius-sm)] p-5 flex flex-col gap-3 bg-[var(--primary-soft)]">
              {vistaPrevia.map((linea, i) => (
                <p key={i} className="m-0 leading-relaxed flex gap-2">
                  <span aria-hidden="true" style={{ color: "var(--primary)" }}>✓</span>
                  <span>{linea}</span>
                </p>
              ))}
            </div>
            <p className="m-0 text-help">
              ¿Algo no calza? Vuelve atrás y corrígelo. Nada queda grabado en piedra.
            </p>
          </Card>
        )}

        {/* Navegación de pasos */}
        <div className="flex gap-3 justify-between">
          {paso > 0 ? (
            <Btn variant="secondary" onClick={() => setPaso(paso - 1)}>← Atrás</Btn>
          ) : <span></span>}
          {paso < 2 ? (
            <Btn size="lg" onClick={() => { if (validarPaso(paso)) { setErrores({}); setPaso(paso + 1); window.scrollTo(0, 0); } }}>
              Continuar →
            </Btn>
          ) : (
            <Btn size="lg" onClick={guardar} disabled={guardando} aria-busy={guardando}>
              {guardando ? "Guardando…" : editar ? "Guardar cambios" : "¡Listo, buscar oportunidades!"}
            </Btn>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { PantallaAcceso, PantallaOnboarding });
