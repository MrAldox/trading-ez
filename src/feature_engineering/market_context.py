"""
Trading EZ - Contexto de Mercado y Fuerza Relativa (SPY / BTC).
Proporciona al modelo la posición del mercado global para evitar comprar contra corriente.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from src.feature_engineering.trend import calculate_ema

def add_market_context_features(
    asset_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    benchmark_name: str = "SPY",
) -> pd.DataFrame:
    """
    Combina la serie del activo con la del índice de referencia (SPY o BTC) para calcular
    fuerza relativa y régimen de mercado de forma estrictamente causal por fecha.
    """
    res = asset_df.copy()

    if benchmark_df is None or benchmark_df.empty:
        # Valores neutros por defecto si no hay benchmark
        res["benchmark_above_ema50"] = 1.0
        res["relative_strength_ratio"] = 1.0
        res["relative_strength_momentum"] = 0.0
        return res

    res_norm_idx = res.index.normalize()
    bench_copy = benchmark_df["close"].copy()
    bench_copy.index = bench_copy.index.normalize()
    bench_close = bench_copy.reindex(res_norm_idx).ffill().bfill()
    bench_close.index = res.index
    bench_ema50 = calculate_ema(bench_close, 50)
    bench_ema200 = calculate_ema(bench_close, 200)

    # 1. Régimen del mercado amplio (¿Está el índice sobre su EMA 50 y EMA 200?)
    res["benchmark_above_ema50"] = (bench_close > bench_ema50).astype(float)
    res["benchmark_above_ema200"] = (bench_close > bench_ema200).astype(float)

    # 2. Ratio de Fuerza Relativa (RS = Activo / Benchmark)
    rs_ratio = res["close"] / bench_close.replace(0, np.nan)
    res["relative_strength_ratio"] = rs_ratio

    # 3. Momentum de Fuerza Relativa (RS actual vs media de 20 días)
    rs_sma20 = rs_ratio.rolling(window=20, min_periods=5).mean()
    res["relative_strength_momentum"] = (rs_ratio - rs_sma20) / rs_sma20.replace(0, np.nan)
    res["outperforming_market"] = (res["relative_strength_momentum"] > 0.0).astype(float)

    return res
