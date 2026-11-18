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

    def close_position(
        self,
        position_id: str,
        reason: str = "MANUAL",
        exit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Cierra una posición abierta en Paper Trading (por TP1, TP2, SL o cierre manual).
        Calcula ganancia o pérdida en USD y múltiplos de R, devuelve el capital al saldo y registra el cierre.
        """
        db = SessionLocal()
        try:
            pos = db.query(PaperPositionModel).filter_by(id=position_id, status="OPEN").first()
            if not pos:
                raise ValueError(f"Posición '{position_id}' no encontrada o ya se encuentra cerrada.")

            port = db.query(PaperPortfolioModel).filter_by(id="default").first()
            if not port:
                port = PaperPortfolioModel(id="default", initial_capital=10000.0, current_cash=10000.0)
                db.add(port)
                db.commit()

            # Determinar precio de salida
            reason_upper = reason.upper().strip()
            final_exit = exit_price
            if final_exit is None or final_exit <= 0:
                if "TP1" in reason_upper and pos.take_profit_1 > 0:
                    final_exit = pos.take_profit_1
                elif "TP2" in reason_upper and pos.take_profit_2 > 0:
                    final_exit = pos.take_profit_2
                elif "SL" in reason_upper and pos.stop_loss > 0:
                    final_exit = pos.stop_loss
                else:
                    try:
                        q = data_manager.fetch_quote(pos.symbol)
                        final_exit = float(q.get("price", pos.current_price or pos.entry_price))
                    except Exception:
                        final_exit = float(pos.current_price or pos.entry_price)

            # Calcular Ganancia / Pérdida en USD
            if pos.direction == "LONG":
                realized_pnl = (final_exit - pos.entry_price) * pos.shares
            else:
                realized_pnl = (pos.entry_price - final_exit) * pos.shares

            # Calcular Múltiplo R (R-multiple)
            r_distance = abs(pos.entry_price - pos.stop_loss) if pos.stop_loss > 0 else (pos.entry_price * 0.015)
            r_risk_usd = r_distance * pos.shares if r_distance > 0 else 1.0
            realized_r = realized_pnl / r_risk_usd if r_risk_usd > 0 else 0.0

            # Retornar capital invertido + PnL al saldo disponible
            invested_capital = pos.entry_price * pos.shares
            port.current_cash += (invested_capital + realized_pnl)
            port.total_realized_pnl += realized_pnl

            # Actualizar estado de la posición
            pos.status = "CLOSED"
            pos.exit_price = round(final_exit, 2)
            pos.closed_at = datetime.now(timezone.utc)
            pos.close_reason = reason_upper
            pos.realized_pnl = round(realized_pnl, 2)
            pos.realized_r = round(realized_r, 2)

            db.commit()

            is_win = realized_pnl > 0
            outcome_label = "VICTORIA ✅" if is_win else ("STOP LOSS ❌" if realized_pnl < 0 else "BREAKEVEN ⚪")
            msg = (
                f"{pos.symbol} cerrada ({outcome_label}) a ${final_exit:.2f} por {reason_upper}. "
                f"Resultado: {'+' if realized_pnl >= 0 else ''}${realized_pnl:.2f} USD "
                f"({'+' if realized_r >= 0 else ''}{realized_r:.2f}R)"
            )

            return {
                "status": "CLOSED",
                "position_id": pos.id,
                "symbol": pos.symbol,
                "direction": pos.direction,
                "shares": pos.shares,
                "entry_price": pos.entry_price,
                "exit_price": round(final_exit, 2),
                "close_reason": reason_upper,
                "realized_pnl": round(realized_pnl, 2),
                "realized_r": round(realized_r, 2),
                "closed_at": pos.closed_at.isoformat(),
                "remaining_cash": round(port.current_cash, 2),
                "total_realized_pnl": round(port.total_realized_pnl, 2),
                "message": msg,
            }
        finally:
            db.close()

    def get_closed_trades(self) -> Dict[str, Any]:
        """
        Retorna el resumen de operaciones cerradas, métricas de rendimiento y notificaciones.
        """
        db = SessionLocal()
        try:
            closed = (
                db.query(PaperPositionModel)
                .filter_by(status="CLOSED")
                .order_by(PaperPositionModel.closed_at.desc())
                .all()
            )

            trades_list = []
            wins = 0
            losses = 0
            gross_win = 0.0
            gross_loss = 0.0

            for p in closed:
                pnl = p.realized_pnl or 0.0
                r_val = p.realized_r or 0.0
                if pnl > 0:
                    wins += 1
                    gross_win += pnl
                elif pnl < 0:
                    losses += 1
                    gross_loss += abs(pnl)

                trades_list.append({
                    "id": p.id,
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "shares": p.shares,
                    "entry_price": p.entry_price,
                    "exit_price": p.exit_price or p.current_price,
                    "stop_loss": p.stop_loss,
                    "take_profit_1": p.take_profit_1,
                    "take_profit_2": p.take_profit_2,
                    "close_reason": p.close_reason or "MANUAL",
                    "realized_pnl": round(pnl, 2),
                    "realized_r": round(r_val, 2),
                    "opened_at": p.opened_at.isoformat() if p.opened_at else None,
                    "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                    "is_win": pnl > 0,
                })

            total_closed = len(trades_list)
            win_rate = round((wins / total_closed) * 100.0, 1) if total_closed > 0 else 0.0
            total_realized_pnl = round(sum(t["realized_pnl"] for t in trades_list), 2)
            total_realized_r = round(sum(t["realized_r"] for t in trades_list), 2)
            profit_factor = (
                round(gross_win / gross_loss, 2)
                if gross_loss > 0
                else (99.0 if gross_win > 0 else 0.0)
            )

            # Generar feed de notificaciones
            notifications = []
            for t in trades_list[:30]:
                is_win = t["is_win"]
                sign = "+" if t["realized_pnl"] >= 0 else ""
                r_sign = "+" if t["realized_r"] >= 0 else ""
                notifications.append({
                    "id": f"notif_{t['id']}",
                    "position_id": t["id"],
                    "symbol": t["symbol"],
                    "direction": t["direction"],
                    "type": "WIN" if is_win else ("LOSS" if t["realized_pnl"] < 0 else "NEUTRAL"),
                    "title": f"Operación {t['symbol']} · {t['direction']} Cerrada",
                    "subtitle": f"Cierre por {t['close_reason']} | {t['shares']} acc @ ${t['exit_price']:.2f}",
                    "pnl_usd": t["realized_pnl"],
                    "pnl_r": t["realized_r"],
                    "message": f"Resultado: {sign}${t['realized_pnl']:.2f} USD ({r_sign}{t['realized_r']:.2f}R)",
                    "timestamp": t["closed_at"],
                })

            return {
                "total_closed": total_closed,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_realized_pnl": total_realized_pnl,
                "total_realized_r": total_realized_r,
                "profit_factor": profit_factor,
                "trades": trades_list,
                "notifications": notifications,
            }
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
