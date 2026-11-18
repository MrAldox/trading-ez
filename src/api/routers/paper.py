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

@router.post("/reset")
def reset_paper_portfolio(req: ResetRequest):
    return paper_manager.reset_portfolio(capital=req.capital)
