"""
Trading EZ - Pruebas de Robustez: Simulación Monte Carlo y Rendimiento por Régimen de Mercado.
"""
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import pandas as pd

def run_monte_carlo_simulation(
    trades: List[Dict[str, Any]],
    initial_capital: float = 100000.0,
    iterations: int = 1000,
) -> Dict[str, Any]:
    """
    Simulación Monte Carlo reordenando aleatoriamente la secuencia de trades.
    Estima el riesgo de cola: peor 5% de drawdown y probabilidad de ruina.
    """
    if len(trades) < 10:
        return {
            "iterations": iterations,
            "worst_5_pct_drawdown": 0.0,
            "median_equity": initial_capital,
            "median_return_pct": 0.0,
            "probability_of_ruin": 0.0,
        }

    pnls = np.array([t["pnl_dollars"] for t in trades])
    n_trades = len(pnls)

    drawdowns = []
    final_equities = []
    ruin_count = 0

    rng = np.random.default_rng(42)

    for _ in range(iterations):
        shuffled = rng.permutation(pnls)
        curve = initial_capital + np.cumsum(shuffled)
        curve = np.insert(curve, 0, initial_capital)

        # Ruina: cuenta cae > 50%
        if np.any(curve <= (initial_capital * 0.50)):
            ruin_count += 1

        running_max = np.maximum.accumulate(curve)
        dds = (curve - running_max) / running_max * 100.0
        drawdowns.append(float(np.min(dds)))
        final_equities.append(float(curve[-1]))

    drawdowns.sort()
    worst_5_pct_dd = drawdowns[int(iterations * 0.05)]
    median_equity = float(np.median(final_equities))
    prob_ruin = float(ruin_count / iterations)

    return {
        "iterations": iterations,
        "worst_5_pct_drawdown": round(worst_5_pct_dd, 2),
        "median_equity": round(median_equity, 2),
        "median_return_pct": round(((median_equity - initial_capital) / initial_capital) * 100.0, 2),
        "probability_of_ruin": round(prob_ruin, 4),
    }

def evaluate_regimes(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Desglosa el rendimiento por año y ciclo de mercado."""
    if not trades:
        return {}

    df = pd.DataFrame(trades)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["year"] = df["entry_date"].dt.year

    regimes = {}
    for year, group in df.groupby("year"):
        total = len(group)
        wins = int((group["pnl_dollars"] > 0).sum())
        pnl = float(group["pnl_dollars"].sum())
        regimes[str(year)] = {
            "total_trades": total,
            "win_rate": round(wins / total, 3) if total > 0 else 0.0,
            "total_pnl": round(pnl, 2),
            "avg_r": round(float(group.get("outcome_r", group["pnl_dollars"] / 1000.0).mean()), 3),
        }

    return regimes
