"""
Trading EZ - Proveedor de Datos Cripto Binance (REST API Pública).
Descarga velas 24/7 sin necesidad obligatoria de API key para datos públicos.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests
import pandas as pd

from src.core.errors import ProviderError
from src.data_providers.base import BaseDataProvider
from src.data_providers.cache_manager import CacheManager
from src.data_providers.integrity import DataIntegrityAuditor

class BinanceDataProvider(BaseDataProvider):
    """
    Proveedor para activos cripto utilizando la API pública de Binance spot.
    No requiere claves para consultar OHLCV y cotizaciones en vivo.
    """
    BASE_URL = "https://api.binance.com"

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        auditor: Optional[DataIntegrityAuditor] = None,
    ):
        super().__init__("Binance", cache_manager, auditor)

    def _normalize_symbol(self, symbol: str) -> str:
        """Convierte BTC-USD o BTC/USDT a BTCUSDT."""
        clean = symbol.upper().replace("-USD", "USDT").replace("/USD", "USDT").replace("-", "").replace("/", "")
        if not clean.endswith("USDT") and not clean.endswith("BUSD"):
            clean = clean + "USDT"
        return clean

    def _fetch_daily_remote(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        binance_sym = self._normalize_symbol(symbol)
        start_ms = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)

        url = f"{self.BASE_URL}/api/v3/klines"
        rows = []
        current_start_ms = start_ms

        try:
            while current_start_ms < end_ms:
                params = {
                    "symbol": binance_sym,
                    "interval": "1d",
                    "startTime": current_start_ms,
                    "endTime": end_ms,
                    "limit": 1000,
                }
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code != 200:
                    break

                data = resp.json()
                if not data or not isinstance(data, list):
                    break

                for k in data:
                    rows.append({
                        "timestamp": pd.to_datetime(k[0], unit="ms", utc=True),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "vwap": (float(k[2]) + float(k[3]) + float(k[4])) / 3.0,
                    })

                # Si recibimos menos de 1000 barras, ya alcanzamos el final
                if len(data) < 1000:
                    break

                # Avanzar al siguiente milisegundo después del último kline
                current_start_ms = int(data[-1][0]) + 86400000

            if not rows:
                raise ProviderError(self.name, symbol, "Respuesta vacía de Binance.")

            df = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"]).set_index("timestamp").sort_index()
            return df

        except Exception as e:
            raise ProviderError(self.name, symbol, f"Error descargando datos Binance: {str(e)}")

    def _fetch_intraday_remote(self, symbol: str, interval: str = "1h", days: int = 7) -> pd.DataFrame:
        binance_sym = self._normalize_symbol(symbol)
        url = f"{self.BASE_URL}/api/v3/klines"
        params = {
            "symbol": binance_sym,
            "interval": interval,
            "limit": min(days * 24, 1000),
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                raise ProviderError(self.name, symbol, f"HTTP {resp.status_code}")

            data = resp.json()
            rows = []
            for k in data:
                rows.append({
                    "timestamp": pd.to_datetime(k[0], unit="ms", utc=True),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "vwap": (float(k[2]) + float(k[3]) + float(k[4])) / 3.0,
                })

            return pd.DataFrame(rows).set_index("timestamp").sort_index()
        except Exception as e:
            raise ProviderError(self.name, symbol, f"Error intradía Binance: {str(e)}")

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        binance_sym = self._normalize_symbol(symbol)
        url = f"{self.BASE_URL}/api/v3/ticker/24hr"
        try:
            resp = requests.get(url, params={"symbol": binance_sym}, timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                return {
                    "symbol": symbol,
                    "price": round(float(d.get("lastPrice", 0)), 4),
                    "previous_close": round(float(d.get("prevClosePrice", 0)), 4),
                    "change": round(float(d.get("priceChange", 0)), 4),
                    "change_pct": round(float(d.get("priceChangePercent", 0)), 2),
                    "volume": round(float(d.get("volume", 0)), 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "live",
                }
            raise ProviderError(self.name, symbol, f"HTTP {resp.status_code}")
        except Exception as e:
            # Fallback a caché
            cached = self.cache_manager.get_daily(symbol)
            if cached is not None:
                df, _ = cached
                last = df.iloc[-1]
                return {
                    "symbol": symbol,
                    "price": float(last["close"]),
                    "change": 0.0,
                    "change_pct": 0.0,
                    "volume": float(last["volume"]),
                    "timestamp": df.index[-1].isoformat(),
                    "source": "stale",
                }
            raise ProviderError(self.name, symbol, str(e))
