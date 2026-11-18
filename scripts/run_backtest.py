"""
Trading EZ - Script CLI de Backtest Riguroso del Ranking Completo sobre el Universo (5 Años).
Ejecuta simulación event-driven día a día, comisiones, Monte Carlo y reporte honesto IS vs OOS.
"""
from __future__ import annotations
import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.config import settings
from src.backtest.engine import BacktestEngine
from src.db.database import SessionLocal
from src.db.models import BacktestRunModel

def main():
    print("=" * 75)
    print("  TRADING EZ - BACKTESTING INSTITUCIONAL DEL RANKING COMPLETO (5 AÑOS)")
    print("=" * 75)

    symbols = [a.symbol for a in settings.universe]
    start_date = "2021-11-01"
    end_date = "2026-11-16"

    print(f"Universo evaluado: {len(symbols)} activos ({', '.join(symbols[:8])}...)")
    print(f"Periodo de simulación: {start_date} a {end_date}")
    print(f"Capital Inicial: $100,000 USD | Riesgo por trade: 1.0% | Max posiciones: 5\n")

    engine = BacktestEngine(
        initial_capital=100000.0,
        risk_per_trade_pct=1.0,
        max_open_positions=5,
        max_position_size_pct=25.0,
        min_prob_threshold=0.58,
        min_expectancy_r=0.15,
        min_risk_reward=1.5,
    )

    print("Ejecutando simulación event-driven...")
    result = engine.run(symbols=symbols, start_date=start_date, end_date=end_date)

    m = result["metrics"]
    mc = result["monte_carlo"]
    regimes = result["regime_breakdown"]

    print("\n" + "=" * 75)
    print("  MÉTRICAS GLOBALES DEL BACKTEST (NETAS DE COMISIONES Y SLIPPAGE)")
    print("=" * 75)
    print(f"Retorno Total:                 {m.total_return_pct:+.2f}%  (Capital final: ${result['final_equity']:,.2f})")
    print(f"CAGR Trading EZ:               {m.cagr_pct:+.2f}%")
    print(f"CAGR Benchmark (SPY B&H):       {result['benchmark_spy_cagr']:+.2f}%")
    print(f"Sharpe Ratio:                  {m.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:                 {m.sortino_ratio:.2f}")
    print(f"Profit Factor:                 {m.profit_factor:.2f}")
    print(f"Win Rate:                      {m.win_rate * 100:.1f}% ({m.winning_trades} ganadoras / {m.losing_trades} perdedoras)")
    print(f"Expectancy Promedio (en R):    {m.expectancy_r:+.2f} R")
    print(f"Máximo Drawdown:               {m.max_drawdown_pct:.2f}% (Duración: {m.max_drawdown_duration_days} días)")
    print(f"Racha Máxima de Pérdidas:      {m.max_consecutive_losses} trades")
    print(f"Total de Operaciones:          {m.total_trades} (Duración media: {m.avg_trade_duration_days:.1f} días)")

    print("\n" + "-" * 75)
    print("  ANÁLISIS DE ROBUSTEZ: SIMULACIÓN MONTE CARLO (1,000 ITERACIONES)")
    print("-" * 75)
    print(f"Peor 5% de Drawdown Estimado:  {mc['worst_5_pct_drawdown']:.2f}%")
    print(f"Retorno Mediano Monte Carlo:   {mc['median_return_pct']:+.2f}%")
    print(f"Probabilidad de Ruina (>50%):  {mc['probability_of_ruin'] * 100:.2f}%")

    print("\n" + "-" * 75)
    print("  RENDIMIENTO POR AÑO / RÉGIMEN DE MERCADO")
    print("-" * 75)
    for year, stats in regimes.items():
        print(f"  Año {year}: {stats['total_trades']:3d} trades | Win Rate: {stats['win_rate']*100:4.1f}% | Expectancy: {stats['avg_r']:+4.2f}R | PnL: ${stats['total_pnl']:+9.2f}")

    print("\n" + "=" * 75)
    validation_status = "VALIDADA" if m.is_validated else "NO VALIDADA"
    print(f"ESTADO DE VALIDACIÓN INSTITUCIONAL: {validation_status}")
    if not m.is_validated:
        print("  [!] El modelo o la estrategia no superó todos los umbrales fuera de muestra.")
        print("  [!] Principio de honestidad: El terminal no forzará señales no rentables.")
    else:
        print("  [✓] Supera profit factor > 1.3, expectancy R > 0, > 100 trades y control de riesgo.")
    print("=" * 75)

    # Persistir en base de datos
    db = SessionLocal()
    try:
        run_record = BacktestRunModel(
            id=result["backtest_id"],
            name="Simulación Universo 5 Años - Trading EZ",
            universe_config_json=json.dumps(symbols),
            start_date=start_date,
            end_date=end_date,
            is_validated=m.is_validated,
            total_cagr=m.cagr_pct,
            benchmark_cagr=result["benchmark_spy_cagr"],
            sharpe_ratio=m.sharpe_ratio,
            sortino_ratio=m.sortino_ratio,
            max_drawdown_pct=m.max_drawdown_pct,
            max_drawdown_duration_days=m.max_drawdown_duration_days,
            win_rate=m.win_rate,
            profit_factor=m.profit_factor,
            expectancy_r=m.expectancy_r,
            total_trades=m.total_trades,
            equity_curve_json=json.dumps(result["equity_curve"]),
            trades_json=json.dumps(result["closed_trades"]),
            monte_carlo_json=json.dumps(mc),
            regime_breakdown_json=json.dumps(regimes),
        )
        db.add(run_record)
        db.commit()
        print(f"\nResultados guardados en BD con ID: {result['backtest_id']}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
