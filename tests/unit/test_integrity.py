"""
Trading EZ - Tests Unitarios de Integridad y Validación de Datos (Fase 1).
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from src.core.errors import DataIntegrityError
from src.data_providers.integrity import DataIntegrityAuditor

@pytest.fixture
def sample_valid_ohlcv():
    dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    data = {
        "open": [100.0 + i for i in range(10)],
        "high": [105.0 + i for i in range(10)],
        "low": [98.0 + i for i in range(10)],
        "close": [102.0 + i for i in range(10)],
        "volume": [1000000 + i * 50000 for i in range(10)],
    }
    return pd.DataFrame(data, index=dates)

def test_auditor_validates_clean_data(sample_valid_ohlcv):
    auditor = DataIntegrityAuditor()
    clean_df, report = auditor.audit_and_clean(sample_valid_ohlcv, symbol="AAPL", asset_class="stocks")
    assert report.is_valid is True
    assert len(clean_df) == 10
    assert report.repaired_rows_dropped == 0
    assert len(report.issues_found) == 0

def test_auditor_detects_and_drops_negative_prices(sample_valid_ohlcv):
    auditor = DataIntegrityAuditor()
    corrupt_df = sample_valid_ohlcv.copy()
    corrupt_df.iloc[3, corrupt_df.columns.get_loc("close")] = -5.0
    corrupt_df.iloc[7, corrupt_df.columns.get_loc("low")] = 0.0

    clean_df, report = auditor.audit_and_clean(corrupt_df, symbol="AAPL", auto_repair=True)
    assert len(clean_df) == 8
    assert report.repaired_rows_dropped == 2
    assert any("<= 0" in issue for issue in report.issues_found)

def test_auditor_strict_raise_on_negative_prices(sample_valid_ohlcv):
    auditor = DataIntegrityAuditor()
    corrupt_df = sample_valid_ohlcv.copy()
    corrupt_df.iloc[2, corrupt_df.columns.get_loc("close")] = -10.0

    with pytest.raises(DataIntegrityError):
        auditor.audit_and_clean(corrupt_df, symbol="AAPL", auto_repair=False, strict_raise=True)

def test_auditor_detects_invalid_candle_geometry(sample_valid_ohlcv):
    auditor = DataIntegrityAuditor()
    corrupt_df = sample_valid_ohlcv.copy()
    # High menor que Low
    corrupt_df.iloc[4, corrupt_df.columns.get_loc("high")] = 90.0
    corrupt_df.iloc[4, corrupt_df.columns.get_loc("low")] = 95.0

    clean_df, report = auditor.audit_and_clean(corrupt_df, symbol="AAPL", auto_repair=True)
    assert len(clean_df) == 9
    assert report.repaired_rows_dropped == 1
    assert any("geometría inválida" in issue for issue in report.issues_found)

def test_auditor_detects_extreme_price_jump(sample_valid_ohlcv):
    auditor = DataIntegrityAuditor(max_price_jump_pct=0.40)
    jump_df = sample_valid_ohlcv.copy()
    # Salto del 60% en el día 5
    jump_df.iloc[5, jump_df.columns.get_loc("close")] = jump_df.iloc[4]["close"] * 1.65

    clean_df, report = auditor.audit_and_clean(jump_df, symbol="AAPL", auto_repair=False)
    assert any("saltos extremos" in issue for issue in report.issues_found)

def test_auditor_deduplicates_timestamps(sample_valid_ohlcv):
    auditor = DataIntegrityAuditor()
    dup_df = pd.concat([sample_valid_ohlcv, sample_valid_ohlcv.iloc[[3]]]).sort_index()
    assert len(dup_df) == 11

    clean_df, report = auditor.audit_and_clean(dup_df, symbol="AAPL", auto_repair=True)
    assert len(clean_df) == 10
    assert any("duplicadas" in issue for issue in report.issues_found)

def test_auditor_detects_stale_data():
    auditor = DataIntegrityAuditor(max_stale_hours_crypto=4.0)
    old_dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    old_df = pd.DataFrame({
        "open": [100.0] * 5,
        "high": [105.0] * 5,
        "low": [95.0] * 5,
        "close": [102.0] * 5,
        "volume": [1000] * 5,
    }, index=old_dates)

    clean_df, report = auditor.audit_and_clean(old_df, symbol="BTC-USD", asset_class="crypto")
    assert report.is_stale is True
    assert report.stale_hours > 4.0
    assert any("obsoletos" in warn for warn in report.warnings)
