"""
Trading EZ - Diario de Operaciones (Trading Journal).
Permite registrar reflexiones, notas del trader y comparar lo que predijo la señal vs lo que ocurrió.
"""
from __future__ import annotations
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.db.database import SessionLocal
from src.db.models import TradingJournalModel

class TradingJournalManager:
    """Gestiona las entradas del diario de trading y el cotejo señal vs realidad."""

    def list_entries(self) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            entries = db.query(TradingJournalModel).order_by(TradingJournalModel.created_at.desc()).all()
            res = []
            for e in entries:
                res.append({
                    "id": e.id,
                    "opportunity_id": e.opportunity_id,
                    "symbol": e.symbol,
                    "created_at": e.created_at.isoformat(),
                    "notes": e.notes,
                    "signal_prob": e.signal_prob,
                    "actual_outcome_r": e.actual_outcome_r,
                    "lessons_learned": e.lessons_learned,
                    "tags": json.loads(e.tags_json or "[]"),
                })
            return res
        finally:
            db.close()

    def add_entry(
        self,
        symbol: str,
        notes: str,
        opportunity_id: Optional[str] = None,
        signal_prob: float = 0.0,
        actual_outcome_r: float = 0.0,
        lessons_learned: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            entry = TradingJournalModel(
                id=f"jrn_{uuid.uuid4().hex[:10]}",
                symbol=symbol.upper(),
                opportunity_id=opportunity_id,
                notes=notes,
                signal_prob=signal_prob,
                actual_outcome_r=actual_outcome_r,
                lessons_learned=lessons_learned,
                tags_json=json.dumps(tags or []),
                created_at=datetime.now(timezone.utc),
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return {
                "id": entry.id,
                "symbol": entry.symbol,
                "message": "Entrada de diario guardada con éxito.",
            }
        finally:
            db.close()

journal_manager = TradingJournalManager()
