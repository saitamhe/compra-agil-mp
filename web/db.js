// ============================================================
// CAPA DE DATOS (window.DB)
// ------------------------------------------------------------
// Una sola interfaz para toda la app. Dos modos:
//  - DEMO: datos de ejemplo persistidos en localStorage.
//  - SUPABASE: usa @supabase/supabase-js con la anon key
//    (RLS hace que cada usuario vea solo lo suyo).
// Todas las funciones son async y devuelven objetos planos.
// ============================================================
(function () {
  const LS_KEY = "oportunia_demo_db_v1";
  const cfg = window.APP_CONFIG;
  let sb = null; // cliente supabase (solo modo real)

  // ---------- utilidades ----------
  function loadLS() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* datos corruptos: se regeneran */ }
    return null;
  }
  function saveLS(state) {
    localStorage.setItem(LS_KEY, JSON.stringify(state));
  }
  function freshState() {
    return {
      session: null, // {email, nombre}
      onboarded: false,
      profile: JSON.parse(JSON.stringify(window.MOCK_PROFILE)),
      config: JSON.parse(JSON.stringify(window.MOCK_CONFIG)),
      opportunities: JSON.parse(JSON.stringify(window.MOCK_OPPORTUNITIES)),
      quotes: JSON.parse(JSON.stringify(window.MOCK_QUOTES)),
    };
  }

  let state = loadLS() || freshState();

  // Cálculo de IVA: en Supabase lo hacen columnas generadas en la BD.
  // En modo demo, esta función SIMULA esas columnas (misma fórmula).
  function computeQuote(q) {
    const pct = (q.iva_pct ?? 19) / 100;
    const iva_credito = Math.round(q.costo_neto * pct);
    const iva_debito = Math.round(q.precio_venta_neto * pct);
    return {
      ...q,
      iva_credito,
      iva_debito,
      iva_a_pagar: iva_debito - iva_credito,
      costo_bruto: q.costo_neto + iva_credito,
      total_venta: q.precio_venta_neto + iva_debito,
      ganancia_neta: q.precio_venta_neto - q.costo_neto,
      margen_pct: q.precio_venta_neto > 0
        ? Math.round(((q.precio_venta_neto - q.costo_neto) / q.precio_venta_neto) * 1000) / 10
        : 0,
    };
  }

  // ---------- API pública ----------
  const DB = {
    demo: cfg.DEMO_MODE,

    async init() {
      if (!cfg.DEMO_MODE && window.supabase) {
        sb = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
      }
    },

    // ----- sesión -----
    async getSession() {
      if (sb) {
        const { data } = await sb.auth.getSession();
        return data.session
          ? { email: data.session.user.email, nombre: data.session.user.user_metadata?.full_name || "" }
          : null;
      }
      return state.session;
    },
    async signInWithGoogle() {
      if (sb) {
        await sb.auth.signInWithOAuth({ provider: "google" });
        return null; // redirige fuera de la app
      }
      state.session = { email: state.profile.email, nombre: state.profile.nombre_empresa };
      saveLS(state);
      return state.session;
    },
    async signOut() {
      if (sb) { await sb.auth.signOut(); return; }
      state.session = null;
      saveLS(state);
    },

    // ----- perfil y configuración -----
    isOnboarded() { return sb ? true : state.onboarded; },
    async getProfile() {
      if (sb) {
        const { data } = await sb.from("profiles").select("*").single();
        return data;
      }
      return state.profile;
    },
    async getConfig() {
      if (sb) {
        const { data } = await sb.from("user_config").select("*").single();
        return data;
      }
      return state.config;
    },
    async saveConfig(newCfg, nombreEmpresa) {
      if (sb) {
        await sb.from("user_config").upsert(newCfg);
        if (nombreEmpresa) await sb.from("profiles").update({ nombre_empresa: nombreEmpresa }).eq("id", newCfg.user_id);
        return;
      }
      state.config = { ...state.config, ...newCfg };
      if (nombreEmpresa) state.profile.nombre_empresa = nombreEmpresa;
      state.onboarded = true;
      saveLS(state);
    },

    // ----- oportunidades -----
    async getOpportunities() {
      if (sb) {
        const { data } = await sb
          .from("user_opportunities")
          .select("*, opportunities(*)")
          .order("score", { ascending: false });
        return (data || []).map((row) => ({ ...row.opportunities, ua: row }));
      }
      return state.opportunities;
    },
    async getOpportunity(codigo) {
      const all = await DB.getOpportunities();
      return all.find((o) => o.codigo === codigo) || null;
    },
    async updateSeguimiento(codigo, estado, montoGanado) {
      if (sb) {
        const patch = { estado_seguimiento: estado };
        if (estado === "ganada") patch.monto_ganado = montoGanado;
        if (estado === "ganada" || estado === "perdida") patch.fecha_resultado = new Date().toISOString();
        await sb.from("user_opportunities").update(patch).eq("codigo", codigo);
        return;
      }
      const opp = state.opportunities.find((o) => o.codigo === codigo);
      if (opp) {
        opp.ua.estado_seguimiento = estado;
        if (estado === "ganada") opp.ua.monto_ganado = montoGanado ?? opp.monto_clp;
        if (estado === "ganada" || estado === "perdida") opp.ua.fecha_resultado = new Date().toISOString();
        if (estado === null || estado === "pendiente") { opp.ua.monto_ganado = null; opp.ua.fecha_resultado = null; }
        saveLS(state);
      }
    },

    // ----- cotizaciones -----
    // Vista previa local (misma fórmula que las columnas de la BD).
    previewQuote: computeQuote,
    async getAllQuotes() {
      if (sb) {
        const { data } = await sb.from("quotes").select("*");
        return data || [];
      }
      return state.quotes.map(computeQuote);
    },
    async getQuotes(codigo) {
      if (sb) {
        const { data } = await sb.from("quotes").select("*").eq("codigo", codigo);
        return data || [];
      }
      return state.quotes.filter((q) => q.codigo === codigo).map(computeQuote);
    },
    async createQuote(q) {
      if (sb) {
        const { data } = await sb.from("quotes").insert(q).select().single();
        return data; // la BD ya trae las columnas calculadas
      }
      const saved = { ...q, id: "q-" + Date.now(), created_at: new Date().toISOString() };
      state.quotes.push(saved);
      saveLS(state);
      return computeQuote(saved);
    },

    // ----- panel de ganancias -----
    async getGanancias() {
      if (sb) {
        const { data: v } = await sb.from("v_ganancias").select("*").single();
        const { data: rows } = await sb
          .from("user_opportunities")
          .select("estado_seguimiento, monto_ganado, fecha_resultado, opportunities(region, monto_clp)");
        return { vista: v, rows: rows || [] };
      }
      const opps = state.opportunities;
      const ganadas = opps.filter((o) => o.ua.estado_seguimiento === "ganada");
      const enviadasTotal = opps.filter((o) =>
        ["enviada", "ganada", "perdida"].includes(o.ua.estado_seguimiento)).length;
      const vista = {
        total_ganado_clp: ganadas.reduce((s, o) => s + (o.ua.monto_ganado || 0), 0),
        ganadas: ganadas.length,
        enviadas: enviadasTotal,
        tasa_exito_pct: enviadasTotal > 0 ? Math.round((ganadas.length / enviadasTotal) * 100) : 0,
      };
      const rows = opps.map((o) => ({
        estado_seguimiento: o.ua.estado_seguimiento,
        monto_ganado: o.ua.monto_ganado,
        fecha_resultado: o.ua.fecha_resultado,
        opportunities: { region: o.region, monto_clp: o.monto_clp },
      }));
      return { vista, rows };
    },

    // ----- demo -----
    async resetDemo() {
      const session = state.session;
      state = freshState();
      state.session = session;
      state.onboarded = true;
      saveLS(state);
    },
  };

  window.DB = DB;
})();
