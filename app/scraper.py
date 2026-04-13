"""
Scraper con Playwright para https://datos-abiertos.chilecompra.cl/descargas/compra-agil

Estrategia:
1. Navega a la página y espera carga completa
2. Detecta el selector de región (dropdown, lista, botones)
3. Para cada región: selecciona → descarga el CSV
4. Devuelve lista de rutas descargadas
"""
import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright, Browser, BrowserContext, Page,
    Download, TimeoutError as PlaywrightTimeout
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Regiones oficiales de Chile con sus posibles nombres en el selector
REGIONES_CHILE = [
    "Arica y Parinacota",
    "Tarapacá",
    "Antofagasta",
    "Atacama",
    "Coquimbo",
    "Valparaíso",
    "Metropolitana de Santiago",
    "Libertador General Bernardo O'Higgins",
    "Maule",
    "Ñuble",
    "Biobío",
    "La Araucanía",
    "Los Ríos",
    "Los Lagos",
    "Aysén del General Carlos Ibáñez del Campo",
    "Magallanes y de la Antártica Chilena",
]


class ScraperError(Exception):
    pass


class CompraAgilScraper:
    def __init__(self):
        self.downloads_dir = Path(settings.downloads_dir)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = settings.scraper_timeout_ms
        self.download_wait = settings.scraper_download_wait_s
        self._browser: Optional[Browser] = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.scraper_headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,900",
            ],
        )
        return self

    async def __aexit__(self, *_):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    async def scrape_all_regions(self) -> list[Path]:
        """
        Descarga CSV de todas las regiones.
        Retorna lista de rutas de archivos descargados.
        """
        logger.info("Iniciando scraping de todas las regiones")
        downloaded: list[Path] = []
        errors: list[str] = []

        context = await self._new_context()
        page = await context.new_page()

        try:
            # Navegar y analizar la página
            await self._navigate(page)
            page_info = await self._analyze_page(page)
            logger.info("Análisis de página: %s", page_info)

            # Obtener lista de regiones disponibles
            regiones = await self._get_available_regions(page, page_info)
            logger.info("Regiones encontradas: %d → %s", len(regiones), regiones)

            if not regiones:
                raise ScraperError("No se encontraron regiones en la página")

            # Descargar por región
            for region in regiones:
                try:
                    path = await self._download_region(page, region, page_info)
                    if path:
                        downloaded.append(path)
                        logger.info("✓ Descargado: %s → %s", region, path.name)
                    await asyncio.sleep(2)  # pausa entre requests
                except Exception as exc:
                    msg = f"Error región '{region}': {exc}"
                    logger.error(msg)
                    errors.append(msg)

        finally:
            await context.close()

        if errors:
            logger.warning("Errores parciales (%d): %s", len(errors), "; ".join(errors))

        logger.info("Scraping completado: %d archivos descargados", len(downloaded))
        return downloaded

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    async def _new_context(self) -> BrowserContext:
        tmp_dir = self.downloads_dir / f"_tmp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        context = await self._browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
            locale="es-CL",
            timezone_id="America/Santiago",
        )
        # Almacena dir temporal en contexto para recuperarlo al procesar descargas
        context._tmp_dir = tmp_dir  # type: ignore[attr-defined]
        return context

    async def _navigate(self, page: Page):
        logger.info("Navegando a %s", settings.scraper_base_url)
        await page.goto(settings.scraper_base_url, timeout=self.timeout, wait_until="networkidle")
        # Espera adicional para frameworks JS lentos
        await page.wait_for_timeout(3000)
        # Tomar screenshot de diagnóstico
        shot_path = self.downloads_dir / "_diagnostico_pagina.png"
        await page.screenshot(path=str(shot_path), full_page=True)
        logger.info("Screenshot guardado en %s", shot_path)

    # ------------------------------------------------------------------
    # Análisis de estructura de página
    # ------------------------------------------------------------------

    async def _analyze_page(self, page: Page) -> dict:
        """Detecta qué controles UI existen en la página."""
        info = {}

        # ¿Hay un <select> de regiones?
        selects = await page.query_selector_all("select")
        info["selects"] = len(selects)

        for sel in selects:
            aria = await sel.get_attribute("aria-label") or ""
            name = await sel.get_attribute("name") or ""
            id_ = await sel.get_attribute("id") or ""
            if any(k in (aria + name + id_).lower() for k in ["region", "región"]):
                info["region_select"] = True
                info["region_select_selector"] = f"select[name='{name}']" if name else f"select#{id_}" if id_ else "select"
                break

        # ¿Hay inputs de fecha?
        date_inputs = await page.query_selector_all("input[type='date'], input[type='text'][class*='date'], input[placeholder*='echa']")
        info["date_inputs"] = len(date_inputs)

        # ¿Hay botones de descarga?
        download_btns = await page.query_selector_all(
            "button, a.btn, a[href*='download'], a[href*='csv'], a[href*='descarga']"
        )
        info["download_buttons"] = len(download_btns)

        # ¿Hay checkboxes de región?
        checkboxes = await page.query_selector_all("input[type='checkbox']")
        info["checkboxes"] = len(checkboxes)

        # Buscar contenedores de filtros por texto
        try:
            region_label = await page.query_selector("label:has-text('Región'), label:has-text('Region'), span:has-text('Región')")
            info["region_label_found"] = region_label is not None
        except Exception:
            info["region_label_found"] = False

        # Textos de botones de descarga
        btn_texts = []
        for btn in await page.query_selector_all("button, a.btn"):
            t = await btn.inner_text()
            if any(k in t.lower() for k in ["descarg", "export", "csv", "download"]):
                btn_texts.append(t.strip())
        info["download_btn_texts"] = btn_texts[:5]

        return info

    # ------------------------------------------------------------------
    # Detección de regiones
    # ------------------------------------------------------------------

    async def _get_available_regions(self, page: Page, page_info: dict) -> list[str]:
        """Retorna lista de regiones disponibles en el selector."""
        regions = []

        # Estrategia 1: <select> con nombre/id que contiene "region"
        if page_info.get("region_select"):
            sel_css = page_info["region_select_selector"]
            options = await page.query_selector_all(f"{sel_css} option")
            for opt in options:
                val = await opt.get_attribute("value") or ""
                text = await opt.inner_text()
                if val and val not in ("", "0", "all", "todas"):
                    regions.append(text.strip())
            if regions:
                return regions

        # Estrategia 2: cualquier <select> con opciones que suenen a región
        for sel in await page.query_selector_all("select"):
            options = await page.query_selector_all_in_focused_frame(f"option") if False else \
                await sel.query_selector_all("option")
            texts = [await o.inner_text() for o in options]
            if any(
                any(r_part in t for r_part in ["Arica", "Tarapacá", "Antofagasta", "Valparaíso", "Metropolitana", "Maule", "Biobío"])
                for t in texts
            ):
                regions = [t.strip() for t in texts if t.strip() and t.strip().lower() not in ("seleccione", "todos", "todas", "")]
                if regions:
                    return regions

        # Estrategia 3: botones/links con nombre de región
        for link in await page.query_selector_all("a, button, li"):
            text = await link.inner_text()
            text = text.strip()
            if any(r.lower() in text.lower() for r in ["Arica", "Antofagasta", "Valparaíso", "Metropolitana", "Maule"]):
                if text not in regions and len(text) < 80:
                    regions.append(text)

        if regions:
            return regions

        # Fallback: usar lista hardcoded e intentar con todas
        logger.warning("No se detectaron regiones automáticamente, usando lista predefinida")
        return REGIONES_CHILE

    # ------------------------------------------------------------------
    # Descarga por región
    # ------------------------------------------------------------------

    async def _download_region(self, page: Page, region: str, page_info: dict) -> Optional[Path]:
        """Selecciona una región y descarga su CSV."""
        logger.info("Procesando región: %s", region)

        # Seleccionar región en el dropdown
        await self._select_region(page, region, page_info)
        await page.wait_for_timeout(1500)

        # Configurar rango de fechas si hay controles de fecha
        if page_info.get("date_inputs", 0) > 0:
            await self._set_date_range(page)
            await page.wait_for_timeout(1000)

        # Hacer click en "Descargar" / "Exportar"
        path = await self._click_download(page, region)
        return path

    async def _select_region(self, page: Page, region: str, page_info: dict):
        """Selecciona la región en el control disponible."""
        # Estrategia 1: <select>
        if page_info.get("region_select"):
            sel_css = page_info["region_select_selector"]
            try:
                # Intenta por label o valor parcial
                await page.select_option(sel_css, label=region)
                return
            except Exception:
                pass
            # Busca opción cuyo texto contenga la región
            options = await page.query_selector_all(f"{sel_css} option")
            for opt in options:
                text = await opt.inner_text()
                if region.lower()[:8] in text.lower():
                    val = await opt.get_attribute("value")
                    await page.select_option(sel_css, value=val)
                    return

        # Estrategia 2: cualquier <select>
        for sel in await page.query_selector_all("select"):
            options = await sel.query_selector_all("option")
            for opt in options:
                text = await opt.inner_text()
                if region.lower()[:8] in text.lower():
                    val = await opt.get_attribute("value")
                    sel_id = await sel.get_attribute("id")
                    sel_name = await sel.get_attribute("name")
                    css = f"select#{sel_id}" if sel_id else f"select[name='{sel_name}']" if sel_name else "select"
                    await page.select_option(css, value=val)
                    return

        # Estrategia 3: click en botón/link con nombre de región
        for link in await page.query_selector_all("a, button, li"):
            text = await link.inner_text()
            if region.lower()[:8] in text.lower():
                await link.click()
                await page.wait_for_timeout(500)
                return

        logger.warning("No se pudo seleccionar la región '%s', continuando de todas formas", region)

    async def _set_date_range(self, page: Page):
        """Configura el rango de fechas al período más reciente disponible."""
        # Fecha fin = hoy, fecha inicio = hace 2 horas (o inicio del día)
        now = datetime.now()
        fecha_fin = now.strftime("%d/%m/%Y")
        fecha_inicio = (now - timedelta(hours=2)).strftime("%d/%m/%Y")

        date_selectors = [
            "input[type='date']",
            "input[placeholder*='nicio']",
            "input[placeholder*='inicio']",
            "input[placeholder*='Inicio']",
        ]
        fin_selectors = [
            "input[placeholder*='in']",
            "input[placeholder*='In']",
            "input[placeholder*='Fin']",
        ]

        # Intentar setear fecha inicio
        for css in date_selectors:
            inputs = await page.query_selector_all(css)
            if inputs:
                try:
                    await inputs[0].fill(fecha_inicio)
                except Exception:
                    pass
                if len(inputs) > 1:
                    try:
                        await inputs[1].fill(fecha_fin)
                    except Exception:
                        pass
                return

        # Alternativa con inputs de texto con placeholder
        all_inputs = await page.query_selector_all("input[type='text']")
        date_inputs = []
        for inp in all_inputs:
            ph = await inp.get_attribute("placeholder") or ""
            if any(k in ph.lower() for k in ["fecha", "date", "desde", "hasta", "inicio", "fin"]):
                date_inputs.append(inp)

        if len(date_inputs) >= 2:
            try:
                await date_inputs[0].triple_click()
                await date_inputs[0].type(fecha_inicio)
                await date_inputs[1].triple_click()
                await date_inputs[1].type(fecha_fin)
            except Exception as exc:
                logger.debug("Error seteando fechas: %s", exc)

    async def _click_download(self, page: Page, region: str) -> Optional[Path]:
        """Encuentra y hace click en el botón de descarga, espera el archivo."""
        download_keywords = ["descarg", "export", "csv", "download", "generar"]

        # Buscar botón
        candidates = []
        for btn in await page.query_selector_all("button, a.btn, input[type='button'], input[type='submit']"):
            text = (await btn.inner_text()).lower()
            if any(k in text for k in download_keywords):
                candidates.append(btn)

        # También buscar links directos a CSV
        for link in await page.query_selector_all("a[href*='.csv'], a[href*='download'], a[href*='export']"):
            candidates.append(link)

        if not candidates:
            # último recurso: cualquier botón visible
            for btn in await page.query_selector_all("button:visible, .btn:visible"):
                text = (await btn.inner_text()).lower()
                if text and not any(k in text for k in ["menu", "nav", "login", "salir"]):
                    candidates.append(btn)

        if not candidates:
            logger.error("No se encontró botón de descarga para región '%s'", region)
            return None

        # Hacer click y esperar descarga
        btn = candidates[0]
        try:
            async with page.expect_download(timeout=self.download_wait * 1000) as dl_info:
                await btn.click()
            download: Download = await dl_info.value

            # Guardar con nombre descriptivo
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            region_slug = region.replace(" ", "_").replace("'", "").replace("/", "-")[:40]
            filename = f"{region_slug}_{ts}.csv"
            dest = self.downloads_dir / filename
            await download.save_as(str(dest))

            if dest.exists() and dest.stat().st_size > 0:
                return dest
            else:
                logger.warning("Archivo descargado vacío para región '%s'", region)
                return None

        except PlaywrightTimeout:
            logger.error("Timeout esperando descarga para región '%s'", region)
            return None
        except Exception as exc:
            logger.error("Error descargando región '%s': %s", region, exc)
            return None


# ---------------------------------------------------------------------------
# Función pública para usar en el scheduler
# ---------------------------------------------------------------------------

async def run_scraper() -> list[Path]:
    """Punto de entrada principal del scraper."""
    async with CompraAgilScraper() as scraper:
        return await scraper.scrape_all_regions()
