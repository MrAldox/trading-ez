"""
Trading EZ - Indicadores Técnicos Causales de Volumen (NumPy / Pandas).
Cálculo de Volumen Relativo (RVOL), On-Balance Volume (OBV), VWAP y divergencias de volumen.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume (OBV) causal acumulativo.
    """
    direction = np.sign(close.diff()).fillna(0.0)
    obv = (direction * volume).cumsum()
    return obv

def calculate_rvol(volume: pd.Series, window: int = 20) -> pd.Series:
    """
    Volumen Relativo (RVOL): Volumen actual / Media móvil de volumen de 20 periodos.
    Valores > 1.5 indican volumen institucional inusual.
    """
    vol_sma = volume.rolling(window=window, min_periods=window).mean()
    return volume / vol_sma.replace(0, np.nan)

def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega todas las características de volumen causales."""
    res = df.copy()
    close = res["close"]
    high = res["high"]
    low = res["low"]
    volume = res["volume"]

    # Volumen Relativo (RVOL 20 días)
    res["rvol_20"] = calculate_rvol(volume, 20)
    res["high_volume_spike"] = (res["rvol_20"] >= 1.5).astype(float)
    res["low_volume_dryup"] = (res["rvol_20"] <= 0.6).astype(float)

    # On-Balance Volume y su media
    obv = calculate_obv(close, volume)
    res["obv"] = obv
    res["obv_ema_21"] = obv.ewm(span=21, adjust=False).mean()
    res["obv_bullish"] = (res["obv"] > res["obv_ema_21"]).astype(float)

    # VWAP aproximado causal si no viene provisto
    if "vwap" not in res.columns:
        typical_price = (high + low + close) / 3.0
        res["vwap"] = (typical_price * volume).cumsum() / volume.cumsum().replace(0, np.nan)

    res["dist_vwap"] = (close - res["vwap"]) / res["vwap"].replace(0, np.nan)

    return res
