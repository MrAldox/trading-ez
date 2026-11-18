"""
Trading EZ - Gestor Dual de Caché (Memoria RAM con TTL + Disco Parquet).
Evita llamadas redundantes a APIs externas y soporta modo offline con datos "stale" si la red cae.
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from src.core.config import settings, BASE_DIR

class MemoryCacheItem:
    def __init__(self, data: pd.DataFrame, source: str, ttl_seconds: float):
        self.data = data
        self.source = source
        self.expires_at = time.time() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class CacheManager:
    """
    Gestor de almacenamiento y recuperación de datos de mercado con doble capa:
    1. Memoria RAM (LRU/TTL): ultra rápido para peticiones web concurrentes.
    2. Disco (Apache Parquet): persistente, comprimido y eficiente entre reinicios.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        memory_ttl_seconds: float = 60.0,
    ):
        self.cache_dir = Path(cache_dir or (BASE_DIR / settings.data.cache_dir))
        self.daily_dir = self.cache_dir / "daily"
        self.intraday_dir = self.cache_dir / "intraday"
        self.memory_ttl_seconds = memory_ttl_seconds
        self._memory_cache: Dict[str, MemoryCacheItem] = {}

        # Asegurar existencia de directorios
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.intraday_dir.mkdir(parents=True, exist_ok=True)

    def _get_daily_parquet_path(self, symbol: str) -> Path:
        safe_sym = symbol.replace("/", "_").replace("^", "_").upper()
        return self.daily_dir / f"{safe_sym}.parquet"

    def _get_intraday_parquet_path(self, symbol: str, interval: str) -> Path:
        safe_sym = symbol.replace("/", "_").replace("^", "_").upper()
        return self.intraday_dir / f"{safe_sym}_{interval}.parquet"

    def get_from_memory(self, cache_key: str) -> Optional[tuple[pd.DataFrame, str]]:
        """Recupera DataFrame desde memoria RAM si el TTL no ha expirado."""
        item = self._memory_cache.get(cache_key)
        if item and not item.is_expired:
            return item.data.copy(), item.source
        return None

    def set_memory(self, cache_key: str, df: pd.DataFrame, source: str, ttl: Optional[float] = None) -> None:
        """Almacena DataFrame en memoria RAM con TTL configurable."""
        ttl_val = ttl if ttl is not None else self.memory_ttl_seconds
        self._memory_cache[cache_key] = MemoryCacheItem(df.copy(), source, ttl_val)

    def get_daily(self, symbol: str, max_age_hours: Optional[float] = None) -> Optional[tuple[pd.DataFrame, str]]:
        """
        Recupera datos diarios. Orden de búsqueda:
        1. Memoria RAM
        2. Disco Parquet
        Retorna (df, "cache" | "stale") o None si no existe.
        """
        cache_key = f"daily_{symbol.upper()}"

        # 1. Chequeo de memoria
        mem_res = self.get_from_memory(cache_key)
        if mem_res is not None:
            return mem_res

        # 2. Chequeo de disco
        file_path = self._get_daily_parquet_path(symbol)
        if not file_path.exists():
            return None

        try:
            df = pd.read_parquet(file_path)
            if df.empty:
                return None

            # Determinar si los datos en disco son considerados "stale"
            file_mtime = file_path.stat().st_mtime
            age_hours = (time.time() - file_mtime) / 3600.0

            limit_hours = max_age_hours or (
                settings.thresholds.max_stale_hours_crypto
                if "USD" in symbol or "BTC" in symbol
                else settings.thresholds.max_stale_hours_stocks
            )

            source = "stale" if age_hours > limit_hours else "cache"

            # Guardar en memoria para siguientes consultas
            self.set_memory(cache_key, df, source)
            return df, source

        except Exception as e:
            return None

    def save_daily(self, symbol: str, df: pd.DataFrame, source: str = "cache") -> None:
        """Guarda en disco (Parquet) y actualiza la caché en memoria."""
        if df is None or df.empty:
            return

        file_path = self._get_daily_parquet_path(symbol)
        # Asegurar tipos y nombres
        save_df = df.copy()
        if not isinstance(save_df.index, pd.DatetimeIndex) and "timestamp" in save_df.columns:
            save_df = save_df.set_index("timestamp")

        # Escribir a Parquet con compresión Snappy
        save_df.to_parquet(file_path, engine="pyarrow", compression="snappy")

        # Refrescar memoria
        cache_key = f"daily_{symbol.upper()}"
        self.set_memory(cache_key, save_df, source)

    def merge_and_save_daily(self, symbol: str, new_df: pd.DataFrame, source: str = "live") -> pd.DataFrame:
        """
        Combina nuevos datos con los existentes en disco, eliminando duplicados
        y conservando la barra más reciente de cada fecha.
        """
        existing_res = self.get_daily(symbol, max_age_hours=999999.0)
        if existing_res is not None:
            existing_df, _ = existing_res
            combined = pd.concat([existing_df, new_df])
            # Deduplicar conservando la última ocurrencia
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        else:
            combined = new_df.sort_index()

        self.save_daily(symbol, combined, source=source)
        return combined

    def clear_memory(self) -> None:
        """Limpia la memoria RAM."""
        self._memory_cache.clear()
