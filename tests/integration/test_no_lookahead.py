"""
Trading EZ - Test de Integración Anti-Lookahead Bias (Fase 2).
Verificación matemática: la señal en la barra k con datos [:k] debe ser idéntica a la calculada con todo el histórico.
"""
import pytest
import pandas as pd
from pathlib import Path

from src.feature_engineering.pipeline import build_features, verify_causality
from src.data_providers.cache_manager import CacheManager

def test_pipeline_zero_lookahead_on_cached_data():
    cm = CacheManager()
    # Usar datos reales descargados de AAPL o SPY
    res = cm.get_daily("AAPL")
    if res is None:
        pytest.skip("No hay datos de AAPL en caché.")

    df, _ = res
    assert len(df) > 500

    # Ejecutar la prueba matemática formal en diferentes puntos temporales
    assert verify_causality(df, test_row_idx=250) is True
    assert verify_causality(df, test_row_idx=500) is True
    assert verify_causality(df, test_row_idx=1000) is True

def test_pipeline_zero_lookahead_on_crypto_data():
    cm = CacheManager()
    res = cm.get_daily("BTC-USD")
    if res is None:
        pytest.skip("No hay datos de BTC-USD en caché.")

    df, _ = res
    assert len(df) > 500
    assert verify_causality(df, test_row_idx=400) is True
    assert verify_causality(df, test_row_idx=800) is True
