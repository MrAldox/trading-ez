"""
Trading EZ - Auditor de Integridad y Validación de Datos de Mercado.
Garantiza que ningún dato corrupto, desactualizado o no verificado alimente el motor cuantitativo.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from src.core.errors import DataIntegrityError, DataStaleError
from src.core.calendar import is_us_market_holiday

@dataclass
class AuditReport:
    """Informe detallado del chequeo de integridad de un conjunto de datos."""
    symbol: str
    is_valid: bool
    total_bars: int
    first_timestamp: Optional[pd.Timestamp] = None
    last_timestamp: Optional[pd.Timestamp] = None
    issues_found: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    repaired_rows_dropped: int = 0
    is_stale: bool = False
    stale_hours: float = 0.0

class DataIntegrityAuditor:
    """
    Auditor riguroso de series temporales OHLCV.
    Reglas inviolables:
    - Precios deben ser estrictamente positivos (> 0).
    - Geometría de velas: High >= max(Open, Close) y Low <= min(Open, Close).
    - Saltos inexplicables (> 40% de un día a otro) se detectan y aíslan.
    - No puede haber duplicados temporales ni desorden cronológico.
    - Se verifica si los datos están desactualizados (stale).
    """

    def __init__(
        self,
        max_price_jump_pct: float = 0.40,
        max_gap_business_days: int = 4,
        max_stale_hours_stocks: float = 24.0,
        max_stale_hours_crypto: float = 4.0,
    ):
        self.max_price_jump_pct = max_price_jump_pct
        self.max_gap_business_days = max_gap_business_days
        self.max_stale_hours_stocks = max_stale_hours_stocks
        self.max_stale_hours_crypto = max_stale_hours_crypto

    def audit_and_clean(
        self,
        df: pd.DataFrame,
        symbol: str,
        asset_class: str = "stocks",
        auto_repair: bool = True,
        strict_raise: bool = False,
    ) -> tuple[pd.DataFrame, AuditReport]:
        """
        Audita el DataFrame y opcionalmente descarta anomalías menores (duplicados, ceros aislados).
        Retorna (DataFrame limpio, AuditReport).
        """
        issues: List[str] = []
        if df is None or df.empty:
            report = AuditReport(symbol=symbol, is_valid=False, total_bars=0, issues_found=["DataFrame vacío o nulo"])
            if strict_raise:
                raise DataIntegrityError(symbol, "DataFrame vacío o nulo")
            return pd.DataFrame(), report

        clean_df = df.copy()

        # 1. Normalización de nombres de columnas
        clean_df.columns = [c.lower() for c in clean_df.columns]
        req_cols = {"open", "high", "low", "close", "volume"}
        missing_cols = req_cols - set(clean_df.columns)
        if missing_cols:
            msg = f"Columnas faltantes: {missing_cols}"
            issues.append(msg)
            if strict_raise:
                raise DataIntegrityError(symbol, msg)
            return pd.DataFrame(), AuditReport(symbol=symbol, is_valid=False, total_bars=len(clean_df), issues_found=issues)

        # 2. Manejo de índice temporal
        if "timestamp" in clean_df.columns and not isinstance(clean_df.index, pd.DatetimeIndex):
            clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"], utc=True)
            clean_df = clean_df.set_index("timestamp")
        elif isinstance(clean_df.index, pd.DatetimeIndex):
            clean_df.index = pd.to_datetime(clean_df.index, utc=True)

        initial_len = len(clean_df)

        # 3. Deduplicación y orden cronológico
        if clean_df.index.duplicated().any():
            dup_count = int(clean_df.index.duplicated().sum())
            issues.append(f"Se encontraron {dup_count} fechas duplicadas. Deduplicando conservando la última.")
            clean_df = clean_df[~clean_df.index.duplicated(keep="last")]

        clean_df = clean_df.sort_index()

        # 4. Chequeo de nulos e infinitos
        null_mask = clean_df[["open", "high", "low", "close"]].isna().any(axis=1) | np.isinf(clean_df[["open", "high", "low", "close"]]).any(axis=1)
        if null_mask.any():
            null_count = int(null_mask.sum())
            issues.append(f"{null_count} filas contienen valores NaN o infinitos.")
            if auto_repair:
                clean_df = clean_df[~null_mask]
            elif strict_raise:
                raise DataIntegrityError(symbol, f"{null_count} filas con valores NaN/Infinitos.")

        # 5. Precios estrictamente positivos
        neg_or_zero = (clean_df[["open", "high", "low", "close"]] <= 0).any(axis=1)
        if neg_or_zero.any():
            count = int(neg_or_zero.sum())
            issues.append(f"{count} filas contienen precios <= 0.")
            if auto_repair:
                clean_df = clean_df[~neg_or_zero]
            elif strict_raise:
                raise DataIntegrityError(symbol, f"Se detectaron {count} barras con precios cero o negativos.")

        # 6. Geometría de velas (High >= max(Open, Close), Low <= min(Open, Close))
        invalid_geom = (
            (clean_df["high"] < clean_df["low"]) |
            (clean_df["high"] < clean_df["open"]) |
            (clean_df["high"] < clean_df["close"]) |
            (clean_df["low"] > clean_df["open"]) |
            (clean_df["low"] > clean_df["close"])
        )
        if invalid_geom.any():
            geom_count = int(invalid_geom.sum())
            issues.append(f"{geom_count} velas con geometría inválida (High < Low o Apertura/Cierre fuera de rango).")
            if auto_repair:
                clean_df = clean_df[~invalid_geom]
            elif strict_raise:
                raise DataIntegrityError(symbol, f"Geometría de vela inválida en {geom_count} barras.")

        # 7. Saltos extremos inexplicables (> max_price_jump_pct, p. ej. 40%)
        if len(clean_df) > 1:
            ret = clean_df["close"].pct_change().abs()
            extreme_jumps = ret > self.max_price_jump_pct
            if extreme_jumps.any():
                jump_count = int(extreme_jumps.sum())
                jump_dates = clean_df.index[extreme_jumps].strftime("%Y-%m-%d").tolist()
                issues.append(f"Se detectaron {jump_count} saltos extremos de precio (> {self.max_price_jump_pct*100:.0f}%): {jump_dates[:3]}")

        # 8. Verificación de obsolescencia (Stale check)
        is_stale = False
        stale_hours = 0.0
        warnings: List[str] = []
        if not clean_df.empty:
            last_dt = clean_df.index[-1].to_pydatetime()
            now_utc = datetime.now(timezone.utc)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)

            delta = now_utc - last_dt
            stale_hours = max(0.0, delta.total_seconds() / 3600.0)

            max_allowed = self.max_stale_hours_crypto if asset_class.lower() == "crypto" else self.max_stale_hours_stocks
            # Si el último timestamp es más antiguo que max_allowed, se marca stale
            if asset_class.lower() == "stocks" and now_utc.weekday() in (0, 6): # Fin de semana / Lunes
                max_allowed += 48.0

            if stale_hours > max_allowed:
                is_stale = True
                warnings.append(f"Datos obsoletos: última barra tiene {stale_hours:.1f}h de antigüedad (máx {max_allowed:.1f}h).")

        rows_dropped = initial_len - len(clean_df)
        # is_valid representa si la geometría y matemáticas del DataFrame son sanas y utilizables
        is_valid = len(clean_df) > 0 and (auto_repair or len(issues) == 0)

        report = AuditReport(
            symbol=symbol,
            is_valid=is_valid,
            total_bars=len(clean_df),
            first_timestamp=clean_df.index[0] if not clean_df.empty else None,
            last_timestamp=clean_df.index[-1] if not clean_df.empty else None,
            issues_found=issues,
            warnings=warnings,
            repaired_rows_dropped=rows_dropped,
            is_stale=is_stale,
            stale_hours=stale_hours,
        )

        return clean_df, report
