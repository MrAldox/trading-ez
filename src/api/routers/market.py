"""
Trading EZ - Router de Mercado en Vivo, Histórico y Mapa de Calor.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
import pandas as pd

from src.core.config import settings
from src.data_providers.manager import data_manager
from src.data_providers.cache_manager import CacheManager

router = APIRouter(prefix="/api/market", tags=["Mercado"])
cache_mgr = CacheManager()

import time
from concurrent.futures import ThreadPoolExecutor

_LIVE_CACHE: Dict[str, Any] = {}
_LIVE_CACHE_EXPIRES: float = 0.0

def _fetch_single_quote(sym: str) -> Optional[Dict[str, Any]]:
    try:
        q = data_manager.fetch_quote(sym)
        meta = settings.assets_by_symbol.get(sym)
        q["name"] = meta.name if meta else sym
        q["asset_class"] = meta.asset_class if meta else "stocks"
        q["sector"] = meta.sector if meta else "General"
        return q
    except Exception:
        # Fallback ultra-rápido a última barra de caché local
        cached = cache_mgr.get_daily(sym)
        if cached:
            df, _ = cached
            if not df.empty:
                last_p = round(float(df["close"].iloc[-1]), 2)
                prev_p = round(float(df["close"].iloc[-2]), 2) if len(df) > 1 else last_p
                chg = round(last_p - prev_p, 2)
                chg_pct = round((chg / prev_p) * 100.0, 2) if prev_p > 0 else 0.0
                meta = settings.assets_by_symbol.get(sym)
                return {
                    "symbol": sym,
                    "name": meta.name if meta else sym,
                    "asset_class": meta.asset_class if meta else "stocks",
                    "sector": meta.sector if meta else "General",
                    "price": last_p,
                    "previous_close": prev_p,
                    "change": chg,
                    "change_pct": chg_pct,
                    "volume": int(df["volume"].iloc[-1]),
                    "source": "cache",
                }
        return None

@router.get("/live")
def get_live_market(symbols: Optional[str] = Query(None, description="Símbolos separados por coma")):
    """Cotizaciones en tiempo real para la cinta de tickers y watchlist con caché y concurrencia."""
    global _LIVE_CACHE, _LIVE_CACHE_EXPIRES
    now = time.time()

    if not symbols and _LIVE_CACHE and now < _LIVE_CACHE_EXPIRES:
        return {"count": len(_LIVE_CACHE), "quotes": list(_LIVE_CACHE.values())}

    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        sym_list = [a.symbol for a in settings.universe]

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_single_quote, sym): sym for sym in sym_list}
        for future in futures:
            res = future.result()
            if res:
                results.append(res)

    if not symbols and results:
        _LIVE_CACHE = {r["symbol"]: r for r in results}
        _LIVE_CACHE_EXPIRES = now + 25.0  # Caché de 25 segundos

    return {"count": len(results), "quotes": results}

@router.get("/history")
def get_market_history(
    symbol: str = Query(..., description="Símbolo del activo (ej. NVDA, BTC-USD)"),
    resolution: str = Query("1d", description="Resolución: 1d | 1h"),
    bars: int = Query(250, description="Número de barras hacia atrás"),
):
    """
    Devuelve la serie OHLCV con indicadores técnicos para el motor Canvas del frontend.
    """
    sym = symbol.strip().upper()
    res = cache_mgr.get_daily(sym)
    if not res:
        # Intentar descargar
        try:
            df, source, _ = data_manager.fetch_daily_data(sym)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para {sym}: {str(e)}")
    else:
        df, source = res

    from src.feature_engineering.pipeline import build_features
    spy_res = cache_mgr.get_daily("SPY")
    bench = spy_res[0] if spy_res else None
    feat_df = build_features(df, benchmark_df=bench)

    # Tomar las últimas 'bars' barras
    tail = feat_df.iloc[-min(bars, len(feat_df)):].copy()

    candle_data = []
    for idx, row in tail.iterrows():
        candle_data.append({
            "timestamp": idx.strftime("%Y-%m-%d"),
            "time_unix": int(idx.timestamp()),
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(row["low"], 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
            "ema_9": round(float(row["ema_9"]), 2) if not pd.isna(row.get("ema_9")) else None,
            "ema_21": round(float(row["ema_21"]), 2) if not pd.isna(row.get("ema_21")) else None,
            "ema_50": round(float(row["ema_50"]), 2) if not pd.isna(row.get("ema_50")) else None,
            "ema_200": round(float(row["ema_200"]), 2) if not pd.isna(row.get("ema_200")) else None,
            "bb_upper": round(float(row["bb_upper"]), 2) if not pd.isna(row.get("bb_upper")) else None,
            "bb_lower": round(float(row["bb_lower"]), 2) if not pd.isna(row.get("bb_lower")) else None,
            "rsi_14": round(float(row["rsi_14"]), 1) if not pd.isna(row.get("rsi_14")) else None,
            "atr_14": round(float(row["atr_14"]), 2) if not pd.isna(row.get("atr_14")) else None,
        })

    return {
        "symbol": sym,
        "resolution": resolution,
        "count": len(candle_data),
        "data_source": source,
        "candles": candle_data,
    }

@router.get("/heatmap")
def get_market_heatmap():
    """Mapa de calor de rendimiento diario por sectores y clases de activos."""
    universe = settings.universe
    sectors_map: Dict[str, List[Dict[str, Any]]] = {}

    for asset in universe:
        try:
            q = data_manager.fetch_quote(asset.symbol)
            item = {
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_class": asset.asset_class,
                "price": q.get("price", 0.0),
                "change_pct": q.get("change_pct", 0.0),
                "volume": q.get("volume", 0),
            }
            sec = asset.sector or "Otros"
            sectors_map.setdefault(sec, []).append(item)
        except Exception:
            continue

    formatted_heatmap = []
    for sector, items in sectors_map.items():
        avg_chg = sum(i["change_pct"] for i in items) / len(items) if items else 0.0
        formatted_heatmap.append({
            "sector": sector,
            "avg_change_pct": round(avg_chg, 2),
            "assets": sorted(items, key=lambda x: abs(x["change_pct"]), reverse=True),
        })

    formatted_heatmap.sort(key=lambda x: x["avg_change_pct"], reverse=True)
    return {"heatmap": formatted_heatmap}
