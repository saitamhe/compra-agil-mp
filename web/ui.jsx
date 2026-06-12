// ============================================================
// COMPONENTES UI REUTILIZABLES — accesibles (WCAG 2.2 AA)
// Botones grandes (≥44px), foco visible, labels y roles ARIA.
// Se exportan a window al final del archivo.
// ============================================================
const { useState, useEffect, useRef, useCallback } = React;

// ---------- formato ----------
function fmtCLP(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return "$" + Math.round(n).toLocaleString("es-CL");
}
function fmtFecha(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-CL", { day: "numeric", month: "long" });
}

// Cuenta regresiva en lenguaje simple
function tiempoRestante(iso) {
  const ms = new Date(iso) - new Date();
  if (ms <= 0) return { texto: "Cerrada", urgente: false, cerrada: true };
  const horas = ms / 36e5;
  if (horas < 24) return { texto: `Cierra en ${Math.max(1, Math.floor(horas))} h`, urgente: true, cerrada: false };
  const diasN = Math.floor(horas / 24);
  return {
    texto: diasN === 1 ? "Cierra mañana" : `Cierra en ${diasN} días`,
    urgente: diasN <= 2,
    cerrada: false,
  };
}

// ---------- Botón ----------
function Btn({ variant = "primary", size = "md", className = "", children, ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 font-semibold rounded-[10px] transition-colors " +
    "disabled:opacity-50 disabled:cursor-not-allowed select-none";
  const sizes = {
    md: "min-h-[48px] px-5 text-[1em]",
    lg: "min-h-[56px] px-7 text-[1.06em]",
    sm: "min-h-[44px] px-4 text-[0.94em]",
  };
  const variants = {
    primary: "text-[var(--on-primary)] bg-[var(--primary)] hover:bg-[var(--primary-hover)]",
    secondary:
      "text-[var(--text)] bg-[var(--surface)] border-2 border-[var(--border-strong)] hover:border-[var(--primary)] hover:text-[var(--primary)]",
    ghost: "text-[var(--primary)] bg-transparent hover:bg-[var(--primary-soft)]",
    danger: "text-[var(--on-primary)] bg-[var(--bad)] hover:opacity-90",
  };
  return (
    <button type="button" className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

// ---------- Tarjeta ----------
function Card({ className = "", children, ...props }) {
  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] shadow-[var(--shadow)] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

// ---------- Score semáforo ----------
function scoreInfo(score) {
  if (score >= 80) return { nivel: "verde", etiqueta: "Buena para ti", color: "var(--ok)", soft: "var(--ok-soft)" };
  if (score >= 60) return { nivel: "amarillo", etiqueta: "Revísala", color: "var(--warn)", soft: "var(--warn-soft)" };
  return { nivel: "rojo", etiqueta: "No te conviene", color: "var(--bad)", soft: "var(--bad-soft)" };
}

function ScoreBadge({ score, size = "md" }) {
  const info = scoreInfo(score);
  const dims = size === "lg" ? "w-[76px] h-[76px] text-[1.7em]" : "w-[56px] h-[56px] text-[1.25em]";
  return (
    <div className="flex flex-col items-center gap-1" aria-label={`Puntaje ${score} de 100: ${info.etiqueta}`} role="img">
      <div
        className={`${dims} rounded-full grid place-items-center font-bold border-4`}
        style={{ color: info.color, background: info.soft, borderColor: info.color }}
        aria-hidden="true"
      >
        {score}
      </div>
      <span className="text-[0.78em] font-semibold text-center leading-tight" style={{ color: info.color }} aria-hidden="true">
        {info.etiqueta}
      </span>
    </div>
  );
}

// ---------- Ayuda "¿Qué es esto?" ----------
function Help({ texto, label = "¿Qué es esto?" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("click", close); document.removeEventListener("keydown", esc); };
  }, [open]);
  return (
    <span className="relative inline-flex" ref={ref}>
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="w-[28px] h-[28px] min-h-0 rounded-full grid place-items-center text-[0.8em] font-bold
                   text-[var(--primary)] bg-[var(--primary-soft)] hover:opacity-80 align-middle"
      >
        ?
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute z-40 left-1/2 -translate-x-1/2 top-[34px] w-[260px] p-3 text-[0.85em] leading-snug
                     bg-[var(--surface)] text-[var(--text)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] shadow-[var(--shadow-lg)]"
        >
          {texto}
        </span>
      )}
    </span>
  );
}

// ---------- Campo de formulario ----------
function Field({ id, label, hint, error, children, optional = false }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="font-semibold flex items-center gap-2">
        {label}
        {optional && <span className="text-[0.8em] font-normal text-[var(--text-2)]">(opcional)</span>}
      </label>
      {hint && <p id={`${id}-hint`} className="text-help m-0">{hint}</p>}
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="m-0 text-[0.9em] font-semibold" style={{ color: "var(--bad)" }}>
          {error}
        </p>
      )}
    </div>
  );
}

const inputCls =
  "min-h-[48px] px-4 rounded-[10px] border-2 border-[var(--border-strong)] bg-[var(--surface)] " +
  "text-[var(--text)] w-full focus:border-[var(--primary)] placeholder:text-[var(--text-2)]";

// ---------- Modal accesible ----------
function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    const esc = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", esc);
    // foco al abrir
    setTimeout(() => {
      const f = ref.current?.querySelector("button, [href], input, select, textarea");
      if (f) f.focus();
    }, 30);
    return () => { document.removeEventListener("keydown", esc); if (prev?.focus) prev.focus(); };
  }, []);
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center p-4"
      style={{ background: "oklch(0.15 0.02 250 / 0.55)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`bg-[var(--surface)] rounded-[var(--radius)] shadow-[var(--shadow-lg)] w-full ${wide ? "max-w-[640px]" : "max-w-[460px]"} max-h-[88vh] overflow-y-auto`}
      >
        <div className="flex items-center justify-between gap-3 p-5 pb-0">
          <h2 className="m-0 text-[1.2em] font-bold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar ventana"
            className="w-[44px] h-[44px] shrink-0 rounded-full grid place-items-center text-[1.2em]
                       bg-[var(--surface-2)] hover:bg-[var(--border)]"
          >
            ✕
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

// ---------- Aviso (toast) ----------
function Toast({ msg }) {
  if (!msg) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-[88px] md:bottom-6 left-1/2 -translate-x-1/2 z-[60] px-5 py-3 rounded-full
                 font-semibold shadow-[var(--shadow-lg)] text-[var(--on-primary)] bg-[var(--primary)] max-w-[90vw] text-center"
    >
      {msg}
    </div>
  );
}

// ---------- Estado vacío ----------
function EmptyState({ icono = "📭", titulo, texto, children }) {
  return (
    <div className="text-center py-12 px-6 flex flex-col items-center gap-3">
      <div className="text-[2.6em]" aria-hidden="true">{icono}</div>
      <h3 className="m-0 text-[1.15em] font-bold">{titulo}</h3>
      <p className="m-0 text-[var(--text-2)] max-w-[420px]">{texto}</p>
      {children}
    </div>
  );
}

// ---------- Chip seleccionable ----------
function ChipToggle({ checked, onChange, children }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`min-h-[44px] px-4 rounded-full border-2 font-medium transition-colors ${
        checked
          ? "border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--primary)]"
          : "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] hover:border-[var(--primary)]"
      }`}
    >
      {checked ? "✓ " : ""}{children}
    </button>
  );
}

// ---------- Barra simple para gráficos ----------
function BarRow({ label, value, max, fmt }) {
  const pct = max > 0 ? Math.max(3, Math.round((value / max) * 100)) : 0;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between gap-3 text-[0.92em]">
        <span className="font-medium">{label}</span>
        <span className="font-bold tabular-nums">{fmt ? fmt(value) : value}</span>
      </div>
      <div className="h-[14px] rounded-full bg-[var(--surface-2)] overflow-hidden" role="img"
           aria-label={`${label}: ${fmt ? fmt(value) : value}`}>
        <div className="h-full rounded-full" style={{ width: pct + "%", background: "var(--primary)" }}></div>
      </div>
    </div>
  );
}

Object.assign(window, {
  fmtCLP, fmtFecha, tiempoRestante, scoreInfo,
  Btn, Card, ScoreBadge, Help, Field, Modal, Toast, EmptyState, ChipToggle, BarRow,
  inputCls,
});
