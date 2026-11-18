"""
Trading EZ - Interfaz Base de Proveedores de Datos de Mercado.
Garantiza un contrato uniforme, auditoría automática de integridad y degradación elegante a caché.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd

from src.core.errors import ProviderError
from src.core.calendar import filter_only_closed_bars
from src.data_providers.cache_manager import CacheManager
from src.data_providers.integrity import DataIntegrityAuditor, AuditReport

class BaseDataProvider(ABC):
    """
    Clase abstracta para todo proveedor de datos (Yahoo Finance, Alpaca, Binance, etc.).
    Implementa el flujo:
    1. Consulta caché rápida.
    2. Si falta o expiró, consulta proveedor remoto.
    3. Audita y limpia la respuesta.
    4. Si falla la red, recurre a la última caché y etiqueta como 'stale'.
    5. Guarda en Parquet.
    """

    def __init__(
        self,
        name: str,
        cache_manager: Optional[CacheManager] = None,
        auditor: Optional[DataIntegrityAuditor] = None,
    ):
        self.name = name
        self.cache_manager = cache_manager or CacheManager()
        self.auditor = auditor or DataIntegrityAuditor()

    @abstractmethod
    def _fetch_daily_remote(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Implementación concreta de descarga diaria desde la API."""
        pass

    @abstractmethod
    def _fetch_intraday_remote(self, symbol: str, interval: str, days: int) -> pd.DataFrame:
        """Implementación concreta de descarga intradía desde la API."""
        pass

    @abstractmethod
    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Obtiene la cotización instantánea más reciente (precio, bid, ask, volumen)."""
        pass

    def fetch_daily(
        self,
        symbol: str,
        start_date: str | datetime | None = None,
        end_date: str | datetime | None = None,
        asset_class: str = "stocks",
        force_refresh: bool = False,
    ) -> tuple[pd.DataFrame, str, AuditReport]:
        """
        Descarga datos diarios asegurando:
        - Auditoría de datos.
        - Filtrado de velas parciales del día en curso.
        - Fallback automático a 'stale' si la API externa falla.
        Retorna: (DataFrame, data_source ['live'|'cache'|'stale'], AuditReport)
        """
        # Fechas por defecto: 5 años atrás hasta hoy
        now = datetime.now()
        start = pd.to_datetime(start_date or (now - timedelta(days=5 * 365 + 30)), utc=True).to_pydatetime()
        end = pd.to_datetime(end_date or now, utc=True).to_pydatetime()

        # 1. Verificar si la caché está fresca (a menos que se fuerce refresco)
        if not force_refresh:
            cached_res = self.cache_manager.get_daily(symbol)
            if cached_res is not None:
                cached_df, source = cached_res
                # Filtrar rango solicitado
                sliced = cached_df.loc[
                    (cached_df.index >= start) & (cached_df.index <= end)
                ]
                if not sliced.empty:
                    clean_df, report = self.auditor.audit_and_clean(sliced, symbol, asset_class=asset_class)
                    return clean_df, source, report

        # 2. Descargar de la API remota
        try:
            raw_df = self._fetch_daily_remote(symbol, start, end)
            if raw_df is None or raw_df.empty:
                raise ProviderError(self.name, symbol, "La API devolvió un dataset vacío.")

            # Filtrar barras parciales si el mercado está abierto
            closed_df = filter_only_closed_bars(raw_df, asset_class)

            # Auditar y limpiar
            clean_df, report = self.auditor.audit_and_clean(closed_df, symbol, asset_class=asset_class)

            # Guardar en caché Parquet
            self.cache_manager.merge_and_save_daily(symbol, clean_df, source="live")
            return clean_df, "live", report

        except Exception as e:
            # Fallback elegante a la última versión en disco
            fallback = self.cache_manager.get_daily(symbol, max_age_hours=999999.0)
            if fallback is not None:
                df_fallback, _ = fallback
                clean_df, report = self.auditor.audit_and_clean(df_fallback, symbol, asset_class=asset_class)
                report.warnings.append(f"Fallback a caché por fallo de API: {str(e)}")
                return clean_df, "stale", report

            raise ProviderError(self.name, symbol, f"Fallo al descargar y no existe caché local disponible: {str(e)}")
