// ============================================================
// PANTALLA: Panel de Ganancias
// Lee la vista v_ganancias (total, ganadas, enviadas, tasa) y
// arma gráficos simples por mes y por región con barras.
// ============================================================
const { useState: useStateGan, useEffect: useEffectGan } = React;

function TarjetaKPI({ titulo, valor, ayuda, color }) {
  return (
    <Card className="p-5 flex flex-col gap-1">
      <p className="m-0 text-[0.9em] font-semibold text-[var(--text-2)] flex items-center gap-2">
        {titulo}
        {ayuda && <Help texto={ayuda} />}
      </p>
      <p className="m-0 text-[1.7em] font-bold tabular-nums leading-tight" style={color ? { color } : {}}>
        {valor}
      </p>
    </Card>
  );
}

function PantallaGanancias({ irA }) {
  const [datos, setDatos] = useStateGan(null);

  useEffectGan(() => {
    DB.getGanancias().then(setDatos);
  }, []);

  if (!datos) {
    return <p role="status" aria-live="polite" className="py-10 text-center font-semibold">Calculando tus ganancias…</p>;
  }

  const { vista, rows } = datos;
  const ganadas = rows.filter((r) => r.estado_seguimiento === "ganada" && r.monto_ganado);
  const enProceso = rows
    .filter((r) => ["pendiente", "cotizando", "enviada"].includes(r.estado_seguimiento))
    .reduce((s, r) => s + (r.opportunities?.monto_clp || 0), 0);

  // Agrupar por mes (últimos 6) y por región
  const porMes = {};
  const porRegion = {};
  ganadas.forEach((r) => {
    const d = new Date(r.fecha_resultado);
    const key = d.toLocaleDateString("es-CL", { month: "short", year: "2-digit" });
    porMes[key] = { fecha: d, total: (porMes[key]?.total || 0) + r.monto_ganado };
    const reg = r.opportunities?.region || "Otra";
    porRegion[reg] = (porRegion[reg] || 0) + r.monto_ganado;
  });
  const mesesOrdenados = Object.entries(porMes).sort((a, b) => a[1].fecha - b[1].fecha);
  const maxMes = Math.max(...mesesOrdenados.map(([, v]) => v.total), 0);
  const regionesOrdenadas = Object.entries(porRegion).sort((a, b) => b[1] - a[1]);
  const maxRegion = Math.max(...regionesOrdenadas.map(([, v]) => v), 0);

  return (
    <div data-screen-label="Panel de ganancias" className="screen-enter">
      <header className="mb-5">
        <h1 className="m-0 text-[1.5em] font-bold">Tus ganancias</h1>
        <p className="m-0 mt-1 text-[var(--text-2)]">Cómo te ha ido vendiéndole al Estado.</p>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
        <TarjetaKPI
          titulo="Total ganado"
          valor={fmtCLP(vista.total_ganado_clp)}
          color="var(--ok)"
          ayuda="La suma de todas las compras que te adjudicaron (montos netos que ingresaste al ganarlas)."
        />
        <TarjetaKPI
          titulo="En proceso"
          valor={fmtCLP(enProceso)}
          ayuda="El monto publicado de las compras que tienes en tu tablero y aún no se resuelven (pendientes, cotizando o enviadas)."
        />
        <TarjetaKPI
          titulo="Tasa de éxito"
          valor={vista.enviadas > 0 ? `${vista.tasa_exito_pct}%` : "—"}
          ayuda={`De las ofertas que han llegado a resolverse, cuántas ganaste. Hoy: ${vista.ganadas} ganadas de ${vista.enviadas} enviadas.`}
        />
      </div>

      {ganadas.length === 0 ? (
        <Card>
          <EmptyState
            icono="🌱"
            titulo="Todavía no registras ventas ganadas"
            texto="Cuando muevas una compra a “Ganada” en tu tablero, aquí verás cuánto has ganado por mes y por región."
          >
            <Btn onClick={() => irA("seguimiento")}>Ir a mi tablero</Btn>
          </EmptyState>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 items-start">
          <Card className="p-5">
            <h2 className="m-0 text-[1.1em] font-bold mb-4">Ganancia por mes</h2>
            <div className="flex flex-col gap-4">
              {mesesOrdenados.map(([mes, v]) => (
                <BarRow key={mes} label={mes.charAt(0).toUpperCase() + mes.slice(1)} value={v.total} max={maxMes} fmt={fmtCLP} />
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <h2 className="m-0 text-[1.1em] font-bold mb-4">Ganancia por región</h2>
            <div className="flex flex-col gap-4">
              {regionesOrdenadas.map(([reg, v]) => (
                <BarRow key={reg} label={reg} value={v} max={maxRegion} fmt={fmtCLP} />
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { PantallaGanancias });
