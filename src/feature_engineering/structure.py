"""
Trading EZ - Indicadores Técnicos de Estructura de Mercado y Soportes/Resistencias.
Pivotes Floor Trader (P, S1, S2, R1, R2) calculados estrictamente con datos de t-1,
distancias a máximos/mínimos de 52 semanas y niveles de swing.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def calculate_floor_pivots(high: pd.Series, low: pd.Series, close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Pivotes clásicos Floor Trader calculados con los valores de la vela PREVIA (shift 1).
    Garantía causal: Para la vela t, los niveles se basan exclusivamente en High, Low, Close de t-1.
    """
    prev_h = high.shift(1)
    prev_l = low.shift(1)
    prev_c = close.shift(1)

    pivot = (prev_h + prev_l + prev_c) / 3.0
    r1 = (2.0 * pivot) - prev_l
    s1 = (2.0 * pivot) - prev_h
    r2 = pivot + (prev_h - prev_l)
    s2 = pivot - (prev_h - prev_l)

    return pivot, r1, s1, r2, s2

def add_structure_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega todas las características de estructura y niveles clave causales."""
    res = df.copy()
    close = res["close"]
    high = res["high"]
    low = res["low"]

    # Niveles Floor Trader
    p, r1, s1, r2, s2 = calculate_floor_pivots(high, low, close)
    res["pivot_p"] = p
    res["pivot_r1"] = r1
    res["pivot_s1"] = s1
    res["pivot_r2"] = r2
    res["pivot_s2"] = s2

    # Distancias porcentuales a pivotes
    res["dist_pivot_p"] = (close - p) / p.replace(0, np.nan)
    res["dist_pivot_s1"] = (close - s1) / s1.replace(0, np.nan)
    res["dist_pivot_r1"] = (close - r1) / r1.replace(0, np.nan)

    # Máximos y Mínimos de 52 semanas (252 barras de mercado)
    rolling_52w_high = high.rolling(window=252, min_periods=50).max()
    rolling_52w_low = low.rolling(window=252, min_periods=50).min()

    res["dist_52w_high"] = (close - rolling_52w_high) / rolling_52w_high.replace(0, np.nan)
    res["dist_52w_low"] = (close - rolling_52w_low) / rolling_52w_low.replace(0, np.nan)
    res["near_52w_high"] = (res["dist_52w_high"] >= -0.05).astype(float)  # A menos de 5% del máximo anual

    # Swings de 20 periodos (Soporte y Resistencia local)
    res["swing_high_20d"] = high.rolling(window=20, min_periods=10).max().shift(1)
    res["swing_low_20d"] = low.rolling(window=20, min_periods=10).min().shift(1)
    res["breakout_20d_high"] = (close > res["swing_high_20d"]).astype(float)
    res["breakdown_20d_low"] = (close < res["swing_low_20d"]).astype(float)

    return res
