"""
Trading EZ - Tests Unitarios de Indicadores Técnicos Contra Valores Matemáticos de Referencia.
"""
import pytest
import numpy as np
import pandas as pd

from src.feature_engineering.trend import calculate_ema, calculate_sma, calculate_adx
from src.feature_engineering.momentum import calculate_rsi, calculate_stoch_rsi, calculate_macd
from src.feature_engineering.volatility import calculate_atr, calculate_bollinger_bands
from src.feature_engineering.volume import calculate_rvol, calculate_obv
from src.feature_engineering.structure import calculate_floor_pivots
from src.feature_engineering.patterns import add_candlestick_patterns

@pytest.fixture
def sample_series():
    # Serie de 30 días ascendente con oscilación
    prices = [100.0 + i + (2.0 if i % 2 == 0 else -1.0) for i in range(30)]
    dates = pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC")
    return pd.Series(prices, index=dates)

@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="UTC")
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(50) * 1.5)
    high = close + np.random.uniform(0.5, 2.0, 50)
    low = close - np.random.uniform(0.5, 2.0, 50)
    open_p = low + np.random.uniform(0.2, 0.8, 50) * (high - low)
    volume = np.random.randint(100000, 500000, 50).astype(float)
    return pd.DataFrame({"open": open_p, "high": high, "low": low, "close": close, "volume": volume}, index=dates)

def test_sma_and_ema_mathematics(sample_series):
    sma_5 = calculate_sma(sample_series, 5)
    assert np.isnan(sma_5.iloc[3])
    assert not np.isnan(sma_5.iloc[4])
    # Media de los primeros 5 elementos
    expected_sma_5 = sample_series.iloc[:5].mean()
    assert abs(sma_5.iloc[4] - expected_sma_5) < 1e-6

    ema_9 = calculate_ema(sample_series, 9)
    assert len(ema_9) == len(sample_series)
    assert not np.isnan(ema_9.iloc[0])

def test_rsi_bounds_and_directional_response():
    dates = pd.date_range("2024-01-01", periods=25, freq="D", tz="UTC")
    # Serie estrictamente alcista -> RSI debe tender a 100
    bull_series = pd.Series([10.0 + i * 2.0 for i in range(25)], index=dates)
    rsi_bull = calculate_rsi(bull_series, 14)
    assert rsi_bull.iloc[-1] > 95.0

    # Serie estrictamente bajista -> RSI debe tender a 0
    bear_series = pd.Series([100.0 - i * 2.0 for i in range(25)], index=dates)
    rsi_bear = calculate_rsi(bear_series, 14)
    assert rsi_bear.iloc[-1] < 5.0

    # Todos los valores dentro del rango [0, 100]
    assert (rsi_bull.dropna() >= 0.0).all() and (rsi_bull.dropna() <= 100.0).all()

def test_bollinger_bands_geometry(sample_series):
    mid, upper, lower, width, pct_b = calculate_bollinger_bands(sample_series, window=10, num_std=2.0)
    valid_idx = mid.dropna().index

    assert (upper.loc[valid_idx] >= mid.loc[valid_idx]).all()
    assert (mid.loc[valid_idx] >= lower.loc[valid_idx]).all()
    assert (width.loc[valid_idx] >= 0.0).all()

def test_atr_is_strictly_positive(sample_ohlcv):
    atr = calculate_atr(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], 14)
    valid_atr = atr.dropna()
    assert len(valid_atr) > 0
    assert (valid_atr > 0.0).all()

def test_floor_pivots_causality(sample_ohlcv):
    p, r1, s1, r2, s2 = calculate_floor_pivots(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
    # La barra 0 debe ser NaN porque shift(1) no tiene dato previo
    assert np.isnan(p.iloc[0])
    # Para la barra 1, el pivote se calcula con los datos de la barra 0
    expected_p1 = (sample_ohlcv["high"].iloc[0] + sample_ohlcv["low"].iloc[0] + sample_ohlcv["close"].iloc[0]) / 3.0
    assert abs(p.iloc[1] - expected_p1) < 1e-6
    # Niveles ordenados: R2 > R1 > P > S1 > S2
    assert r2.iloc[1] > r1.iloc[1] >= p.iloc[1] >= s1.iloc[1] > s2.iloc[1]

def test_candlestick_pattern_hammer():
    dates = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    # Construir un martillo sintético perfecto:
    # Open=100, High=100.5 (sombra sup 0.5), Low=90 (sombra inf 9), Close=101 (cuerpo 1)
    df = pd.DataFrame({
        "open": [105.0, 103.0, 100.0],
        "high": [106.0, 104.0, 101.8],
        "low": [104.0, 102.0, 92.0],
        "close": [104.5, 102.5, 101.5],
        "volume": [1000, 1000, 2000],
    }, index=dates)

    patterns = add_candlestick_patterns(df)
    assert patterns["pattern_hammer"].iloc[-1] == 1.0
