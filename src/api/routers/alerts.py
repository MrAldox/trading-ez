"""
Trading EZ - Router de Alertas de Precios (FastAPI).
"""
from __future__ import annotations
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.database import SessionLocal
from src.db.models import AlertModel

router = APIRouter(prefix="/api/alerts", tags=["Alertas"])

class AlertRequest(BaseModel):
    symbol: str
    condition: str = "ABOVE"  # ABOVE | BELOW
    target_value: float

@router.get("")
def list_alerts():
    db = SessionLocal()
    try:
        alerts = db.query(AlertModel).all()
        return {
            "alerts": [
                {
                    "id": a.id,
                    "symbol": a.symbol,
                    "condition": a.condition,
                    "target_value": a.target_value,
                    "is_active": a.is_active,
                    "is_triggered": a.is_triggered,
                    "created_at": a.created_at.isoformat(),
                }
                for a in alerts
            ]
        }
    finally:
        db.close()

@router.post("")
def create_alert(req: AlertRequest):
    db = SessionLocal()
    try:
        alert = AlertModel(
            id=f"alt_{uuid.uuid4().hex[:10]}",
            symbol=req.symbol.upper(),
            condition=req.condition.upper(),
            target_value=req.target_value,
            is_active=True,
            is_triggered=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return {"id": alert.id, "message": f"Alerta creada para {alert.symbol} {alert.condition} ${alert.target_value}"}
    finally:
        db.close()

@router.delete("/{alert_id}")
def delete_alert(alert_id: str):
    db = SessionLocal()
    try:
        a = db.query(AlertModel).filter_by(id=alert_id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")
        db.delete(a)
        db.commit()
        return {"message": "Alerta eliminada con éxito."}
    finally:
        db.close()
