"""
Trading EZ - Tests Unitarios de Calendario, Feriados y Manejo de Barras Parciales (Fase 1).
"""
import pytest
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
import pandas as pd

from src.core.calendar import (
    is_us_market_holiday,
    is_market_open,
    is_bar_closed,
    filter_only_closed_bars,
    TZ_US_EASTERN,
    TZ_UTC,
)

def test_fixed_and_floating_us_holidays():
    # Navidad
    assert is_us_market_holiday(date(2024, 12, 25)) is True
    # 4 de Julio
    assert is_us_market_holiday(date(2024, 7, 4)) is True
    # Fin de semana (Sábado)
    assert is_us_market_holiday(date(2024, 7, 6)) is True
    # Día laborable normal (Miércoles 10 Julio 2024)
    assert is_us_market_holiday(date(2024, 7, 10)) is False

def test_market_open_crypto_always_open():
    assert is_market_open("crypto") is True

def test_market_open_stocks_schedule():
    # Martes a las 10:30 AM ET -> Abierto
    open_time = datetime(2024, 10, 15, 10, 30, tzinfo=TZ_US_EASTERN)
    assert is_market_open("stocks", current_dt=open_time) is True

    # Martes a las 08:30 AM ET -> Pre-market cerrado para horario regular
    pre_time = datetime(2024, 10, 15, 8, 30, tzinfo=TZ_US_EASTERN)
    assert is_market_open("stocks", current_dt=pre_time) is False

    # Martes a las 17:00 PM ET -> After-hours cerrado para horario regular
    post_time = datetime(2024, 10, 15, 17, 0, tzinfo=TZ_US_EASTERN)
    assert is_market_open("stocks", current_dt=post_time) is False

def test_partial_bar_identification_and_filtering():
    # Simular momento actual: 14:00 ET de hoy (mercado abierto, vela en curso NO cerrada)
    now_et = datetime(2024, 10, 15, 14, 0, tzinfo=TZ_US_EASTERN)

    # Barra de ayer (Cerrada)
    yesterday = pd.Timestamp("2024-10-14", tz="UTC")
    assert is_bar_closed(yesterday, "stocks", current_dt=now_et) is True

    # Barra de hoy a las 14:00 (Aún no está cerrada, son antes de las 16:00 ET)
    today_bar = pd.Timestamp("2024-10-15", tz="UTC")
    assert is_bar_closed(today_bar, "stocks", current_dt=now_et) is False

    # DataFrame con ambas barras
    df = pd.DataFrame({
        "open": [100.0, 102.0],
        "high": [105.0, 106.0],
        "low": [99.0, 101.0],
        "close": [102.0, 104.0],
        "volume": [1000, 500],
    }, index=[yesterday, today_bar])

    # El filtro DEBE descartar la vela de hoy para evitar lookahead bias
    filtered = filter_only_closed_bars(df, "stocks", current_dt=now_et)
    assert len(filtered) == 1
    assert filtered.index[0] == yesterday
