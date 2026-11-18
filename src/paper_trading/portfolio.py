"""
Trading EZ - Motor de Paper Trading y Gestión de Cartera Virtual.
"""
from __future__ import annotations
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.db.database import SessionLocal
from src.db.models import PaperPortfolioModel, PaperPositionModel
from src.data_providers.manager import data_manager

class PaperTradingManager:
    """Gestiona saldo virtual, órdenes de compra/venta simuladas y PnL."""

    def get_or_create_portfolio(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            port = db.query(PaperPortfolioModel).filter_by(id="default").first()
            if not port:
                port = PaperPortfolioModel(
                    id="default",
                    initial_capital=10000.0,
                    current_cash=10000.0,
                    total_realized_pnl=0.0,
                )
                db.add(port)
                db.commit()
                db.refresh(port)

            positions = db.query(PaperPositionModel).filter_by(status="OPEN").all()

            pos_list = []
            unrealized_total = 0.0

            for p in positions:
                # Actualizar precio actual
                try:
                    q = data_manager.fetch_quote(p.symbol)
                    curr_price = float(q.get("price", p.entry_price))
                except Exception:
                    curr_price = p.entry_price

                pnl = (curr_price - p.entry_price) * p.shares if p.direction == "LONG" else (p.entry_price - curr_price) * p.shares
                unrealized_total += pnl

                pos_list.append({
                    "id": p.id,
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "shares": p.shares,
                    "entry_price": p.entry_price,
                    "current_price": curr_price,
                    "stop_loss": p.stop_loss,
                    "take_profit_1": p.take_profit_1,
                    "take_profit_2": p.take_profit_2,
                    "unrealized_pnl": round(pnl, 2),
                    "opened_at": p.opened_at.isoformat(),
                })

            total_equity = port.current_cash + sum(p["shares"] * p["current_price"] for p in pos_list)

            return {
                "initial_capital": port.initial_capital,
                "current_cash": round(port.current_cash, 2),
                "total_equity": round(total_equity, 2),
                "total_realized_pnl": round(port.total_realized_pnl, 2),
                "total_unrealized_pnl": round(unrealized_total, 2),
                "open_positions": pos_list,
            }
        finally:
            db.close()

    def execute_order(
        self,
        symbol: str,
        direction: str = "LONG",
        shares: int = 1,
        stop_loss: float = 0.0,
        take_profit_1: float = 0.0,
        take_profit_2: float = 0.0,
    ) -> Dict[str, Any]:
        """Ejecuta una orden simulada en paper trading."""
        db = SessionLocal()
        try:
            port = db.query(PaperPortfolioModel).filter_by(id="default").first()
            if not port:
                port = PaperPortfolioModel(id="default", initial_capital=10000.0, current_cash=10000.0)
                db.add(port)
                db.commit()

            quote = data_manager.fetch_quote(symbol)
            fill_price = float(quote.get("price", 100.0))
            cost = fill_price * shares

            if cost > port.current_cash:
                raise ValueError(f"Efectivo insuficiente (${port.current_cash:.2f}) para comprar {shares} {symbol} a ${fill_price:.2f}")

            port.current_cash -= cost
            pos = PaperPositionModel(
                id=f"pos_{uuid.uuid4().hex[:10]}",
                symbol=symbol.upper(),
                direction=direction.upper(),
                shares=shares,
                entry_price=fill_price,
                current_price=fill_price,
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                unrealized_pnl=0.0,
                status="OPEN",
            )
            db.add(pos)
            db.commit()

            res_dict = {
                "position_id": pos.id,
                "symbol": symbol,
                "shares": shares,
                "fill_price": fill_price,
                "remaining_cash": round(port.current_cash, 2),
                "message": f"Orden de paper trading ejecutada: {shares} {symbol} @ ${fill_price:.2f}",
            }
            res_dict["position"] = {
                "id": pos.id,
                "symbol": symbol,
                "shares": shares,
                "fill_price": fill_price,
            }
            return res_dict
        finally:
            db.close()

    def reset_portfolio(self, capital: float = 10000.0) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            db.query(PaperPositionModel).delete()
            port = db.query(PaperPortfolioModel).filter_by(id="default").first()
            if port:
                port.initial_capital = capital
                port.current_cash = capital
                port.total_realized_pnl = 0.0
            else:
                port = PaperPortfolioModel(id="default", initial_capital=capital, current_cash=capital)
                db.add(port)
            db.commit()
            return {
                "message": "Cuenta de Paper Trading reiniciada con éxito.",
                "capital": capital,
                "portfolio": {
                    "cash": capital,
                    "initial_capital": capital,
                    "total_equity": capital,
                    "positions_value": 0.0,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "open_positions": [],
                },
            }
        finally:
            db.close()

paper_manager = PaperTradingManager()
