"""
Trading EZ - Reconocimiento Algorítmico de Patrones de Velas Japonesas.
Implementación matemática precisa: Martillo, Envolvente Alcista/Bajista, Doji y Estrella de la Mañana.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def add_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables booleanas (0/1) para patrones de velas japonesas clásicos."""
    res = df.copy()
    o = res["open"]
    h = res["high"]
    l = res["low"]
    c = res["close"]

    body = (c - o).abs()
    candle_range = (h - l).replace(0, np.nan)
    body_pct = body / candle_range

    is_green = c > o
    is_red = c < o

    upper_shadow = h - np.maximum(o, c)
    lower_shadow = np.minimum(o, c) - l

    # 1. Doji: cuerpo menor al 10% del rango total de la vela
    res["pattern_doji"] = (body_pct <= 0.10).astype(float)

    # 2. Martillo (Hammer): sombra inferior >= 2x cuerpo, sombra superior pequeña (<= 20% del rango)
    res["pattern_hammer"] = (
        (lower_shadow >= 2.0 * body) &
        (upper_shadow <= 0.20 * candle_range) &
        (body_pct >= 0.10)
    ).astype(float)

    # 3. Envolvente Alcista (Bullish Engulfing)
    prev_o = o.shift(1)
    prev_c = c.shift(1)
    prev_is_red = prev_c < prev_o
    res["pattern_bullish_engulfing"] = (
        prev_is_red &
        is_green &
        (c >= prev_o) &
        (o <= prev_c)
    ).astype(float)

    # 4. Envolvente Bajista (Bearish Engulfing)
    prev_is_green = prev_c > prev_o
    res["pattern_bearish_engulfing"] = (
        prev_is_green &
        is_red &
        (c <= prev_o) &
        (o >= prev_c)
    ).astype(float)

    # 5. Estrella de la Mañana (Morning Star - 3 velas)
    # Vela t-2 roja fuerte, Vela t-1 cuerpo pequeño (indecisión), Vela t verde cerrando > punto medio de t-2
    c_minus_2 = c.shift(2)
    o_minus_2 = o.shift(2)
    body_pct_minus_1 = body_pct.shift(1)

    is_red_minus_2 = c_minus_2 < o_minus_2
    midpoint_minus_2 = (o_minus_2 + c_minus_2) / 2.0

    res["pattern_morning_star"] = (
        is_red_minus_2 &
        (body_pct_minus_1 <= 0.35) &
        is_green &
        (c > midpoint_minus_2)
    ).astype(float)

    return res
