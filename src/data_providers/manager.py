"""
Trading EZ - Gestor Centralizado de Proveedores de Datos.
Enruta automáticamente cada activo al proveedor más idóneo y coordina auditoría y caché.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd

from src.core.config import settings, AssetMetadata
from src.core.errors import ProviderError
from src.data_providers.base import BaseDataProvider
from src.data_providers.cache_manager import CacheManager
from src.data_providers.integrity import DataIntegrityAuditor, AuditReport
from src.data_providers.yfinance_provider import YahooFinanceProvider
from src.data_providers.binance_provider import BinanceDataProvider
from src.data_providers.alpaca_provider import AlpacaDataProvider
from src.data_providers.finnhub_provider import FinnhubProvider

class DataProviderManager:
    """
    Punto de entrada único para la adquisición de datos de mercado en todo el sistema.
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or CacheManager()
        self.auditor = DataIntegrityAuditor(
            max_price_jump_pct=settings.data.max_price_jump_pct,
            max_gap_business_days=settings.data.max_gap_business_days,
            max_stale_hours_stocks=settings.thresholds.max_stale_hours_stocks,
            max_stale_hours_crypto=settings.thresholds.max_stale_hours_crypto,
        )
        self.yfinance = YahooFinanceProvider(self.cache_manager, self.auditor)
        self.binance = BinanceDataProvider(self.cache_manager, self.auditor)
        self.alpaca = AlpacaDataProvider(cache_manager=self.cache_manager, auditor=self.auditor)
        self.finnhub = FinnhubProvider()

    def get_provider_for_asset(self, asset: AssetMetadata) -> BaseDataProvider:
        """Selecciona el proveedor más eficiente según la clase de activo."""
        if asset.asset_class == "crypto":
            # Para cripto, intentamos Binance o Yahoo
            return self.binance
        if asset.asset_class == "stocks" and self.alpaca.is_configured:
            return self.alpaca
        # Por defecto Yahoo Finance para prototipo y cobertura amplia de 5+ años
        return self.yfinance

    def fetch_daily_data(
        self,
        symbol: str,
        start_date: Optional[str | datetime] = None,
        end_date: Optional[str | datetime] = None,
        force_refresh: bool = False,
    ) -> tuple[pd.DataFrame, str, AuditReport]:
        """
        Descarga datos diarios para cualquier activo del universo configurado o símbolo arbitrario.
        """
        asset = settings.assets_by_symbol.get(symbol)
        asset_class = asset.asset_class if asset else ("crypto" if "-USD" in symbol or "BTC" in symbol else "stocks")

        provider = self.get_provider_for_asset(asset) if asset else self.yfinance

        try:
            return provider.fetch_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                asset_class=asset_class,
                force_refresh=force_refresh,
            )
        except Exception:
            # Fallback cruzado a Yahoo Finance si otro proveedor falla
            if provider != self.yfinance:
                return self.yfinance.fetch_daily(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    asset_class=asset_class,
                    force_refresh=force_refresh,
                )
            raise

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Obtiene cotización en tiempo real."""
        asset = settings.assets_by_symbol.get(symbol)
        provider = self.get_provider_for_asset(asset) if asset else self.yfinance
        try:
            return provider.fetch_quote(symbol)
        except Exception:
            return self.yfinance.fetch_quote(symbol)

# Instancia global del gestor de datos
data_manager = DataProviderManager()
