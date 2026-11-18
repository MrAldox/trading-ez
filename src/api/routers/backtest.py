"""
Trading EZ - Router de Backtesting (FastAPI).
"""
from __future__ import annotations
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.config import settings
from src.backtest.engine import BacktestEngine
from src.db.database import SessionLocal
from src.db.models import BacktestRunModel

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

class BacktestRequest(BaseModel):
    symbols: Optional[List[str]] = None
    start_date: str = "2022-01-01"
    end_date: str = "2026-11-16"
    initial_capital: float = 100000.0
    risk_pct: float = 1.0
    min_prob: float = 0.58
    min_expectancy_r: float = 0.15

@router.post("")
def run_backtest(req: BacktestRequest):
    """Ejecuta una simulación event-driven y persiste el resultado."""
    syms = req.symbols or [a.symbol for a in settings.universe]
    engine = BacktestEngine(
        initial_capital=req.initial_capital,
        risk_per_trade_pct=req.risk_pct,
        min_prob_threshold=req.min_prob,
        min_expectancy_r=req.min_expectancy_r,
    )

    try:
        res = engine.run(symbols=syms, start_date=req.start_date, end_date=req.end_date)
        m = res["metrics"]
        mc = res["monte_carlo"]
        regimes = res["regime_breakdown"]

        # Guardar en BD
        db = SessionLocal()
        try:
            record = BacktestRunModel(
                id=res["backtest_id"],
                name="Backtest Web - Trading EZ",
                universe_config_json=json.dumps(syms),
                start_date=req.start_date,
                end_date=req.end_date,
                is_validated=m.is_validated,
                total_cagr=m.cagr_pct,
                benchmark_cagr=res["benchmark_spy_cagr"],
                sharpe_ratio=m.sharpe_ratio,
                sortino_ratio=m.sortino_ratio,
                max_drawdown_pct=m.max_drawdown_pct,
                max_drawdown_duration_days=m.max_drawdown_duration_days,
                win_rate=m.win_rate,
                profit_factor=m.profit_factor,
                expectancy_r=m.expectancy_r,
                total_trades=m.total_trades,
                equity_curve_json=json.dumps(res["equity_curve"]),
                trades_json=json.dumps(res["closed_trades"]),
                monte_carlo_json=json.dumps(mc),
                regime_breakdown_json=json.dumps(regimes),
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/latest")
def get_latest_backtest():
    """Recupera el último backtest ejecutado."""
    db = SessionLocal()
    try:
        record = db.query(BacktestRunModel).order_by(BacktestRunModel.created_at.desc()).first()
        if not record:
            raise HTTPException(status_code=404, detail="No hay backtests ejecutados aún.")

        return {
            "backtest_id": record.id,
            "created_at": record.created_at.isoformat(),
            "start_date": record.start_date,
            "end_date": record.end_date,
            "is_validated": record.is_validated,
            "summary_metrics": {
                "total_cagr": record.total_cagr,
                "benchmark_spy_cagr": record.benchmark_cagr,
                "sharpe_ratio": record.sharpe_ratio,
                "sortino_ratio": record.sortino_ratio,
                "profit_factor": record.profit_factor,
                "win_rate": record.win_rate,
                "expectancy_r": record.expectancy_r,
                "max_drawdown_pct": record.max_drawdown_pct,
                "max_drawdown_duration_days": record.max_drawdown_duration_days,
                "total_trades": record.total_trades,
            },
            "equity_curve": json.loads(record.equity_curve_json or "[]"),
            "closed_trades": json.loads(record.trades_json or "[]"),
            "monte_carlo": json.loads(record.monte_carlo_json or "{}"),
            "regime_breakdown": json.loads(record.regime_breakdown_json or "{}"),
        }
    finally:
        db.close()

@router.get("/{backtest_id}")
def get_backtest_by_id(backtest_id: str):
    db = SessionLocal()
    try:
        record = db.query(BacktestRunModel).filter_by(id=backtest_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Backtest no encontrado.")

        return {
            "backtest_id": record.id,
            "created_at": record.created_at.isoformat(),
            "start_date": record.start_date,
            "end_date": record.end_date,
            "is_validated": record.is_validated,
            "summary_metrics": {
                "total_cagr": record.total_cagr,
                "benchmark_spy_cagr": record.benchmark_cagr,
                "sharpe_ratio": record.sharpe_ratio,
                "sortino_ratio": record.sortino_ratio,
                "profit_factor": record.profit_factor,
                "win_rate": record.win_rate,
                "expectancy_r": record.expectancy_r,
                "max_drawdown_pct": record.max_drawdown_pct,
                "max_drawdown_duration_days": record.max_drawdown_duration_days,
                "total_trades": record.total_trades,
            },
            "equity_curve": json.loads(record.equity_curve_json or "[]"),
            "closed_trades": json.loads(record.trades_json or "[]"),
            "monte_carlo": json.loads(record.monte_carlo_json or "{}"),
            "regime_breakdown": json.loads(record.regime_breakdown_json or "{}"),
        }
    finally:
        db.close()
