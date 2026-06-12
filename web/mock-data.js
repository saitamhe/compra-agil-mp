// ============================================================
// DATOS DE EJEMPLO (modo demo)
// Estructura idéntica a las tablas de Supabase:
// opportunities + user_opportunities (unidas por "codigo").
// Las fechas de cierre se calculan relativas a "hoy" para que
// la cuenta regresiva siempre tenga sentido.
// ============================================================
(function () {
  const dias = (n) => {
    const d = new Date();
    d.setDate(d.getDate() + n);
    d.setHours(17, 0, 0, 0);
    return d.toISOString();
  };
  const mesAtras = (n, dia) => {
    const d = new Date();
    d.setMonth(d.getMonth() - n, dia);
    return d.toISOString();
  };

  // --- Perfil y configuración del usuario demo -------------
  window.MOCK_PROFILE = {
    id: "demo-user",
    email: "contacto@aseototal.cl",
    nombre_empresa: "Aseo Total SpA",
  };

  window.MOCK_CONFIG = {
    user_id: "demo-user",
    que_vende:
      "Vendemos artículos de aseo e higiene: papel higiénico, toallas de papel, detergentes, cloro, bolsas de basura y dispensadores. También insumos de oficina básicos.",
    rubros: ["Artículos de aseo e higiene", "Insumos de oficina"],
    regiones: ["Región Metropolitana", "Valparaíso", "O'Higgins"],
    monto_min: 300000,
    monto_max: 6000000,
    score_minimo: 40,
    modelo: "estandar",
    activo: true,
    system_message: "",
  };

  // --- Oportunidades (tabla opportunities) -----------------
  // user_opportunities va embebido bajo "ua" para simplificar el mock.
  window.MOCK_OPPORTUNITIES = [
    {
      codigo: "1057-2026-COT26",
      nombre: "Adquisición de artículos de aseo para dependencias municipales",
      organismo: "Municipalidad de Puente Alto",
      region: "Región Metropolitana",
      monto_clp: 2480000,
      fecha_cierre: dias(2),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 92,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "Piden papel higiénico, toallas de papel y detergente para 4 edificios municipales. Es exactamente lo que vendes y el monto está dentro de tu rango.",
        justificacion:
          "Coincide con tu rubro principal (artículos de aseo), la región es la tuya y el organismo publica compras similares todos los meses. El detalle pide marcas \"o equivalentes\", así que puedes ofrecer tu línea habitual.",
        riesgo:
          "Cierra en pocos días: deja tu cotización lista con anticipación. Piden despacho en 5 días hábiles.",
        precio_sugerido_clp: 2300000,
        estado_seguimiento: "pendiente",
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "2239-2026-COT26",
      nombre: "Compra de bolsas de basura industriales 240 litros",
      organismo: "Hospital Sótero del Río",
      region: "Región Metropolitana",
      monto_clp: 1850000,
      fecha_cierre: dias(4),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 88,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "Hospital necesita 500 paquetes de bolsas industriales. Producto que ya tienes en catálogo, entrega en un solo punto.",
        justificacion:
          "Producto estándar de tu catálogo, sin requisitos técnicos especiales. Los hospitales pagan a 30 días vía plataforma, historial de pago correcto.",
        riesgo:
          "Exigen ficha técnica del producto adjunta. Si no la adjuntas, descartan la oferta.",
        precio_sugerido_clp: 1700000,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "3811-2026-COT26",
      nombre: "Insumos de oficina: resmas, archivadores y tóner",
      organismo: "SERVIU Región de Valparaíso",
      region: "Valparaíso",
      monto_clp: 3200000,
      fecha_cierre: dias(6),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 74,
        viabilidad: "Media",
        accion: "investigar",
        resumen:
          "Mezcla de papelería (que vendes) con tóner específico de impresoras HP (que tendrías que conseguir con un distribuidor).",
        justificacion:
          "El 60% del monto es papelería que manejas bien. El resto es tóner original: revisa si tu distribuidor te da buen precio antes de cotizar.",
        riesgo:
          "Si cotizas el tóner muy caro, pierdes contra papelerías especializadas. Evalúa cotizar solo si consigues el tóner a precio competitivo.",
        precio_sugerido_clp: 2950000,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "1182-2026-COT26",
      nombre: "Kit de útiles de aseo personal para programas sociales",
      organismo: "Municipalidad de Rancagua",
      region: "O'Higgins",
      monto_clp: 4100000,
      fecha_cierre: dias(8),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 81,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "Armado de 800 kits con jabón, shampoo, pasta y cepillo de dientes. Tienes los productos; el armado del kit es trabajo extra simple.",
        justificacion:
          "Todos los productos están en tu rubro. El armado de kits agrega trabajo, pero también margen: pocos competidores quieren hacerlo.",
        riesgo:
          "Entrega en Rancagua: considera el costo de flete en tu precio.",
        precio_sugerido_clp: 3800000,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "4520-2026-COT26",
      nombre: "Servicio de sanitización de oficinas (6 meses)",
      organismo: "Dirección del Trabajo, Valparaíso",
      region: "Valparaíso",
      monto_clp: 5600000,
      fecha_cierre: dias(3),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 55,
        viabilidad: "Baja",
        accion: "ignorar",
        resumen:
          "Es un SERVICIO de sanitización con personal en terreno, no venta de productos. Necesitarías personal certificado que hoy no tienes.",
        justificacion:
          "Tu negocio vende productos, no servicios. Exigen certificación SEREMI de Salud para aplicadores y experiencia previa comprobable.",
        riesgo:
          "Alto: sin la certificación, la oferta queda fuera de bases. No conviene invertir tiempo aquí.",
        precio_sugerido_clp: null,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "2877-2026-COT26",
      nombre: "Dispensadores de alcohol gel y repuestos",
      organismo: "JUNAEB Dirección Regional RM",
      region: "Región Metropolitana",
      monto_clp: 990000,
      fecha_cierre: dias(5),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 85,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "30 dispensadores de pedestal y 60 bidones de alcohol gel para escuelas. Producto de tu catálogo, monto chico pero margen sano.",
        justificacion:
          "Vendes dispensadores y alcohol gel. JUNAEB compra seguido: ganar esta abre la puerta a compras repetidas.",
        riesgo:
          "Bajo. Solo cuida que el dispensador cumpla la capacidad mínima (1 litro) que piden.",
        precio_sugerido_clp: 920000,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "1633-2026-COT26",
      nombre: "Adquisición de equipos de radiocomunicación VHF",
      organismo: "Municipalidad de Quilpué",
      region: "Valparaíso",
      monto_clp: 4800000,
      fecha_cierre: dias(7),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 22,
        viabilidad: "Muy baja",
        accion: "ignorar",
        resumen:
          "Equipos de radio para seguridad municipal. Nada que ver con tu rubro.",
        justificacion:
          "Fuera de tus rubros (aseo y oficina). Requiere proveedor especializado en telecomunicaciones con soporte técnico.",
        riesgo: "No aplica: se sugiere ignorar.",
        precio_sugerido_clp: null,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "3045-2026-COT26",
      nombre: "Toallas de papel interfoliadas para baños públicos",
      organismo: "Municipalidad de Viña del Mar",
      region: "Valparaíso",
      monto_clp: 1320000,
      fecha_cierre: dias(1),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 90,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "600 paquetes de toallas interfoliadas, entrega única en bodega municipal. Producto que tienes en stock.",
        justificacion:
          "Coincidencia exacta con tu catálogo. Compra simple, un solo producto, una sola entrega.",
        riesgo:
          "¡Cierra mañana! Si te interesa, cotiza hoy mismo.",
        precio_sugerido_clp: 1240000,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "2210-2026-COT26",
      nombre: "Cloro gel y desengrasante industrial para casino",
      organismo: "Gendarmería de Chile, RM",
      region: "Región Metropolitana",
      monto_clp: 760000,
      fecha_cierre: dias(9),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 68,
        viabilidad: "Media",
        accion: "investigar",
        resumen:
          "Productos químicos de aseo que manejas, pero piden resolución sanitaria del fabricante y hoja de seguridad por producto.",
        justificacion:
          "Los productos calzan con tu rubro. El papeleo extra (hojas de seguridad) es manejable si tu proveedor te las entrega.",
        riesgo:
          "Si no adjuntas las hojas de seguridad, la oferta queda descartada automáticamente.",
        precio_sugerido_clp: 690000,
        estado_seguimiento: null,
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    // --- Ya en seguimiento (pueblan el Kanban y Ganancias) ---
    {
      codigo: "1499-2026-COT26",
      nombre: "Papel higiénico institucional jumbo 550 m",
      organismo: "Municipalidad de Maipú",
      region: "Región Metropolitana",
      monto_clp: 2150000,
      fecha_cierre: dias(5),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 89,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "400 rollos jumbo para dependencias municipales. Producto estrella de tu catálogo.",
        justificacion:
          "Coincidencia total con tu rubro y región. Compra recurrente del organismo.",
        riesgo: "Bajo. Competencia alta en este producto: afina el precio.",
        precio_sugerido_clp: 1980000,
        estado_seguimiento: "cotizando",
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "1875-2026-COT26",
      nombre: "Detergente y lavalozas para jardines infantiles",
      organismo: "Fundación Integra, Valparaíso",
      region: "Valparaíso",
      monto_clp: 1480000,
      fecha_cierre: dias(2),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 84,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen:
          "Productos de limpieza de cocina para 12 jardines infantiles, entrega en un centro de acopio.",
        justificacion: "Productos de tu catálogo, entrega única, organismo confiable.",
        riesgo: "Bajo.",
        precio_sugerido_clp: 1390000,
        estado_seguimiento: "enviada",
        monto_ganado: null,
        fecha_resultado: null,
      },
    },
    {
      codigo: "0922-2026-COT26",
      nombre: "Artículos de aseo para oficinas SERVIU RM",
      organismo: "SERVIU Metropolitano",
      region: "Región Metropolitana",
      monto_clp: 1900000,
      fecha_cierre: mesAtras(1, 12),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 91,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen: "Compra mensual de artículos de aseo para oficinas centrales.",
        justificacion: "Coincidencia total con catálogo.",
        riesgo: "Bajo.",
        precio_sugerido_clp: 1800000,
        estado_seguimiento: "ganada",
        monto_ganado: 1780000,
        fecha_resultado: mesAtras(1, 20),
      },
    },
    {
      codigo: "0781-2026-COT26",
      nombre: "Bolsas y guantes de aseo para áreas verdes",
      organismo: "Municipalidad de San Bernardo",
      region: "Región Metropolitana",
      monto_clp: 850000,
      fecha_cierre: mesAtras(2, 5),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 86,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen: "Insumos para cuadrillas de áreas verdes.",
        justificacion: "Productos básicos de catálogo.",
        riesgo: "Bajo.",
        precio_sugerido_clp: 800000,
        estado_seguimiento: "ganada",
        monto_ganado: 795000,
        fecha_resultado: mesAtras(2, 15),
      },
    },
    {
      codigo: "0655-2026-COT26",
      nombre: "Insumos de oficina segundo semestre",
      organismo: "Municipalidad de Valparaíso",
      region: "Valparaíso",
      monto_clp: 2600000,
      fecha_cierre: mesAtras(1, 3),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 78,
        viabilidad: "Media",
        accion: "cotizar",
        resumen: "Papelería y archivadores para oficinas municipales.",
        justificacion: "Rubro secundario tuyo; competencia fuerte.",
        riesgo: "Competencia de papelerías locales.",
        precio_sugerido_clp: 2400000,
        estado_seguimiento: "perdida",
        monto_ganado: null,
        fecha_resultado: mesAtras(1, 10),
      },
    },
    {
      codigo: "0510-2026-COT26",
      nombre: "Alcohol gel y mascarillas para CESFAM",
      organismo: "Municipalidad de Quillota",
      region: "Valparaíso",
      monto_clp: 1150000,
      fecha_cierre: mesAtras(3, 8),
      url_mp: "https://www.mercadopublico.cl/",
      ua: {
        score: 83,
        viabilidad: "Alta",
        accion: "cotizar",
        resumen: "Insumos de higiene para centros de salud familiar.",
        justificacion: "Productos de catálogo.",
        riesgo: "Bajo.",
        precio_sugerido_clp: 1080000,
        estado_seguimiento: "ganada",
        monto_ganado: 1065000,
        fecha_resultado: mesAtras(3, 18),
      },
    },
  ];

  // --- Cotizaciones guardadas (tabla quotes) ----------------
  window.MOCK_QUOTES = [
    {
      id: "q-demo-1",
      codigo: "1499-2026-COT26",
      descripcion: "400 rollos jumbo 550 m, marca propia",
      costo_neto: 1320000,
      precio_venta_neto: 1980000,
      iva_pct: 19,
      created_at: dias(-1),
    },
  ];

  // Regiones disponibles para filtros y onboarding
  window.REGIONES_CL = [
    "Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
    "Valparaíso", "Región Metropolitana", "O'Higgins", "Maule", "Ñuble",
    "Biobío", "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
  ];

  window.RUBROS_CL = [
    "Artículos de aseo e higiene", "Insumos de oficina", "Alimentos y abarrotes",
    "Ferretería y construcción", "Computación y tecnología", "Mobiliario",
    "Vestuario y calzado", "Imprenta y publicidad", "Servicios de aseo",
    "Servicios de capacitación", "Otro",
  ];
})();
