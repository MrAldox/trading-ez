"""
Trading EZ - Cargador Central de Configuración Tipada.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field

# Rutas base relativas a la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

class AssetMetadata(BaseModel):
    symbol: str
    name: str
    asset_class: str = "stocks"  # stocks, etfs, crypto, commodities
    sector: str = "General"
    market: str = "NASDAQ"
    currency: str = "USD"
    tick_size: float = 0.01
    est_cost_bps: float = 5.0    # Comisión + spread estimado en puntos básicos
    is_active: bool = True

class AppSettings(BaseModel):
    name: str = "Trading EZ"
    version: str = "1.0.0"
    description: str = "Market Terminal Pro"
    env: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"

class ThresholdSettings(BaseModel):
    min_calibrated_prob: float = 0.60
    min_expectancy_r: float = 0.15
    min_risk_reward: float = 1.5
    max_stale_hours_stocks: float = 24.0
    max_stale_hours_crypto: float = 4.0

class SizingSettings(BaseModel):
    default_capital: float = 10000.0
    default_risk_pct: float = 1.0
    max_position_size_pct: float = 25.0
    max_open_positions: int = 5
    max_daily_loss_pct: float = 3.0
    consecutive_losses_circuit: int = 4

class DataSettings(BaseModel):
    cache_dir: str = "data/cache"
    db_path: str = "data/db/trading_ez.db"
    history_years: int = 5
    max_price_jump_pct: float = 0.40
    max_gap_business_days: int = 4
    default_provider: str = "yahoo"

class MLSettings(BaseModel):
    calibration_method: str = "isotonic"
    walk_forward_splits: int = 5
    train_years: int = 3
    test_months: int = 6
    embargo_days: int = 5
    psi_drift_threshold: float = 0.20
    min_trades_for_validation: int = 100
    min_profit_factor_validation: float = 1.3

class Config(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)
    sizing: SizingSettings = Field(default_factory=SizingSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    universe: List[AssetMetadata] = Field(default_factory=list)

    @property
    def assets_by_symbol(self) -> Dict[str, AssetMetadata]:
        return {a.symbol: a for a in self.universe}

def load_config() -> Config:
    """Carga universe.yaml y settings.yaml con sobreescritura de variables de entorno."""
    settings_path = CONFIG_DIR / "settings.yaml"
    universe_path = CONFIG_DIR / "universe.yaml"

    settings_dict: Dict[str, Any] = {}
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            settings_dict = yaml.safe_load(f) or {}

    universe_list: List[Dict[str, Any]] = []
    if universe_path.exists():
        with open(universe_path, "r", encoding="utf-8") as f:
            raw_univ = yaml.safe_load(f) or {}
            universe_list = raw_univ.get("assets", [])

    # Sobreescrituras de entorno para Render / Docker
    if "PORT" in os.environ:
        settings_dict.setdefault("app", {})["port"] = int(os.environ["PORT"])
    if "HOST" in os.environ:
        settings_dict.setdefault("app", {})["host"] = os.environ["HOST"]
    if "DATA_CACHE_DIR" in os.environ:
        settings_dict.setdefault("data", {})["cache_dir"] = os.environ["DATA_CACHE_DIR"]
    if "DATABASE_URL" in os.environ:
        settings_dict.setdefault("data", {})["db_path"] = os.environ["DATABASE_URL"]

    config = Config(
        app=AppSettings(**settings_dict.get("app", {})),
        thresholds=ThresholdSettings(**settings_dict.get("thresholds", {})),
        sizing=SizingSettings(**settings_dict.get("sizing", {})),
        data=DataSettings(**settings_dict.get("data", {})),
        ml=MLSettings(**settings_dict.get("ml", {})),
        universe=[AssetMetadata(**item) for item in universe_list],
    )

    # Asegurar que existan directorios de persistencia
    (BASE_DIR / config.data.cache_dir / "daily").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / config.data.cache_dir / "intraday").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data" / "db").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data" / "models").mkdir(parents=True, exist_ok=True)

    return config

# Instancia global accesible
settings = load_config()
