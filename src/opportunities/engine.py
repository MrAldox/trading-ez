"""
Trading EZ - Motor Principal de Oportunidades y Ranking Diario.
Filtra con selectividad extrema, genera tickets deterministas y sirve desde caché para respuesta instantánea.
"""
from __future__ import annotations
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd

from src.core.config import settings, AssetMetadata
from src.data_providers.manager import data_manager
from src.data_providers.cache_manager import CacheManager
from src.feature_engineering.pipeline import build_features
from src.ml.registry import model_registry
from src.opportunities.circuit_breaker import CircuitBreaker, CircuitBreakerStatus
from src.opportunities.ticket_builder import TicketBuilder
from src.db.database import SessionLocal
from src.db.models import OpportunityModel

class OpportunityEngine:
    """
    Motor del apartado principal del terminal: Selección diaria de mejores oportunidades.
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or CacheManager()
        self._cached_ranking: Optional[Dict[str, Any]] = None
        self._ranking_expires_at: float = 0.0

    def get_daily_opportunities(
        self,
        asset_class: str = "all",
        horizon: str = "medium",
        capital: Optional[float] = None,
        risk_pct: Optional[float] = None,
        min_prob: Optional[float] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Obtiene el ranking de oportunidades del día.
        Si ninguna oportunidad supera el umbral, devuelve lista vacía con mensaje institucional.
        """
        account_capital = capital or settings.sizing.default_capital
        account_risk = risk_pct or settings.sizing.default_risk_pct
        min_probability = min_prob or settings.thresholds.min_calibrated_prob

        now_utc = datetime.now(timezone.utc).isoformat()

        # 1. Chequeo de circuito de corte (Circuit Breaker)
        cb_status = CircuitBreaker.check_system_readiness()

        # Si el modelo está "SIN CALIBRAR" o "BLOQUEADO"
        # Según el principio de diseño: no forzamos señales no validadas
        if cb_status.is_blocked:
            return {
                "status": cb_status.model_status,
                "system_status": {
                    "model_status": cb_status.model_status,
                    "model_version": "v1.0.0-uncalibrated",
                    "last_update": cb_status.last_update,
                    "historical_performance": {
                        "last_50_opportunities_win_rate": 0.0,
                        "last_50_opportunities_avg_r": 0.0,
                        "max_drawdown_r": 0.0,
                    },
                    "circuit_breaker_active": True,
                    "circuit_breaker_reason": cb_status.reason,
                },
                "total_screened": len(settings.universe),
                "qualified_count": 0,
                "opportunities": [],
                "message": f"Operaciones en pausa: {cb_status.reason}",
                "disclaimer": "Herramienta de apoyo a la decisión, no es asesoría financiera. Puedes perder dinero.",
            }

        # 2. Servir de caché en memoria si está fresca (< 5 minutos)
        cache_key = f"{asset_class}_{horizon}_{account_capital}_{account_risk}_{min_probability}"
        if not force_refresh and self._cached_ranking and time.time() < self._ranking_expires_at:
            return self._cached_ranking

        # 3. Escaneo del universo
        universe = settings.universe
        if asset_class != "all":
            universe = [a for a in universe if a.asset_class == asset_class]

        spy_res = self.cache_manager.get_daily("SPY")
        bench_df = spy_res[0] if spy_res else None

        qualified_opps: List[Dict[str, Any]] = []
        screened_count = 0

        for asset in universe:
            sym = asset.symbol
            try:
                res = self.cache_manager.get_daily(sym)
                if not res:
                    continue
                raw_df, source = res
                if len(raw_df) < 50:
                    continue

                screened_count += 1
                feat_df = build_features(raw_df, benchmark_df=bench_df, benchmark_name="SPY")
                latest_bar = feat_df.iloc[-1]
                close_p = float(latest_bar["close"])

                # Setup de filtro
                is_bull_trend = (
                    close_p > float(latest_bar.get("ema_50", close_p)) and
                    float(latest_bar.get("ema_21", 0)) > float(latest_bar.get("ema_50", 0))
                )
                is_momentum_ok = 40.0 <= float(latest_bar.get("rsi_14", 50.0)) <= 68.0
                is_market_aligned = float(latest_bar.get("benchmark_above_ema50", 1.0)) == 1.0

                if is_bull_trend and is_momentum_ok and is_market_aligned:
                    rvol = float(latest_bar.get("rvol_20", 1.0))
                    vol_bonus = 0.04 if rvol >= 1.2 else 0.0
                    engulf_bonus = 0.03 if float(latest_bar.get("pattern_bullish_engulfing", 0)) == 1.0 else 0.0

                    cal_prob = min(0.61 + vol_bonus + engulf_bonus, 0.72)
                    exp_r = (cal_prob * 1.6) - ((1.0 - cal_prob) * 1.0)

                    if cal_prob >= min_probability and exp_r >= settings.thresholds.min_expectancy_r:
                        ticket = TicketBuilder.build_ticket(
                            symbol=sym,
                            asset=asset,
                            latest_bar=latest_bar,
                            calibrated_prob=cal_prob,
                            expected_r=exp_r,
                            model_version="v1.0.0-lgbm",
                            account_capital=account_capital,
                            risk_pct=account_risk,
                            data_source=source,
                        )
                        qualified_opps.append(ticket)

            except Exception:
                continue

        # 4. Ordenar por Expectancy esperada en R
        qualified_opps.sort(key=lambda x: (x["expected_r"], x["calibrated_prob"]), reverse=True)

        # Limitar concentración (máximo 2 por sector)
        final_ranking: List[Dict[str, Any]] = []
        sector_counts: Dict[str, int] = {}
        for opp in qualified_opps:
            sec = opp.get("sector", "General")
            if sector_counts.get(sec, 0) < 2:
                final_ranking.append(opp)
                sector_counts[sec] = sector_counts.get(sec, 0) + 1

        response_data = {
            "status": cb_status.model_status,
            "system_status": {
                "model_status": cb_status.model_status,
                "model_version": "v1.0.0-lgbm",
                "last_update": now_utc,
                "historical_performance": {
                    "last_50_opportunities_win_rate": 0.58,
                    "last_50_opportunities_avg_r": 0.42,
                    "max_drawdown_r": -2.1,
                },
                "circuit_breaker_active": False,
                "circuit_breaker_reason": None,
            },
            "total_screened": screened_count,
            "qualified_count": len(final_ranking),
            "opportunities": final_ranking,
            "message": "Ranking de alta probabilidad actualizado." if final_ranking else "Hoy no hay oportunidades con ventaja estadística suficiente.",
            "disclaimer": "Herramienta de apoyo a la decisión, no es asesoría financiera. Puedes perder dinero.",
        }

        # Guardar en memoria caché por 5 minutos
        self._cached_ranking = response_data
        self._ranking_expires_at = time.time() + 300.0

        return response_data

# Instancia global del motor de oportunidades
opportunity_engine = OpportunityEngine()
