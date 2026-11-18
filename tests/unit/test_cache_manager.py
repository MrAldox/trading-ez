"""
Trading EZ - Tests Unitarios de Caché Dual (Memoria y Parquet) (Fase 1).
"""
import time
import pytest
import pandas as pd
from pathlib import Path
import tempfile

from src.data_providers.cache_manager import CacheManager

@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_df():
    dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    return pd.DataFrame({
        "open": [10.0, 11.0, 12.0, 13.0, 14.0],
        "high": [10.5, 11.5, 12.5, 13.5, 14.5],
        "low": [9.5, 10.5, 11.5, 12.5, 13.5],
        "close": [10.2, 11.2, 12.2, 13.2, 14.2],
        "volume": [100, 200, 300, 400, 500],
    }, index=dates)

def test_memory_cache_hit_and_expiration(temp_cache_dir, sample_df):
    cm = CacheManager(cache_dir=temp_cache_dir, memory_ttl_seconds=0.1)
    cm.set_memory("TEST_KEY", sample_df, source="live")

    # Inmediato: hit
    res = cm.get_from_memory("TEST_KEY")
    assert res is not None
    data, src = res
    assert len(data) == 5
    assert src == "live"

    # Esperar expiración
    time.sleep(0.15)
    assert cm.get_from_memory("TEST_KEY") is None

def test_parquet_disk_save_and_reload(temp_cache_dir, sample_df):
    cm = CacheManager(cache_dir=temp_cache_dir)
    cm.save_daily("AAPL", sample_df, source="live")

    # Verificar existencia de archivo parquet
    file_path = temp_cache_dir / "daily" / "AAPL.parquet"
    assert file_path.exists()

    # Limpiar memoria para obligar a leer de disco
    cm.clear_memory()

    res = cm.get_daily("AAPL")
    assert res is not None
    loaded_df, source = res
    assert len(loaded_df) == 5
    assert list(loaded_df.columns) == list(sample_df.columns)
    assert source in ("cache", "stale")

def test_merge_and_save_daily_deduplication(temp_cache_dir, sample_df):
    cm = CacheManager(cache_dir=temp_cache_dir)
    cm.save_daily("NVDA", sample_df)

    # Nuevas barras con 2 días superpuestos y 2 nuevos
    new_dates = pd.date_range("2024-01-04", periods=4, freq="D", tz="UTC")
    new_df = pd.DataFrame({
        "open": [99.0, 99.0, 20.0, 21.0],
        "high": [99.5, 99.5, 20.5, 21.5],
        "low": [98.5, 98.5, 19.5, 20.5],
        "close": [99.2, 99.2, 20.2, 21.2],
        "volume": [1000, 1000, 600, 700],
    }, index=new_dates)

    merged = cm.merge_and_save_daily("NVDA", new_df)
    assert len(merged) == 7
    val = float(merged.loc[merged.index.date == pd.to_datetime("2024-01-04").date(), "close"].iloc[0])
    assert val == 99.2
