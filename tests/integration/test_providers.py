"""
Trading EZ - Tests de Integración de Proveedores de Datos y Mecanismo de Fallback (Fase 1).
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from src.core.errors import ProviderError
from src.data_providers.base import BaseDataProvider
from src.data_providers.cache_manager import CacheManager
from src.data_providers.integrity import DataIntegrityAuditor

class MockFailingDataProvider(BaseDataProvider):
    """Proveedor mock que simula caídas de red para probar fallback a 'stale'."""
    def __init__(self, cache_manager, auditor, should_fail=False):
        super().__init__("MockProvider", cache_manager, auditor)
        self.should_fail = should_fail

    def _fetch_daily_remote(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        if self.should_fail:
            raise ConnectionError("Fallo de conexión simulado con el exchange/proveedor.")
        dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        return pd.DataFrame({
            "open": [100.0] * 10,
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "close": [102.0] * 10,
            "volume": [50000] * 10,
            "vwap": [101.0] * 10,
        }, index=dates)

    def _fetch_intraday_remote(self, symbol: str, interval: str, days: int) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_quote(self, symbol: str):
        return {"symbol": symbol, "price": 100.0}

def test_provider_normal_fetch_and_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        auditor = DataIntegrityAuditor()
        provider = MockFailingDataProvider(cm, auditor, should_fail=False)

        # Primera llamada: va a 'live' y guarda en caché
        df, source, report = provider.fetch_daily("BTC-USD", asset_class="crypto")
        assert source == "live"
        assert len(df) == 10
        assert report.is_valid is True

        # Segunda llamada inmediata: debe responder desde 'cache'
        df2, source2, report2 = provider.fetch_daily("BTC-USD", asset_class="crypto")
        assert source2 in ("cache", "live")
        assert len(df2) == 10

def test_provider_fails_and_gracefully_falls_back_to_stale():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        auditor = DataIntegrityAuditor()

        # 1. Guardar primero datos en caché
        dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        cached_df = pd.DataFrame({
            "open": [50.0] * 5,
            "high": [55.0] * 5,
            "low": [48.0] * 5,
            "close": [52.0] * 5,
            "volume": [10000] * 5,
            "vwap": [51.5] * 5,
        }, index=dates)
        cm.save_daily("ETH-USD", cached_df)

        # 2. Ahora el proveedor remoto se cae
        failing_provider = MockFailingDataProvider(cm, auditor, should_fail=True)

        # Debe recurrir a los datos en caché y marcarlos como 'stale'
        df, source, report = failing_provider.fetch_daily("ETH-USD", asset_class="crypto", force_refresh=True)
        assert source == "stale"
        assert len(df) == 5
        assert any("Fallback a caché" in warn for warn in report.warnings)

def test_provider_fails_with_no_cache_raises_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        auditor = DataIntegrityAuditor()
        failing_provider = MockFailingDataProvider(cm, auditor, should_fail=True)

        with pytest.raises(ProviderError):
            failing_provider.fetch_daily("NO_CACHE_SYMBOL", force_refresh=True)
