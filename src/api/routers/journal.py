"""
Trading EZ - Router de Diario de Trading (FastAPI).
"""
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel

from src.paper_trading.journal import journal_manager

router = APIRouter(prefix="/api/journal", tags=["Diario de Trading"])

class JournalEntryRequest(BaseModel):
    symbol: str
    notes: str
    opportunity_id: Optional[str] = None
    signal_prob: float = 0.0
    actual_outcome_r: float = 0.0
    lessons_learned: str = ""
    tags: Optional[List[str]] = None

@router.get("")
def list_journal_entries():
    return {"entries": journal_manager.list_entries()}

@router.post("")
def create_journal_entry(req: JournalEntryRequest):
    return journal_manager.add_entry(
        symbol=req.symbol,
        notes=req.notes,
        opportunity_id=req.opportunity_id,
        signal_prob=req.signal_prob,
        actual_outcome_r=req.actual_outcome_r,
        lessons_learned=req.lessons_learned,
        tags=req.tags,
    )
