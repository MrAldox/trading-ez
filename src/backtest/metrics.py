"""
Trading EZ - Métricas Cuantitativas de Backtesting y Evaluación de Rendimiento.
Cálculo de CAGR, Sharpe, Sortino, Max Drawdown, Profit Factor, Expectancy R y rachas.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

@dataclass
class BacktestMetrics:
    total_return_pct: float
    cagr_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    win_rate: float
    expectancy_r: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    max_consecutive_losses: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_duration_days: float
    is_validated: bool  # Cumple todos los filtros OOS

def calculate_backtest_metrics(
    trades: List[Dict[str, Any]],
    equity_curve: pd.DataFrame,  # DataFrame con índice de fecha y columna 'equity'
    initial_capital: float = 100000.0,
    annual_factor: float = 252.0,
) -> BacktestMetrics:
    """Calcula todas las métricas de rendimiento y riesgo institucional."""
    if not trades or equity_curve.empty:
        return BacktestMetrics(
            total_return_pct=0.0, cagr_pct=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            profit_factor=0.0, win_rate=0.0, expectancy_r=0.0, max_drawdown_pct=0.0,
            max_drawdown_duration_days=0, max_consecutive_losses=0, total_trades=0,
            winning_trades=0, losing_trades=0, avg_trade_duration_days=0.0, is_validated=False,
        )

    # 1. Métricas de curva de equity
    equity_series = equity_curve["equity"]
    final_equity = float(equity_series.iloc[-1])
    total_return = ((final_equity - initial_capital) / initial_capital) * 100.0

    days_total = max(1, (equity_curve.index[-1] - equity_curve.index[0]).days)
    years = max(0.1, days_total / 365.25)
    cagr = (((final_equity / initial_capital) ** (1.0 / years)) - 1.0) * 100.0 if final_equity > 0 else -100.0

    # Retornos diarios
    daily_returns = equity_series.pct_change().dropna()
    mean_ret = daily_returns.mean()
    std_ret = daily_returns.std()

    # Sharpe (tasa libre de riesgo = 0 para evaluación conservadora)
    sharpe = float((mean_ret / std_ret * np.sqrt(annual_factor))) if std_ret > 0 else 0.0

    # Sortino (desviación a la baja exclusivamente)
    downside_returns = daily_returns[daily_returns < 0.0]
    downside_std = downside_returns.std()
    sortino = float((mean_ret / downside_std * np.sqrt(annual_factor))) if downside_std > 0 else 0.0

    # Drawdown
    running_max = equity_series.cummax()
    drawdowns = (equity_series - running_max) / running_max * 100.0
    max_dd = float(drawdowns.min())

    # Duración máxima de drawdown
    is_underwater = drawdowns < 0.0
    current_dd_duration = 0
    max_dd_duration = 0
    for under in is_underwater:
        if under:
            current_dd_duration += 1
            max_dd_duration = max(max_dd_duration, current_dd_duration)
        else:
            current_dd_duration = 0

    pnl_dollars = [t["pnl_dollars"] for t in trades]
    r_multiples = [
        t["outcome_r"] if "outcome_r" in t and t["outcome_r"] is not None
        else (t["pnl_dollars"] / (t.get("risk_dollar", 1000.0) or 1000.0))
        for t in trades
    ]

    total_trades = len(trades)
    winning_trades = sum(1 for p in pnl_dollars if p > 0.0)
    losing_trades = sum(1 for p in pnl_dollars if p <= 0.0)
    win_rate = winning_trades / float(total_trades)

    gross_profits = sum(p for p in pnl_dollars if p > 0.0)
    gross_losses = abs(sum(p for p in pnl_dollars if p < 0.0))
    profit_factor = float(gross_profits / gross_losses) if gross_losses > 0 else 999.0

    expectancy_r = float(np.mean(r_multiples))

    # Racha perdedora máxima
    consecutive_losses = 0
    max_consecutive = 0
    for p in pnl_dollars:
        if p <= 0.0:
            consecutive_losses += 1
            max_consecutive = max(max_consecutive, consecutive_losses)
        else:
            consecutive_losses = 0

    durations = [t.get("duration_days", 1) for t in trades]
    avg_duration = float(np.mean(durations)) if durations else 0.0

    # Criterio estricto de validación institucional OOS
    is_validated = (
        expectancy_r > 0.0 and
        profit_factor >= 1.3 and
        total_trades >= 100 and
        abs(max_dd) <= 25.0 and
        win_rate >= 0.45
    )

    return BacktestMetrics(
        total_return_pct=round(total_return, 2),
        cagr_pct=round(cagr, 2),
        sharpe_ratio=round(sharpe, 2),
        sortino_ratio=round(sortino, 2),
        profit_factor=round(profit_factor, 2),
        win_rate=round(win_rate, 4),
        expectancy_r=round(expectancy_r, 4),
        max_drawdown_pct=round(max_dd, 2),
        max_drawdown_duration_days=max_dd_duration,
        max_consecutive_losses=max_consecutive,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        avg_trade_duration_days=round(avg_duration, 1),
        is_validated=is_validated,
    )
