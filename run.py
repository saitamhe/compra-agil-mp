#!/usr/bin/env python3
"""
Punto de entrada alternativo para desarrollo local.
Uso: python run.py [--scrape-now]
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Asegurar que el directorio raíz está en PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="CompraÁgil API")
    parser.add_argument(
        "--scrape-now",
        action="store_true",
        help="Ejecutar scraping inmediatamente y salir",
    )
    parser.add_argument(
        "--process-dir",
        type=str,
        default=None,
        help="Procesar todos los CSV en un directorio y salir",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Hot-reload (dev)")
    args = parser.parse_args()

    if args.scrape_now:
        from app.config import get_settings
        from app.database import init_db
        settings = get_settings()
        settings.ensure_dirs()
        init_db()

        async def _run():
            from app.scraper import run_scraper
            from app.processor import process_all
            files = await run_scraper()
            result = process_all(files)
            print(f"\nResultado: {result}")

        asyncio.run(_run())
        return

    if args.process_dir:
        from app.config import get_settings
        from app.database import init_db
        from app.processor import process_all
        settings = get_settings()
        settings.ensure_dirs()
        init_db()
        csv_files = list(Path(args.process_dir).glob("*.csv"))
        print(f"Procesando {len(csv_files)} archivos CSV...")
        result = process_all(csv_files)
        print(f"Resultado: {result}")
        return

    # Modo servidor
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
