"""
Trading EZ - Indicadores Técnicos Causales de Volatilidad (NumPy / Pandas).
Cálculo de ATR(14) de Wilder, Bandas de Bollinger(20,2), Ancho de Banda, %B,
Volatilidad Realizada anualizada y Régimen de Volatilidad en percentil histórico.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range (TR)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range (ATR) con suavizado de Wilder."""
    tr = calculate_true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

def calculate_bollinger_bands(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Bandas de Bollinger: Medio (SMA), Superior, Inferior, Ancho y %B.
    """
    middle = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    percent_b = (series - lower) / (upper - lower).replace(0, np.nan)

    return middle, upper, lower, bandwidth, percent_b

def calculate_realized_volatility(close: pd.Series, window: int = 20, annual_factor: float = 252.0) -> pd.Series:
    """Volatilidad Realizada anualizada a partir de retornos logarítmicos causales."""
    log_ret = np.log(close / close.shift(1))
    rolling_std = log_ret.rolling(window=window, min_periods=window).std()
    return rolling_std * np.sqrt(annual_factor)

def calculate_rolling_percentile(series: pd.Series, lookback: int = 252) -> pd.Series:
    """
    Calcula el percentil histórico (0.0 a 1.0) del valor actual respecto a los últimos 'lookback' periodos.
    Permite identificar si el activo está en un régimen de volatilidad anormalmente alto o bajo.
    """
    def _pct_rank(window_vals):
        current = window_vals[-1]
        valid = window_vals[~np.isnan(window_vals)]
        if len(valid) == 0:
            return 0.5
        return (valid < current).sum() / float(len(valid))

    return series.rolling(window=lookback, min_periods=min(30, lookback)).apply(_pct_rank, raw=True)

def add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega todas las características de volatilidad causales."""
    res = df.copy()
    close = res["close"]
    high = res["high"]
    low = res["low"]

    # ATR(14)
    atr_14 = calculate_atr(high, low, close, 14)
    res["atr_14"] = atr_14
    res["atr_pct"] = atr_14 / close.replace(0, np.nan)  # ATR como % del precio

    # Bandas de Bollinger(20, 2)
    bb_mid, bb_upper, bb_lower, bb_width, bb_pct = calculate_bollinger_bands(close, 20, 2.0)
    res["bb_middle"] = bb_mid
    res["bb_upper"] = bb_upper
    res["bb_lower"] = bb_lower
    res["bb_bandwidth"] = bb_width
    res["bb_percent_b"] = bb_pct

    # Squeeze y rupturas de volatilidad
    # Bollinger Squeeze: cuando el ancho de banda cae a su mínimo de 60 periodos
    res["bb_squeeze"] = (bb_width <= bb_width.rolling(window=60, min_periods=20).min()).astype(float)
    res["bb_upper_touch"] = (close >= bb_upper).astype(float)
    res["bb_lower_touch"] = (close <= bb_lower).astype(float)

    # Volatilidad Realizada anualizada (20 días)
    res["realized_vol_20d"] = calculate_realized_volatility(close, 20)

    # Régimen de Volatilidad (percentil histórico anual 252 días)
    res["volatility_regime_pct"] = calculate_rolling_percentile(res["atr_pct"], 252)
    res["high_volatility_regime"] = (res["volatility_regime_pct"] > 0.75).astype(float)
    res["low_volatility_regime"] = (res["volatility_regime_pct"] < 0.25).astype(float)

    return res
