"""
Trading EZ - Calendarios de Mercado, Zonas Horarias y Manejo de Barras Parciales.
"""
from __future__ import annotations
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
import pandas as pd

# Zonas Horarias Oficiales
TZ_US_EASTERN = ZoneInfo("America/New_York")
TZ_UTC = ZoneInfo("UTC")

# Feriados fijos y reglas estándar de la Bolsa de Nueva York (NYSE/NASDAQ)
# Para modelado riguroso, calculamos o mapeamos días no laborables de mercado
US_HOLIDAYS_FIXED = {
    # Mes, Día: Año Nuevo, Juneteenth, Independence Day, Christmas
    (1, 1): "New Year's Day",
    (6, 19): "Juneteenth",
    (7, 4): "Independence Day",
    (12, 25): "Christmas Day",
}

def is_us_market_holiday(d: date) -> bool:
    """Verifica si una fecha determinada es festivo en NYSE/NASDAQ."""
    # Sábado o domingo
    if d.weekday() >= 5:
        return True

    # Feriados fijos (con regla si cae en fin de semana)
    if (d.month, d.day) in US_HOLIDAYS_FIXED:
        return True

    # Observación de fin de semana: si cae en domingo, se observa el lunes
    if d.weekday() == 0:  # Lunes
        yesterday_tuple = (d.month, d.day - 1) if d.day > 1 else None
        if yesterday_tuple and yesterday_tuple in US_HOLIDAYS_FIXED:
            return True

    # Observación de fin de semana: si cae en sábado, se observa el viernes
    if d.weekday() == 4:  # Viernes
        tomorrow_tuple = (d.month, d.day + 1)
        if tomorrow_tuple in US_HOLIDAYS_FIXED:
            return True

    # Feriados móviles comunes en EE.UU.:
    # MLK: 3er lunes de enero
    if d.month == 1 and d.weekday() == 0 and 15 <= d.day <= 21:
        return True
    # Washington's Birthday (Presidents Day): 3er lunes de febrero
    if d.month == 2 and d.weekday() == 0 and 15 <= d.day <= 21:
        return True
    # Memorial Day: último lunes de mayo
    if d.month == 5 and d.weekday() == 0 and d.day >= 25:
        return True
    # Labor Day: 1er lunes de septiembre
    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True
    # Thanksgiving: 4to jueves de noviembre
    if d.month == 11 and d.weekday() == 3 and 22 <= d.day <= 28:
        return True

    return False

def is_market_open(asset_class: str, current_dt: datetime | None = None) -> bool:
    """
    Indica si el mercado correspondiente al activo está actualmente abierto.
    - Cripto: 24/7, siempre abierto.
    - Acciones / ETFs / Commodities: Lunes a Viernes 09:30 - 16:00 US/Eastern (excluyendo festivos).
    """
    if asset_class.lower() == "crypto":
        return True

    now = current_dt or datetime.now(TZ_US_EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ_US_EASTERN)
    else:
        now = now.astimezone(TZ_US_EASTERN)

    market_date = now.date()
    if is_us_market_holiday(market_date):
        return False

    market_open_time = time(9, 30)
    market_close_time = time(16, 0)
    current_time = now.time()

    return market_open_time <= current_time < market_close_time

def is_bar_closed(bar_timestamp: datetime | pd.Timestamp, asset_class: str, current_dt: datetime | None = None) -> bool:
    """
    Regla de integridad causal: Determina si una barra diaria está completamente CERRADA.
    Una vela del día en curso NO debe usarse para generar señales antes de su cierre oficial.
    """
    now = current_dt or datetime.now(TZ_UTC)
    if isinstance(bar_timestamp, str):
        bar_timestamp = pd.to_datetime(bar_timestamp)

    if asset_class.lower() == "crypto":
        # En cripto, la barra diaria cierra a las 23:59:59 UTC
        # Si la barra es de hoy UTC y aún no ha concluido el día UTC, es parcial
        bar_date = bar_timestamp.date() if hasattr(bar_timestamp, "date") else bar_timestamp
        current_date_utc = now.astimezone(TZ_UTC).date()
        return bar_date < current_date_utc

    # Acciones y ETFs (mercado estadounidense)
    now_et = now.astimezone(TZ_US_EASTERN)
    bar_date = bar_timestamp.date() if hasattr(bar_timestamp, "date") else bar_timestamp
    current_date_et = now_et.date()

    if bar_date < current_date_et:
        return True
    elif bar_date == current_date_et:
        # Es hoy: solo está cerrada si ya pasaron las 16:00 US/Eastern
        return now_et.time() >= time(16, 0)
    else:
        # Fecha en el futuro (anomalía de datos)
        return False

def filter_only_closed_bars(df: pd.DataFrame, asset_class: str, current_dt: datetime | None = None) -> pd.DataFrame:
    """
    Filtra rigurosamente un DataFrame eliminando la última barra si aún está en formación (parcial).
    Previene de raíz el Lookahead Bias y la distorsión de indicadores en tiempo real.
    """
    if df.empty:
        return df

    # Identificar columna o índice temporal
    if isinstance(df.index, pd.DatetimeIndex):
        last_timestamp = df.index[-1]
    else:
        last_timestamp = df["timestamp"].iloc[-1]

    if not is_bar_closed(last_timestamp, asset_class, current_dt):
        return df.iloc[:-1].copy()

    return df.copy()
