"""
Trading EZ - Registro de Modelos (Model Registry) y Esquema Campeón / Retador.
Gestión del ciclo de vida, persistencia, versionado con hash, tracking de métricas y rollback.
"""
from __future__ import annotations
import os
import json
import joblib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from src.core.config import settings, BASE_DIR
from src.ml.models import TradingMLPipeline, ModelMetrics

MODELS_DIR = BASE_DIR / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

class ModelRegistry:
    """
    Gestor del ciclo de vida de los modelos predictivos en producción.
    """

    def __init__(self, models_dir: Path | None = None):
        self.models_dir = Path(models_dir or MODELS_DIR)
        self.champion_file = self.models_dir / "champion.pkl"
        self.metadata_file = self.models_dir / "champion_metadata.json"
        self.history_dir = self.models_dir / "versions"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_champion(
        self,
        pipeline: TradingMLPipeline,
        version: str,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
    ) -> Dict[str, Any]:
        """Serializa el modelo como campeón y archiva una versión histórica para rollback."""
        if not pipeline.is_fitted or not pipeline.metrics:
            raise ValueError("No se puede registrar un modelo que no ha sido entrenado y validado.")

        m = pipeline.metrics
        metadata = {
            "version": version,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "model_type": pipeline.model_type,
            "calibration_method": pipeline.calibration_method,
            "train_period": f"{train_start} a {train_end}",
            "test_period": f"{test_start} a {test_end}",
            "is_validated": m.is_validated,
            "status": "VALIDADO" if m.is_validated else "SIN CALIBRAR",
            "metrics": {
                "is_auc": m.is_auc,
                "oos_auc": m.oos_auc,
                "auc_degradation_pct": m.auc_degradation_pct,
                "is_brier": m.is_brier,
                "oos_brier": m.oos_brier,
                "oos_win_rate_actual": m.oos_win_rate_actual,
            },
            "calibration": {
                "brier_score": m.calibration.brier_score,
                "auc_roc": m.calibration.auc_roc,
                "bins_predicted": m.calibration.bins_predicted,
                "bins_empirical": m.calibration.bins_empirical,
                "bin_counts": m.calibration.bin_counts,
                "status": m.calibration.status,
            },
            "top_features": sorted(m.feature_importances.items(), key=lambda x: x[1], reverse=True)[:10],
        }

        # 1. Guardar archivo activo campeón
        joblib.dump(pipeline, self.champion_file)
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 2. Archivar versión histórica
        version_model_path = self.history_dir / f"{version}.pkl"
        version_meta_path = self.history_dir / f"{version}.json"
        joblib.dump(pipeline, version_model_path)
        with open(version_meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return metadata

    def load_champion(self) -> Optional[Tuple[TradingMLPipeline, Dict[str, Any]]]:
        """Carga el modelo campeón actual y sus metadatos desde disco."""
        if not self.champion_file.exists() or not self.metadata_file.exists():
            return None

        try:
            pipeline = joblib.load(self.champion_file)
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return pipeline, metadata
        except Exception:
            return None

    def rollback_to_version(self, target_version: str) -> Dict[str, Any]:
        """Restaura una versión anterior archivada como el nuevo campeón."""
        version_model_path = self.history_dir / f"{target_version}.pkl"
        version_meta_path = self.history_dir / f"{target_version}.json"

        if not version_model_path.exists() or not version_meta_path.exists():
            raise FileNotFoundError(f"Versión de modelo '{target_version}' no encontrada en el archivo histórico.")

        # Copiar versión histórica a campeón
        pipeline = joblib.load(version_model_path)
        with open(version_meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        metadata["rollback_restored_at"] = datetime.now(timezone.utc).isoformat()

        joblib.dump(pipeline, self.champion_file)
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return metadata

    def list_available_versions(self) -> List[str]:
        """Lista todas las versiones disponibles para rollback."""
        return [p.stem for p in self.history_dir.glob("*.pkl")]

# Instancia global del registro
model_registry = ModelRegistry()
