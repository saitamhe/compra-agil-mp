"""
Script de diagnóstico: vuelca la estructura real de la página de ChileCompra.
Uso: docker exec compra-agil-api python3 /app/diagnose.py
"""
import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://datos-abiertos.chilecompra.cl/descargas/compra-agil"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print(f"\n=== Navegando a {URL} ===")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # Screenshot completo
        await page.screenshot(path="/app/data/downloads/_diag_full.png", full_page=True)
        print("Screenshot guardado en data/downloads/_diag_full.png")

        # HTML completo
        html = await page.content()
        with open("/app/data/downloads/_diag_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML guardado ({len(html)} chars) en data/downloads/_diag_page.html")

        # Todos los links
        print("\n=== TODOS LOS <a> ===")
        links = await page.query_selector_all("a")
        for link in links:
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).strip()[:60]
            cls = await link.get_attribute("class") or ""
            if href or text:
                print(f"  href={href!r:50} text={text!r:40} class={cls[:30]!r}")

        # Todos los botones
        print("\n=== TODOS LOS <button> ===")
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            text = (await btn.inner_text()).strip()[:60]
            cls = await btn.get_attribute("class") or ""
            aria = await btn.get_attribute("aria-label") or ""
            data = await btn.get_attribute("data-region") or await btn.get_attribute("data-id") or ""
            print(f"  text={text!r:40} aria={aria!r:30} class={cls[:30]!r} data={data!r}")

        # Selects
        print("\n=== TODOS LOS <select> ===")
        selects = await page.query_selector_all("select")
        for sel in selects:
            name = await sel.get_attribute("name") or ""
            id_ = await sel.get_attribute("id") or ""
            opts = await sel.query_selector_all("option")
            opt_texts = [(await o.inner_text()).strip() for o in opts[:5]]
            print(f"  name={name!r} id={id_!r} opciones={opt_texts}")

        # Inputs
        print("\n=== INPUTS ===")
        inputs = await page.query_selector_all("input")
        for inp in inputs:
            t = await inp.get_attribute("type") or "text"
            name = await inp.get_attribute("name") or ""
            placeholder = await inp.get_attribute("placeholder") or ""
            print(f"  type={t!r} name={name!r} placeholder={placeholder!r}")

        # Texto de la página (para ver qué hay)
        print("\n=== TEXTO VISIBLE (primeros 2000 chars) ===")
        body_text = await page.evaluate("() => document.body.innerText")
        print(body_text[:2000])

        # Elementos con "region" o "descarg" en cualquier atributo
        print("\n=== ELEMENTOS CON 'region' O 'descarg' EN ATRIBUTOS ===")
        elements = await page.query_selector_all("[class*='region'],[class*='Region'],[id*='region'],[data-region],[href*='region'],[href*='descarg']")
        for el in elements[:20]:
            tag = await el.evaluate("el => el.tagName")
            attrs = await el.evaluate("el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))")
            text = (await el.inner_text()).strip()[:50]
            print(f"  <{tag.lower()}> text={text!r} attrs={json.dumps(attrs)[:120]}")

        await browser.close()
        print("\n=== DIAGNÓSTICO COMPLETO ===")

asyncio.run(main())
