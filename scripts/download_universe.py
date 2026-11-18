"""
Trading EZ - Script de Descarga y Auditoría del Universo de Activos (5+ Años).
Descarga series diarias completas, audita integridad, almacena en Parquet y genera reporte.
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Asegurar que el directorio raíz esté en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.core.config import settings
from src.data_providers.manager import data_manager

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    print("=" * 70)
    print("  TRADING EZ - DESCARGA Y AUDITORIA DE DATOS HISTORICOS (5+ ANOS)")
    print("=" * 70)

    universe = settings.universe
    print(f"Total de activos en universo: {len(universe)}")
    print(f"Directorio de cache Parquet: {settings.data.cache_dir}/daily")

    # Descarga desde hace 5 anos y 3 meses para tener suficiente margen
    start_date = datetime.now() - timedelta(days=5 * 365 + 90)
    print(f"Fecha de inicio: {start_date.strftime('%Y-%m-%d')}\n")

    success_count = 0
    failed_count = 0

    print(f"{'Simbolo':<10} {'Clase':<12} {'Barras':<8} {'Fuente':<8} {'Rango Fechas':<24} {'Estado'}")
    print("-" * 75)

    for asset in universe:
        sym = asset.symbol
        try:
            df, source, report = data_manager.fetch_daily_data(
                symbol=sym,
                start_date=start_date,
                force_refresh=False,
            )

            date_range = f"{df.index[0].strftime('%Y-%m-%d')} a {df.index[-1].strftime('%Y-%m-%d')}" if not df.empty else "N/A"
            status = "OK" if report.is_valid else "CORRUPTO"

            print(f"{sym:<10} {asset.asset_class:<12} {len(df):<8} {source:<8} {date_range:<24} {status}")

            if report.warnings:
                for w in report.warnings[:1]:
                    print(f"    -> Aviso: {w}")

            if report.repaired_rows_dropped > 0:
                print(f"    -> Reparado: {report.repaired_rows_dropped} filas descartadas por anomalias")

            success_count += 1

        except Exception as e:
            failed_count += 1
            print(f"{sym:<10} {asset.asset_class:<12} {'0':<8} {'ERROR':<8} {'N/A':<24} ERROR: {str(e)[:30]}")

    print("-" * 75)
    print(f"Resumen: {success_count} descargados/validados con éxito, {failed_count} con error.")
    print("=" * 70)

if __name__ == "__main__":
    main()
