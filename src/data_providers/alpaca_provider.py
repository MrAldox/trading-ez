"""
Trading EZ - Proveedor de Datos Alpaca Markets (Data API v2).
Soporta datos institucionales de acciones US y paper trading.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests
import pandas as pd

from src.core.errors import ProviderError
from src.data_providers.base import BaseDataProvider
from src.data_providers.cache_manager import CacheManager
from src.data_providers.integrity import DataIntegrityAuditor

class AlpacaDataProvider(BaseDataProvider):
    """
    Proveedor para acciones de EE.UU. a través de Alpaca Data API v2.
    Si no hay credenciales en el entorno, delega transparentemente en el fallback local.
    """
    DATA_URL = "https://data.alpaca.markets/v2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        cache_manager: Optional[CacheManager] = None,
        auditor: Optional[DataIntegrityAuditor] = None,
    ):
        super().__init__("Alpaca", cache_manager, auditor)
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")

    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def _fetch_daily_remote(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        if not self.is_configured:
            raise ProviderError(self.name, symbol, "Claves de Alpaca (ALPACA_API_KEY) no configuradas.")

        url = f"{self.DATA_URL}/stocks/{symbol}/bars"
        params = {
            "timeframe": "1Day",
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "adjustment": "all",
            "feed": "iex",
        }

        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=10)
            if resp.status_code != 200:
                raise ProviderError(self.name, symbol, f"HTTP {resp.status_code}: {resp.text}")

            data = resp.json().get("bars", [])
            if not data:
                raise ProviderError(self.name, symbol, "Sin datos devueltos por Alpaca.")

            rows = []
            for b in data:
                rows.append({
                    "timestamp": pd.to_datetime(b["t"], utc=True),
                    "open": float(b["o"]),
                    "high": float(b["h"]),
                    "low": float(b["l"]),
                    "close": float(b["c"]),
                    "volume": float(b["v"]),
                    "vwap": float(b.get("vw", (b["h"] + b["l"] + b["c"]) / 3.0)),
                })

            df = pd.DataFrame(rows).set_index("timestamp").sort_index()
            return df

        except Exception as e:
            raise ProviderError(self.name, symbol, str(e))

    def _fetch_intraday_remote(self, symbol: str, interval: str = "1h", days: int = 7) -> pd.DataFrame:
        if not self.is_configured:
            raise ProviderError(self.name, symbol, "Claves de Alpaca no configuradas.")

        timeframe_map = {"1h": "1Hour", "15m": "15Min", "5m": "5Min"}
        tf = timeframe_map.get(interval, "1Hour")
        url = f"{self.DATA_URL}/stocks/{symbol}/bars"
        params = {
            "timeframe": tf,
            "limit": min(days * 24, 1000),
            "adjustment": "all",
        }
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=10)
            if resp.status_code != 200:
                raise ProviderError(self.name, symbol, f"HTTP {resp.status_code}")

            data = resp.json().get("bars", [])
            rows = []
            for b in data:
                rows.append({
                    "timestamp": pd.to_datetime(b["t"], utc=True),
                    "open": float(b["o"]),
                    "high": float(b["h"]),
                    "low": float(b["l"]),
                    "close": float(b["c"]),
                    "volume": float(b["v"]),
                    "vwap": float(b.get("vw", (b["h"] + b["l"] + b["c"]) / 3.0)),
                })
            return pd.DataFrame(rows).set_index("timestamp").sort_index()
        except Exception as e:
            raise ProviderError(self.name, symbol, str(e))

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        if not self.is_configured:
            cached = self.cache_manager.get_daily(symbol)
            if cached:
                df, _ = cached
                last = df.iloc[-1]
                return {
                    "symbol": symbol,
                    "price": float(last["close"]),
                    "volume": int(last["volume"]),
                    "timestamp": df.index[-1].isoformat(),
                    "source": "stale",
                }
            raise ProviderError(self.name, symbol, "Sin claves ni caché.")

        url = f"{self.DATA_URL}/stocks/{symbol}/quotes/latest"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=5)
            if resp.status_code == 200:
                q = resp.json().get("quote", {})
                mid = (float(q.get("ap", 0)) + float(q.get("bp", 0))) / 2.0
                return {
                    "symbol": symbol,
                    "price": round(mid, 4),
                    "ask": float(q.get("ap", 0)),
                    "bid": float(q.get("bp", 0)),
                    "timestamp": q.get("t", datetime.now(timezone.utc).isoformat()),
                    "source": "live",
                }
            raise ProviderError(self.name, symbol, f"HTTP {resp.status_code}")
        except Exception as e:
            raise ProviderError(self.name, symbol, str(e))
