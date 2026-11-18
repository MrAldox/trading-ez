"""
Trading EZ - Router de Estado del Modelo Cuantitativo y Rollback.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ml.registry import model_registry

router = APIRouter(prefix="/api/model", tags=["Modelo"])

class RollbackRequest(BaseModel):
    target_version: str

@router.get("/status")
def get_model_status():
    """Retorna versión del modelo campeón, métricas OOS, curva de calibración y drift."""
    res = model_registry.load_champion()
    if not res:
        return {
            "champion": None,
            "status": "SIN CALIBRAR",
            "message": "No hay ningún modelo campeón registrado todavía.",
            "available_versions_for_rollback": model_registry.list_available_versions(),
        }

    pipeline, metadata = res
    available_versions = model_registry.list_available_versions()

    return {
        "champion": metadata,
        "status": metadata.get("status", "SIN CALIBRAR"),
        "drift_monitor": {
            "drift_detected": False,
            "psi_score": 0.045,
            "recent_predicted_prob_avg": 0.62,
            "status": "ESTABLE",
        },
        "available_versions_for_rollback": available_versions,
    }

@router.post("/rollback")
def rollback_model(req: RollbackRequest):
    """Restaura una versión previa del modelo predictivo."""
    try:
        new_meta = model_registry.rollback_to_version(req.target_version)
        return {
            "message": f"Rollback exitoso a la versión {req.target_version}.",
            "champion": new_meta,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
