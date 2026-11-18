"""
Trading EZ - Router de Paper Trading y Cartera Virtual.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.paper_trading.portfolio import paper_manager

router = APIRouter(prefix="/api/paper", tags=["Paper Trading"])

class OrderRequest(BaseModel):
    symbol: str
    direction: str = "LONG"
    shares: int = 1
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0

class ResetRequest(BaseModel):
    capital: float = 10000.0

class ClosePositionRequest(BaseModel):
    position_id: str
    reason: str = "MANUAL"  # TP1 | TP2 | SL | MANUAL
    exit_price: Optional[float] = None

@router.get("/portfolio")
def get_paper_portfolio():
    p = paper_manager.get_or_create_portfolio()
    p["cash"] = p.get("current_cash", 10000.0)
    return {"portfolio": p, **p}

@router.post("/order")
def execute_paper_order(req: OrderRequest):
    try:
        return paper_manager.execute_order(
            symbol=req.symbol,
            direction=req.direction,
            shares=req.shares,
            stop_loss=req.stop_loss,
            take_profit_1=req.take_profit_1,
            take_profit_2=req.take_profit_2,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/close")
def close_paper_position(req: ClosePositionRequest):
    try:
        return paper_manager.close_position(
            position_id=req.position_id,
            reason=req.reason,
            exit_price=req.exit_price,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/closed")
def get_closed_trades():
    return paper_manager.get_closed_trades()

@router.get("/notifications")
def get_paper_notifications():
    closed_data = paper_manager.get_closed_trades()
    return {
        "notifications": closed_data.get("notifications", []),
        "summary": {
            "total_closed": closed_data.get("total_closed", 0),
            "wins": closed_data.get("wins", 0),
            "losses": closed_data.get("losses", 0),
            "win_rate": closed_data.get("win_rate", 0.0),
            "total_realized_pnl": closed_data.get("total_realized_pnl", 0.0),
            "total_realized_r": closed_data.get("total_realized_r", 0.0),
            "profit_factor": closed_data.get("profit_factor", 0.0),
        },
    }

@router.post("/reset")
def reset_paper_portfolio(req: ResetRequest):
    return paper_manager.reset_portfolio(capital=req.capital)
