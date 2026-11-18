"""
Trading EZ - Tests Unitarios del Motor de Backtesting y Cálculo de Métricas (Fase 4).
"""
import pytest
import pandas as pd
from datetime import datetime

from src.backtest.metrics import calculate_backtest_metrics
from src.backtest.robustness import run_monte_carlo_simulation

def test_metrics_calculation_standard():
    dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    equity_df = pd.DataFrame({
        "equity": [100000.0, 101000.0, 102500.0, 101500.0, 103000.0, 102000.0, 104000.0, 105000.0, 104500.0, 106000.0]
    }, index=dates)

    trades = [
        {"pnl_dollars": 1000.0, "risk_dollar": 1000.0, "outcome_r": 1.0, "duration_days": 2},
        {"pnl_dollars": 1500.0, "risk_dollar": 1000.0, "outcome_r": 1.5, "duration_days": 3},
        {"pnl_dollars": -1000.0, "risk_dollar": 1000.0, "outcome_r": -1.0, "duration_days": 1},
        {"pnl_dollars": 1500.0, "risk_dollar": 1000.0, "outcome_r": 1.5, "duration_days": 2},
        {"pnl_dollars": -1000.0, "risk_dollar": 1000.0, "outcome_r": -1.0, "duration_days": 2},
        {"pnl_dollars": 2000.0, "risk_dollar": 1000.0, "outcome_r": 2.0, "duration_days": 3},
        {"pnl_dollars": 1000.0, "risk_dollar": 1000.0, "outcome_r": 1.0, "duration_days": 1},
    ]

    metrics = calculate_backtest_metrics(trades, equity_df, initial_capital=100000.0)

    assert metrics.total_return_pct == 6.0
    assert metrics.winning_trades == 5
    assert metrics.losing_trades == 2
    assert metrics.win_rate == round(5 / 7.0, 4)
    # Gross profit: 1000+1500+1500+2000+1000 = 7000; Gross loss: 2000; Profit factor = 3.5
    assert metrics.profit_factor == 3.5
    assert metrics.expectancy_r > 0.0
    assert metrics.max_drawdown_pct < 0.0

def test_monte_carlo_distribution():
    trades = [
        {"pnl_dollars": 1500.0},
        {"pnl_dollars": -1000.0},
        {"pnl_dollars": 1500.0},
        {"pnl_dollars": -1000.0},
        {"pnl_dollars": 3000.0},
        {"pnl_dollars": -1000.0},
        {"pnl_dollars": 1500.0},
        {"pnl_dollars": -1000.0},
        {"pnl_dollars": 1500.0},
        {"pnl_dollars": -1000.0},
        {"pnl_dollars": 1500.0},
    ]

    mc = run_monte_carlo_simulation(trades, initial_capital=100000.0, iterations=200)
    assert mc["iterations"] == 200
    assert mc["worst_5_pct_drawdown"] <= 0.0
    assert mc["probability_of_ruin"] == 0.0
