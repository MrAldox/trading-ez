"""
Trading EZ - Indicadores Técnicos Causales de Tendencia (NumPy / Pandas).
Cálculo de EMA, SMA, Cruces, Pendientes y ADX(14) según la fórmula canónica de Wilder.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Media Móvil Simple (SMA)."""
    return series.rolling(window=window, min_periods=window).mean()

def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Media Móvil Exponencial (EMA)."""
    return series.ewm(span=span, adjust=False).mean()

def calculate_slope(series: pd.Series, window: int = 5) -> pd.Series:
    """
    Pendiente porcentual normalizada de la serie sobre 'window' velas:
    (valor_actual - valor_hace_n) / valor_hace_n / window
    """
    shifted = series.shift(window)
    slope = (series - shifted) / (shifted.replace(0, np.nan) * window)
    return slope

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Cálculo de Average Directional Index (ADX) con suavizado de Wilder.
    Retorna (ADX, +DI, -DI).
    """
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    # True Range
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

    # Suavizado de Wilder: alpha = 1 / period
    tr_smooth = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # Directional Indicators (+DI, -DI)
    plus_di = 100.0 * (plus_dm_smooth / tr_smooth.replace(0, np.nan))
    minus_di = 100.0 * (minus_dm_smooth / tr_smooth.replace(0, np.nan))

    # DX y ADX
    dx_diff = (plus_di - minus_di).abs()
    dx_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100.0 * (dx_diff / dx_sum)

    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx, plus_di, minus_di

def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega todas las características de tendencia de forma estrictamente causal."""
    res = df.copy()
    close = res["close"]
    high = res["high"]
    low = res["low"]

    # EMAs canónicas
    res["ema_9"] = calculate_ema(close, 9)
    res["ema_21"] = calculate_ema(close, 21)
    res["ema_50"] = calculate_ema(close, 50)
    res["ema_200"] = calculate_ema(close, 200)

    # SMAs de referencia
    res["sma_20"] = calculate_sma(close, 20)
    res["sma_50"] = calculate_sma(close, 50)

    # Posición relativa respecto a EMAs (distancia porcentual)
    res["dist_ema_21"] = (close - res["ema_21"]) / res["ema_21"]
    res["dist_ema_50"] = (close - res["ema_50"]) / res["ema_50"]
    res["dist_ema_200"] = (close - res["ema_200"]) / res["ema_200"]

    # Cruces y alineación tendencial
    res["ema_9_above_21"] = (res["ema_9"] > res["ema_21"]).astype(float)
    res["ema_21_above_50"] = (res["ema_21"] > res["ema_50"]).astype(float)
    res["ema_50_above_200"] = (res["ema_50"] > res["ema_200"]).astype(float)  # Golden Cross
    res["trend_alignment_bullish"] = (
        (res["ema_9"] > res["ema_21"]) &
        (res["ema_21"] > res["ema_50"]) &
        (res["ema_50"] > res["ema_200"])
    ).astype(float)

    # Pendientes
    res["ema_21_slope_5d"] = calculate_slope(res["ema_21"], 5)
    res["ema_50_slope_10d"] = calculate_slope(res["ema_50"], 10)

    # ADX(14)
    adx, plus_di, minus_di = calculate_adx(high, low, close, 14)
    res["adx_14"] = adx
    res["plus_di_14"] = plus_di
    res["minus_di_14"] = minus_di
    res["adx_trending"] = (adx > 25.0).astype(float)

    return res
