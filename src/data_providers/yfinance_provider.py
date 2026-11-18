"""
Trading EZ - Proveedor de Datos Yahoo Finance (yfinance).
Descarga 5+ años de histórico ajustado por splits y dividendos, e intradía para detalle.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import yfinance as yf

from src.core.errors import ProviderError
from src.data_providers.base import BaseDataProvider
from src.data_providers.cache_manager import CacheManager
from src.data_providers.integrity import DataIntegrityAuditor

class YahooFinanceProvider(BaseDataProvider):
    """
    Proveedor de datos basado en Yahoo Finance.
    Ideal para prototipo rápido, cobertura universal y 5+ años de datos sin coste de suscripción.
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        auditor: Optional[DataIntegrityAuditor] = None,
    ):
        super().__init__("YahooFinance", cache_manager, auditor)

    def _format_symbol(self, symbol: str) -> str:
        """Formatea símbolos estándar al formato de Yahoo Finance."""
        sym = symbol.strip().upper()
        # Normalizar cripto si viene como BTC/USD o BTCUSDT
        if sym in ("BTC", "BITCOIN"):
            return "BTC-USD"
        if sym in ("ETH", "ETHEREUM"):
            return "ETH-USD"
        if sym in ("SOL", "SOLANA"):
            return "SOL-USD"
        return sym

    def _fetch_daily_remote(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        yf_symbol = self._format_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            # auto_adjust=True ajusta Open, High, Low, Close por splits y dividendos
            df = ticker.history(
                start=start.strftime("%Y-%m-%d"),
                end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=True,
                raise_errors=True,
            )

            if df.empty:
                raise ProviderError(self.name, symbol, "Yahoo Finance retornó un DataFrame vacío.")

            # Normalizar columnas a minúsculas
            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })

            # Asegurar índice UTC
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")

            # Cálculo de VWAP diario aproximado: (High + Low + Close) / 3
            df["vwap"] = (df["high"] + df["low"] + df["close"]) / 3.0

            # Mantener solo columnas requeridas
            return df[["open", "high", "low", "close", "volume", "vwap"]].copy()

        except Exception as e:
            raise ProviderError(self.name, symbol, f"Error descargando datos diarios: {str(e)}")

    def _fetch_intraday_remote(self, symbol: str, interval: str = "1h", days: int = 7) -> pd.DataFrame:
        yf_symbol = self._format_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            # yfinance permite hasta 60 días para 1h y 30 días para 15m
            period = f"{min(days, 59)}d"
            df = ticker.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })

            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")

            df["vwap"] = (df["high"] + df["low"] + df["close"]) / 3.0
            return df[["open", "high", "low", "close", "volume", "vwap"]].copy()

        except Exception as e:
            raise ProviderError(self.name, symbol, f"Error descargando datos intradía: {str(e)}")

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        yf_symbol = self._format_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            fast_info = getattr(ticker, "fast_info", None)

            price = None
            prev_close = None
            vol = None

            if fast_info:
                price = getattr(fast_info, "last_price", None)
                prev_close = getattr(fast_info, "previous_close", None)
                vol = getattr(fast_info, "last_volume", None)

            if price is None:
                # Fallback con última barra de 1d
                hist = ticker.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                    vol = float(hist["Volume"].iloc[-1])

            chg = (price - prev_close) if (price and prev_close) else 0.0
            chg_pct = (chg / prev_close * 100.0) if prev_close else 0.0

            return {
                "symbol": symbol,
                "price": round(float(price or 0.0), 4),
                "previous_close": round(float(prev_close or 0.0), 4),
                "change": round(float(chg), 4),
                "change_pct": round(float(chg_pct), 2),
                "volume": int(vol or 0),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "live",
            }
        except Exception as e:
            # Fallback seguro con última barra de caché
            cached = self.cache_manager.get_daily(symbol)
            if cached is not None:
                df, _ = cached
                last_bar = df.iloc[-1]
                prev_bar = df.iloc[-2] if len(df) > 1 else last_bar
                chg = float(last_bar["close"] - prev_bar["close"])
                chg_pct = (chg / float(prev_bar["close"])) * 100.0 if prev_bar["close"] > 0 else 0.0
                return {
                    "symbol": symbol,
                    "price": round(float(last_bar["close"]), 4),
                    "previous_close": round(float(prev_bar["close"]), 4),
                    "change": round(chg, 4),
                    "change_pct": round(chg_pct, 2),
                    "volume": int(last_bar["volume"]),
                    "timestamp": df.index[-1].isoformat(),
                    "source": "stale",
                }
            raise ProviderError(self.name, symbol, f"No se pudo obtener cotización: {str(e)}")
