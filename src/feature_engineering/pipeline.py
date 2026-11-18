"""
Trading EZ - Pipeline Unificado de Características Causales y Verificador Anti-Lookahead.
Transforma series crudas de precios en vectores de variables predictivas 100% reproducibles.
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd

from src.core.errors import LookaheadError
from src.feature_engineering.trend import add_trend_features
from src.feature_engineering.momentum import add_momentum_features
from src.feature_engineering.volatility import add_volatility_features
from src.feature_engineering.volume import add_volume_features
from src.feature_engineering.structure import add_structure_features
from src.feature_engineering.patterns import add_candlestick_patterns
from src.feature_engineering.market_context import add_market_context_features

# Lista canónica de columnas de características predictivas para el modelo
FEATURE_COLUMNS = [
    # Tendencia
    "dist_ema_21", "dist_ema_50", "dist_ema_200",
    "ema_9_above_21", "ema_21_above_50", "ema_50_above_200", "trend_alignment_bullish",
    "ema_21_slope_5d", "ema_50_slope_10d",
    "adx_14", "plus_di_14", "minus_di_14", "adx_trending",

    # Momentum
    "ret_1d", "ret_5d", "ret_20d", "ret_60d",
    "rsi_14", "rsi_oversold", "rsi_overbought", "rsi_bullish_momentum",
    "stoch_rsi_k", "stoch_rsi_d", "stoch_rsi_bullish_cross",
    "macd_line", "macd_signal", "macd_hist", "macd_bullish_cross", "macd_accelerating",
    "roc_12",

    # Volatilidad
    "atr_pct", "bb_bandwidth", "bb_percent_b",
    "bb_squeeze", "bb_upper_touch", "bb_lower_touch",
    "realized_vol_20d", "volatility_regime_pct", "high_volatility_regime", "low_volatility_regime",

    # Volumen
    "rvol_20", "high_volume_spike", "low_volume_dryup",
    "obv_bullish", "dist_vwap",

    # Estructura
    "dist_pivot_p", "dist_pivot_s1", "dist_pivot_r1",
    "dist_52w_high", "dist_52w_low", "near_52w_high",
    "breakout_20d_high", "breakdown_20d_low",

    # Patrones de velas
    "pattern_doji", "pattern_hammer", "pattern_bullish_engulfing",
    "pattern_bearish_engulfing", "pattern_morning_star",

    # Contexto de Mercado
    "benchmark_above_ema50", "relative_strength_momentum", "outperforming_market",
]

def build_features(
    df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None,
    benchmark_name: str = "SPY",
) -> pd.DataFrame:
    """
    Calcula el pipeline completo de características sobre el DataFrame.
    Todas las transformaciones son causales (dependen únicamente de observaciones t <= ahora).
    """
    res = df.copy()

    # 1. Indicadores por dominio
    res = add_trend_features(res)
    res = add_momentum_features(res)
    res = add_volatility_features(res)
    res = add_volume_features(res)
    res = add_structure_features(res)
    res = add_candlestick_patterns(res)

    # 2. Contexto de mercado
    res = add_market_context_features(res, benchmark_df, benchmark_name)

    return res

def verify_causality(df: pd.DataFrame, test_row_idx: int = 300) -> bool:
    """
    PRUEBA MATEMÁTICA FORMAL ANTI-LOOKAHEAD BIAS:
    1. Calcula el pipeline sobre todo el conjunto de datos df[0 : N].
    2. Calcula el pipeline de forma independiente sobre un subconjunto truncado df[0 : test_row_idx].
    3. Compara el vector de características en la barra test_row_idx - 1.
    Si cualquier valor difiere en más de 1e-9, existe lookahead bias y se lanza LookaheadError.
    """
    if len(df) < test_row_idx + 10:
        raise ValueError(f"El DataFrame debe tener al menos {test_row_idx + 10} filas para la prueba causal.")

    # Cálculo completo
    full_features = build_features(df)

    # Cálculo con histórico truncado hasta test_row_idx
    truncated_df = df.iloc[:test_row_idx].copy()
    truncated_features = build_features(truncated_df)

    target_bar_date = truncated_df.index[-1]

    # Comparar cada característica en la última barra truncada
    for col in FEATURE_COLUMNS:
        if col not in full_features.columns or col not in truncated_features.columns:
            continue

        val_full = full_features.loc[target_bar_date, col]
        val_trunc = truncated_features.loc[target_bar_date, col]

        if pd.isna(val_full) and pd.isna(val_trunc):
            continue

        diff = abs(float(val_full) - float(val_trunc))
        if diff > 1e-6:
            raise LookaheadError(
                f"Lookahead bias detectado en la variable '{col}' en la fecha {target_bar_date}. "
                f"Valor con datos completos: {val_full}, Valor con histórico truncado: {val_trunc} (Diff: {diff})"
            )

    return True
