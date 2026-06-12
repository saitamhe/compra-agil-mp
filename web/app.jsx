// ============================================================
// APP PRINCIPAL — navegación, sesión, tema y Tweaks
// ============================================================
const { useState: useStateApp, useEffect: useEffectApp } = React;

const NAV_KEY = "oportunia_nav_v1";

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "fontSize": 17,
  "dark": false,
  "acento": "#34518E"
}/*EDITMODE-END*/;

const HUE_POR_ACENTO = { "#34518E": 252, "#0F6E62": 175, "#8C4538": 25 };

const NAV_ITEMS = [
  { id: "feed", label: "Oportunidades", icono: "🔎" },
  { id: "seguimiento", label: "Tablero", icono: "📋" },
  { id: "calculadora", label: "Calculadora", icono: "🧮" },
  { id: "ganancias", label: "Ganancias", icono: "📈" },
  { id: "negocio", label: "Mi negocio", icono: "🏪" },
];

// ---------- Mi negocio (config + cuenta) ----------
function PantallaMiNegocio({ perfil, config, recargar, onSalir, avisar }) {
  const [confirmSalir, setConfirmSalir] = useStateApp(false);
  const [confirmReset, setConfirmReset] = useStateApp(false);
  return (
    <div data-screen-label="Mi negocio">
      <PantallaOnboarding
        editar={true}
        perfil={perfil}
        configInicial={config}
        onListo={async () => { await recargar(); avisar("Cambios guardados ✓"); }}
      />
      <div className="max-w-[640px] mx-auto px-5 pb-28 md:pb-10 -mt-2 flex flex-col gap-3">
        <Card className="p-5 flex flex-col gap-3">
          <h2 className="m-0 text-[1.1em] font-bold">Tu cuenta</h2>
          <p className="m-0 text-help">Conectada como {perfil?.email}</p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Btn variant="secondary" className="flex-1" onClick={() => setConfirmSalir(true)}>Cerrar sesión</Btn>
            {DB.demo && (
              <Btn variant="secondary" className="flex-1" onClick={() => setConfirmReset(true)}>
                Restablecer datos de ejemplo
              </Btn>
            )}
          </div>
          {DB.demo && (
            <p className="m-0 text-help">
              Estás en <strong>modo demo</strong>: los datos son de ejemplo y viven solo en este navegador.
              Para conectar tu cuenta real, agrega tus claves de Supabase en <code>config.js</code>.
            </p>
          )}
        </Card>
      </div>

      {confirmSalir && (
        <Modal title="¿Cerrar sesión?" onClose={() => setConfirmSalir(false)}>
          <p className="mt-0">Volverás a la pantalla de acceso. Tus datos quedan guardados.</p>
          <div className="flex flex-col sm:flex-row gap-3 mt-5">
            <Btn className="flex-1" onClick={onSalir}>Sí, cerrar sesión</Btn>
            <Btn variant="secondary" className="flex-1" onClick={() => setConfirmSalir(false)}>Cancelar</Btn>
          </div>
        </Modal>
      )}
      {confirmReset && (
        <Modal title="¿Restablecer los datos de ejemplo?" onClose={() => setConfirmReset(false)}>
          <p className="mt-0">
            Se borrarán los cambios que hiciste en el tablero y las cotizaciones guardadas, y volverán los datos de ejemplo originales. Esta acción no se puede deshacer.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mt-5">
            <Btn
              variant="danger"
              className="flex-1"
              onClick={async () => {
                await DB.resetDemo();
                setConfirmReset(false);
                await recargar();
                avisar("Datos de ejemplo restablecidos");
              }}
            >
              Sí, restablecer
            </Btn>
            <Btn variant="secondary" className="flex-1" onClick={() => setConfirmReset(false)}>Cancelar</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ---------- App ----------
function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [sesion, setSesion] = useStateApp(undefined); // undefined = comprobando
  const [perfil, setPerfil] = useStateApp(null);
  const [config, setConfig] = useStateApp(null);
  const [nav, setNav] = useStateApp(() => {
    try { return JSON.parse(localStorage.getItem(NAV_KEY)) || { id: "feed", params: {} }; }
    catch (e) { return { id: "feed", params: {} }; }
  });
  const [toast, setToast] = useStateApp("");

  // Tema, letra y acento
  useEffectApp(() => {
    document.documentElement.dataset.theme = t.dark ? "dark" : "light";
    document.documentElement.style.setProperty("--font-base", t.fontSize + "px");
    document.documentElement.style.setProperty("--accent-hue", HUE_POR_ACENTO[t.acento] || 252);
  }, [t.dark, t.fontSize, t.acento]);

  // Sesión inicial
  useEffectApp(() => {
    (async () => {
      await DB.init();
      const s = await DB.getSession();
      setSesion(s);
      if (s) await recargar();
    })();
  }, []);

  async function recargar() {
    const [p, c] = await Promise.all([DB.getProfile(), DB.getConfig()]);
    setPerfil(p);
    setConfig(c);
  }

  function irA(id, params = {}) {
    const destino = { id, params };
    setNav(destino);
    localStorage.setItem(NAV_KEY, JSON.stringify(destino));
    window.scrollTo(0, 0);
  }

  function avisar(msg) {
    setToast(msg);
    window.clearTimeout(avisar._t);
    avisar._t = window.setTimeout(() => setToast(""), 3500);
  }

  async function entrar() {
    const s = await DB.getSession();
    setSesion(s);
    if (s) {
      await recargar();
      irA(DB.isOnboarded() ? "feed" : "onboarding");
    }
  }

  // ---------- Render ----------
  if (sesion === undefined) {
    return <p role="status" className="py-16 text-center font-semibold">Cargando…</p>;
  }

  if (!sesion) {
    return (
      <React.Fragment>
        <PantallaAcceso onEntrar={entrar} />
        <PanelTweaks t={t} setTweak={setTweak} />
      </React.Fragment>
    );
  }

  if (!DB.isOnboarded() || nav.id === "onboarding") {
    return (
      <React.Fragment>
        <PantallaOnboarding
          perfil={perfil}
          configInicial={config}
          onListo={async () => { await recargar(); irA("feed"); avisar("¡Tu asistente quedó listo! 🎉"); }}
        />
        <PanelTweaks t={t} setTweak={setTweak} />
      </React.Fragment>
    );
  }

  const navActivo = nav.id === "detalle" ? "feed" : nav.id;

  return (
    <React.Fragment>
      <a href="#contenido" className="skip-link">Saltar al contenido</a>

      {/* Barra superior */}
      <header className="sticky top-0 z-30 bg-[var(--surface)] border-b border-[var(--border)] no-print">
        <div className="max-w-[1080px] mx-auto px-4 md:px-6 h-[64px] flex items-center gap-4">
          <button type="button" onClick={() => irA("feed")} className="flex items-center gap-2.5 min-h-[44px]" aria-label="OportunIA, ir al inicio">
            <span
              className="w-[36px] h-[36px] rounded-[10px] grid place-items-center font-black text-[1.1em] text-[var(--on-primary)]"
              style={{ background: "var(--primary)" }}
              aria-hidden="true"
            >
              O
            </span>
            <span className="font-bold text-[1.1em] hidden sm:inline">OportunIA</span>
          </button>

          {DB.demo && (
            <span className="text-[0.75em] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full bg-[var(--warn-soft)]" style={{ color: "var(--warn)" }}>
              Demo
            </span>
          )}

          {/* Navegación escritorio */}
          <nav aria-label="Principal" className="hidden md:flex items-center gap-1 ml-auto">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => irA(item.id)}
                aria-current={navActivo === item.id ? "page" : undefined}
                className={`min-h-[44px] px-4 rounded-[10px] font-semibold transition-colors ${
                  navActivo === item.id
                    ? "bg-[var(--primary-soft)] text-[var(--primary)]"
                    : "text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <button
            type="button"
            onClick={() => setTweak("dark", !t.dark)}
            aria-label={t.dark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            aria-pressed={t.dark}
            className="ml-auto md:ml-2 w-[44px] h-[44px] rounded-full grid place-items-center text-[1.15em] bg-[var(--surface-2)] hover:bg-[var(--border)]"
          >
            {t.dark ? "☀️" : "🌙"}
          </button>
        </div>
      </header>

      {/* Contenido */}
      <main id="contenido" className="max-w-[1080px] mx-auto px-4 md:px-6 py-6 pb-28 md:pb-12 min-h-[70vh]">
        {nav.id === "feed" && <PantallaFeed irA={irA} />}
        {nav.id === "detalle" && <PantallaDetalle codigo={nav.params.codigo} irA={irA} avisar={avisar} />}
        {nav.id === "seguimiento" && <PantallaSeguimiento irA={irA} avisar={avisar} />}
        {nav.id === "calculadora" && <PantallaCalculadora codigo={nav.params.codigo} irA={irA} avisar={avisar} key={nav.params.codigo || "libre"} />}
        {nav.id === "ganancias" && <PantallaGanancias irA={irA} />}
        {nav.id === "negocio" && (
          <div className="-mx-4 md:-mx-6 -my-6">
            <PantallaMiNegocio
              perfil={perfil}
              config={config}
              recargar={recargar}
              avisar={avisar}
              onSalir={async () => { await DB.signOut(); setSesion(null); }}
            />
          </div>
        )}
      </main>

      {/* Navegación móvil inferior */}
      <nav
        aria-label="Principal móvil"
        className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-[var(--surface)] border-t border-[var(--border)] no-print"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="grid grid-cols-5">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => irA(item.id)}
              aria-current={navActivo === item.id ? "page" : undefined}
              className={`min-h-[60px] flex flex-col items-center justify-center gap-0.5 text-[0.68em] font-semibold ${
                navActivo === item.id ? "text-[var(--primary)]" : "text-[var(--text-2)]"
              }`}
            >
              <span className="text-[1.7em]" aria-hidden="true">{item.icono}</span>
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      <Toast msg={toast} />
      <PanelTweaks t={t} setTweak={setTweak} />
    </React.Fragment>
  );
}

// ---------- Panel de Tweaks ----------
function PanelTweaks({ t, setTweak }) {
  return (
    <TweaksPanel>
      <TweakSection label="Apariencia" />
      <TweakToggle label="Modo oscuro" value={t.dark} onChange={(v) => setTweak("dark", v)} />
      <TweakColor
        label="Color principal"
        value={t.acento}
        options={["#34518E", "#0F6E62", "#8C4538"]}
        onChange={(v) => setTweak("acento", v)}
      />
      <TweakSection label="Accesibilidad" />
      <TweakSlider
        label="Tamaño de letra"
        value={t.fontSize}
        min={15}
        max={21}
        step={1}
        unit="px"
        onChange={(v) => setTweak("fontSize", v)}
      />
    </TweaksPanel>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
