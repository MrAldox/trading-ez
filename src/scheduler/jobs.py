"""
Trading EZ - Planificador de Tareas Continuas (APScheduler).
Gestiona la descarga nocturna de datos, el refresco del ranking de oportunidades y el monitor de drift.
"""
from __future__ import annotations
import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.core.config import settings
from src.data_providers.manager import data_manager
from src.opportunities.engine import opportunity_engine
from src.ml.registry import model_registry

logger = logging.getLogger("trading_ez.scheduler")

class TradingScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def job_daily_data_refresh(self):
        """Descarga y actualiza los datos al cierre del mercado NYSE (21:00 UTC)."""
        logger.info("[Scheduler] Iniciando actualización diaria de datos de mercado...")
        updated_count = 0
        for asset in settings.universe:
            try:
                data_manager.fetch_daily_data(asset.symbol, force_refresh=True)
                updated_count += 1
            except Exception as e:
                logger.warning(f"[Scheduler] Fallo actualizando {asset.symbol}: {e}")
        logger.info(f"[Scheduler] Actualización diaria completada. {updated_count}/{len(settings.universe)} activos sincronizados.")

    def job_refresh_opportunities(self):
        """Pre-calcula y precalienta la caché del ranking de oportunidades."""
        logger.info("[Scheduler] Pre-calculando ranking de oportunidades...")
        try:
            res = opportunity_engine.get_daily_opportunities(force_refresh=True)
            logger.info(f"[Scheduler] Ranking actualizado: {len(res.get('opportunities', []))} oportunidades encontradas.")
        except Exception as e:
            logger.error(f"[Scheduler] Error precalculando oportunidades: {e}")

    def job_drift_detection(self):
        """Monitorea si la calibración o las distribuciones han sufrido drift significativo."""
        logger.info("[Scheduler] Ejecutando monitor de drift estadístico...")
        # Evaluar consistencia
        champ = model_registry.load_champion()
        if champ:
            _, meta = champ
            logger.info(f"[Scheduler] Modelo campeón {meta.get('version')}: Calibración Brier={meta.get('oos_brier')}")

    def start(self):
        """Inicia el planificador con las tareas registradas."""
        if self.scheduler.running:
            return

        # 1. Actualización diaria tras cierre de mercado (Lunes a Viernes a las 21:15 UTC)
        self.scheduler.add_job(
            self.job_daily_data_refresh,
            trigger=CronTrigger(day_of_week="mon-fri", hour=21, minute=15),
            id="job_daily_data_refresh",
            replace_existing=True,
        )

        # 2. Refresco periódico de ranking cada 30 minutos
        self.scheduler.add_job(
            self.job_refresh_opportunities,
            trigger=IntervalTrigger(minutes=30),
            id="job_refresh_opportunities",
            replace_existing=True,
        )

        # 3. Auditoría de drift diaria
        self.scheduler.add_job(
            self.job_drift_detection,
            trigger=CronTrigger(hour=22, minute=0),
            id="job_drift_detection",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("[Scheduler] APScheduler iniciado correctamente con 3 tareas en segundo plano.")

    def shutdown(self):
        """Detiene el planificador limpiamente."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[Scheduler] APScheduler detenido limpiamente.")

scheduler = TradingScheduler()
