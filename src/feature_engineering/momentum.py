"""
Trading EZ - Indicadores Técnicos Causales de Momentum (NumPy / Pandas).
Cálculo canónico de RSI(14) de Wilder, Stochastic RSI, MACD(12,26,9), ROC y retornos multi-horizonte.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from src.feature_engineering.trend import calculate_ema

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI canónico de J. Welles Wilder con suavizado exponencial alpha = 1 / period.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Suavizado de Wilder: alpha = 1 / period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Casos límite: sin pérdidas -> RSI=100; sin ganancias -> RSI=0
    fill_vals = pd.Series(np.where(avg_gain > 0, 100.0, 50.0), index=series.index)
    rsi = rsi.fillna(fill_vals)
    return rsi

def calculate_stoch_rsi(
    rsi_series: pd.Series,
    period: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    Stochastic RSI (%K y %D).
    """
    min_rsi = rsi_series.rolling(window=period, min_periods=period).min()
    max_rsi = rsi_series.rolling(window=period, min_periods=period).max()
    denom = (max_rsi - min_rsi).replace(0, np.nan)

    stoch_raw = (rsi_series - min_rsi) / denom
    stoch_k = stoch_raw.rolling(window=smooth_k, min_periods=smooth_k).mean() * 100.0
    stoch_d = stoch_k.rolling(window=smooth_d, min_periods=smooth_d).mean()
    return stoch_k, stoch_d

def calculate_macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD estándar: Línea MACD (EMA 12 - EMA 26), Señal (EMA 9) e Histograma.
    """
    fast_ema = calculate_ema(series, fast_period)
    slow_ema = calculate_ema(series, slow_period)
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal_period)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calculate_roc(series: pd.Series, period: int = 12) -> pd.Series:
    """Rate of Change (ROC): ((Close_t - Close_{t-n}) / Close_{t-n}) * 100."""
    return ((series - series.shift(period)) / series.shift(period).replace(0, np.nan)) * 100.0

def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega todas las características de momentum causales."""
    res = df.copy()
    close = res["close"]

    # Retornos temporales causales
    res["ret_1d"] = close.pct_change(1)
    res["ret_5d"] = close.pct_change(5)
    res["ret_20d"] = close.pct_change(20)
    res["ret_60d"] = close.pct_change(60)

    # RSI(14)
    res["rsi_14"] = calculate_rsi(close, 14)
    res["rsi_oversold"] = (res["rsi_14"] < 30.0).astype(float)
    res["rsi_overbought"] = (res["rsi_14"] > 70.0).astype(float)
    res["rsi_bullish_momentum"] = ((res["rsi_14"] >= 50.0) & (res["rsi_14"] <= 70.0)).astype(float)

    # Stochastic RSI
    stoch_k, stoch_d = calculate_stoch_rsi(res["rsi_14"], 14, 3, 3)
    res["stoch_rsi_k"] = stoch_k
    res["stoch_rsi_d"] = stoch_d
    res["stoch_rsi_bullish_cross"] = ((stoch_k > stoch_d) & (stoch_k.shift(1) <= stoch_d.shift(1)) & (stoch_k < 80.0)).astype(float)

    # MACD(12, 26, 9)
    macd_line, signal_line, hist = calculate_macd(close, 12, 26, 9)
    res["macd_line"] = macd_line
    res["macd_signal"] = signal_line
    res["macd_hist"] = hist
    res["macd_bullish_cross"] = ((macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))).astype(float)
    res["macd_accelerating"] = (hist > hist.shift(1)).astype(float)

    # ROC
    res["roc_12"] = calculate_roc(close, 12)

    return res
