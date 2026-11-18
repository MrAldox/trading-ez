"""
Trading EZ - Router de Escáner Técnico Multicriterio.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query

from src.core.config import settings
from src.data_providers.cache_manager import CacheManager
from src.feature_engineering.pipeline import build_features

router = APIRouter(prefix="/api/screener", tags=["Escáner"])
cache_mgr = CacheManager()

@router.get("")
def run_screener(
    rsi_max: Optional[float] = Query(None, description="RSI máximo (ej. 30 para sobreventa)"),
    rsi_min: Optional[float] = Query(None, description="RSI mínimo (ej. 70 para sobrecompra)"),
    rvol_min: Optional[float] = Query(None, description="Volumen relativo mínimo (ej. 1.5)"),
    above_ema50: Optional[bool] = Query(None, description="Filtrar precio sobre EMA 50"),
    above_ema200: Optional[bool] = Query(None, description="Filtrar precio sobre EMA 200 (Tendencia secular)"),
    golden_cross: Optional[bool] = Query(None, description="Cruce dorado EMA 50 > EMA 200"),
    bb_squeeze: Optional[bool] = Query(None, description="Compresión de Bollinger Squeeze"),
    hammer: Optional[bool] = Query(None, description="Patrón de vela martillo alcista"),
    engulfing: Optional[bool] = Query(None, description="Patrón envolvente alcista"),
):
    """Escanea el universo de activos en tiempo real aplicando filtros combinables."""
    results = []
    spy_res = cache_mgr.get_daily("SPY")
    bench = spy_res[0] if spy_res else None

    for asset in settings.universe:
        sym = asset.symbol
        res = cache_mgr.get_daily(sym)
        if not res:
            continue
        df, _ = res
        if len(df) < 50:
            continue

        feat_df = build_features(df, benchmark_df=bench)
        bar = feat_df.iloc[-1]
        close_p = float(bar["close"])

        # Aplicar filtros
        rsi_val = float(bar.get("rsi_14", 50.0))
        if rsi_max is not None and rsi_val > rsi_max:
            continue
        if rsi_min is not None and rsi_val < rsi_min:
            continue

        rvol_val = float(bar.get("rvol_20", 1.0))
        if rvol_min is not None and rvol_val < rvol_min:
            continue

        if above_ema50 is True and close_p <= float(bar.get("ema_50", close_p)):
            continue
        if above_ema200 is True and close_p <= float(bar.get("ema_200", close_p)):
            continue
        if golden_cross is True and float(bar.get("ema_50_above_200", 0)) != 1.0:
            continue
        if bb_squeeze is True and float(bar.get("bb_squeeze", 0)) != 1.0:
            continue
        if hammer is True and float(bar.get("pattern_hammer", 0)) != 1.0:
            continue
        if engulfing is True and float(bar.get("pattern_bullish_engulfing", 0)) != 1.0:
            continue

        results.append({
            "symbol": sym,
            "name": asset.name,
            "asset_class": asset.asset_class,
            "sector": asset.sector,
            "close": round(close_p, 2),
            "rsi_14": round(rsi_val, 1),
            "rvol_20": round(rvol_val, 2),
            "above_ema50": bool(close_p > float(bar.get("ema_50", close_p))),
            "above_ema200": bool(close_p > float(bar.get("ema_200", close_p))),
            "pattern": "Martillo" if float(bar.get("pattern_hammer", 0)) == 1.0 else (
                "Envolvente" if float(bar.get("pattern_bullish_engulfing", 0)) == 1.0 else "Normal"
            ),
        })

    return {"count": len(results), "matches": results}
