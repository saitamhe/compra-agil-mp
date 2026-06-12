// ============================================================
// CONFIGURACIÓN DE SUPABASE
// ------------------------------------------------------------
// Pega aquí la URL de tu proyecto y la "anon key" (NUNCA la
// service_role). Si dejas los valores de ejemplo, la app corre
// en MODO DEMO con datos de ejemplo guardados en este navegador.
// ============================================================
window.APP_CONFIG = {
  SUPABASE_URL: "https://ugbyawltzcahjjjgnkid.supabase.co",
  SUPABASE_ANON_KEY: "TU_ANON_KEY",   // ← pega aquí tu anon key (Project Settings → API). Hasta entonces corre en MODO DEMO.
};

window.APP_CONFIG.DEMO_MODE =
  window.APP_CONFIG.SUPABASE_URL.includes("TU-PROYECTO") ||
  window.APP_CONFIG.SUPABASE_ANON_KEY === "TU_ANON_KEY";
