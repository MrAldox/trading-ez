"""
Trading EZ - Motor de Backtesting Event-Driven Institucional y Simulación de Cartera.
Simula la operativa real día a día: decisión al cierre de t, ejecución en apertura de t+1,
costes de transacción, reglas de gestión monetaria y regla conservadora stop-primero.
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from src.core.config import settings, AssetMetadata
from src.data_providers.cache_manager import CacheManager
from src.feature_engineering.pipeline import build_features
from src.backtest.metrics import calculate_backtest_metrics, BacktestMetrics
from src.backtest.robustness import run_monte_carlo_simulation, evaluate_regimes

class BacktestEngine:
    """
    Motor de simulación paso a paso sin lookahead bias.
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        risk_per_trade_pct: float = 1.0,
        max_open_positions: int = 5,
        max_position_size_pct: float = 25.0,
        min_prob_threshold: float = 0.58,
        min_expectancy_r: float = 0.15,
        min_risk_reward: float = 1.5,
        cache_manager: Optional[CacheManager] = None,
    ):
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_open_positions = max_open_positions
        self.max_position_size_pct = max_position_size_pct
        self.min_prob_threshold = min_prob_threshold
        self.min_expectancy_r = min_expectancy_r
        self.min_risk_reward = min_risk_reward
        self.cache_manager = cache_manager or CacheManager()

    def run(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Ejecuta el backtest completo sobre el universo y rango temporal."""
        # 1. Cargar y procesar características de todos los activos
        spy_res = self.cache_manager.get_daily("SPY")
        bench_df = spy_res[0] if spy_res else None

        asset_data: Dict[str, pd.DataFrame] = {}
        for sym in symbols:
            res = self.cache_manager.get_daily(sym)
            if not res:
                continue
            df, _ = res
            feat_df = build_features(df, benchmark_df=bench_df, benchmark_name="SPY")
            # Filtrar rango
            sliced = feat_df.loc[(feat_df.index >= pd.to_datetime(start_date, utc=True)) &
                                 (feat_df.index <= pd.to_datetime(end_date, utc=True))]
            if len(sliced) >= 50:
                norm_slice = sliced.copy()
                norm_slice.index = norm_slice.index.normalize()
                asset_data[sym] = norm_slice

        if not asset_data:
            raise ValueError("No hay datos suficientes para ejecutar el backtest en las fechas dadas.")

        # Obtener todas las fechas de negociación comunes ordenadas
        all_dates = sorted(list(set.union(*[set(df.index) for df in asset_data.values()])))

        cash = self.initial_capital
        open_positions: List[Dict[str, Any]] = []
        closed_trades: List[Dict[str, Any]] = []
        equity_records: List[Dict[str, Any]] = []
        pending_orders: List[Dict[str, Any]] = []

        # Mapa de costos por símbolo
        asset_map = settings.assets_by_symbol

        # 2. Bucle Event-Driven día a día
        for idx, current_dt in enumerate(all_dates):
            current_date_str = current_dt.strftime("%Y-%m-%d")

            # A) EJECUCIÓN AL INICIO DEL DÍA (Apertura de t)
            # Procesar órdenes pendientes generadas en el cierre anterior t-1
            for order in pending_orders:
                sym = order["symbol"]
                if sym in asset_data and current_dt in asset_data[sym].index:
                    bar = asset_data[sym].loc[current_dt]
                    open_price = float(bar["open"])

                    cost_bps = asset_map.get(sym, AssetMetadata(symbol=sym, name=sym)).est_cost_bps
                    slippage = open_price * (cost_bps / 10000.0)
                    fill_price = open_price + slippage

                    # Recalcular riesgo con fill real
                    stop_price = float(order["stop_loss"])
                    risk_per_share = max(fill_price - stop_price, fill_price * 0.005)

                    max_risk_dollars = cash * (self.risk_per_trade_pct / 100.0)
                    shares = math.floor(max_risk_dollars / risk_per_share)

                    # Tope de capital por posición (máx 25%)
                    max_notional = (cash + sum(p["shares"] * p["current_price"] for p in open_positions)) * (self.max_position_size_pct / 100.0)
                    shares = min(shares, math.floor(max_notional / fill_price))

                    cost_total = shares * fill_price
                    if shares > 0 and cost_total <= cash and len(open_positions) < self.max_open_positions:
                        cash -= cost_total
                        open_positions.append({
                            "symbol": sym,
                            "entry_date": current_date_str,
                            "entry_price": fill_price,
                            "current_price": fill_price,
                            "shares": shares,
                            "stop_loss": stop_price,
                            "take_profit_1": float(order["take_profit_1"]),
                            "take_profit_2": float(order["take_profit_2"]),
                            "risk_dollar": shares * risk_per_share,
                            "bars_held": 0,
                            "max_bars": 12,
                        })

            pending_orders = []

            # B) MONITOREO INTRADÍA Y CIERRE DE POSICIONES
            surviving_positions = []
            for pos in open_positions:
                sym = pos["symbol"]
                if sym in asset_data and current_dt in asset_data[sym].index:
                    bar = asset_data[sym].loc[current_dt]
                    b_high = float(bar["high"])
                    b_low = float(bar["low"])
                    b_close = float(bar["close"])
                    b_open = float(bar["open"])

                    pos["bars_held"] += 1
                    pos["current_price"] = b_close

                    hit_stop = b_low <= pos["stop_loss"]
                    hit_tp = b_high >= pos["take_profit_1"]
                    expired = pos["bars_held"] >= pos["max_bars"]

                    # REGLA CONSERVADORA: Si ambos se tocan, STOP PRIMERO
                    if hit_stop and hit_tp:
                        exit_price = min(pos["stop_loss"], b_open)
                        exit_reason = "stop_loss"
                    elif hit_stop:
                        exit_price = min(pos["stop_loss"], b_open)
                        exit_reason = "stop_loss"
                    elif hit_tp:
                        exit_price = max(pos["take_profit_1"], b_open)
                        exit_reason = "take_profit"
                    elif expired:
                        exit_price = b_close
                        exit_reason = "time_expiry"
                    else:
                        surviving_positions.append(pos)
                        continue

                    # Cerrar posición y aplicar comisiones de salida
                    cost_bps = asset_map.get(sym, AssetMetadata(symbol=sym, name=sym)).est_cost_bps
                    exit_slippage = exit_price * (cost_bps / 10000.0)
                    effective_exit = exit_price - exit_slippage

                    gross_proceeds = pos["shares"] * effective_exit
                    cash += gross_proceeds

                    pnl_dollars = (effective_exit - pos["entry_price"]) * pos["shares"]
                    r_outcome = pnl_dollars / (pos["risk_dollar"] or 1.0)

                    closed_trades.append({
                        "symbol": sym,
                        "entry_date": pos["entry_date"],
                        "exit_date": current_date_str,
                        "entry_price": round(pos["entry_price"], 2),
                        "exit_price": round(effective_exit, 2),
                        "shares": pos["shares"],
                        "risk_dollar": round(pos["risk_dollar"], 2),
                        "pnl_dollars": round(pnl_dollars, 2),
                        "outcome_r": round(r_outcome, 2),
                        "exit_reason": exit_reason,
                        "duration_days": pos["bars_held"],
                    })
                else:
                    surviving_positions.append(pos)

            open_positions = surviving_positions

            # C) CALCULAR VALOR TOTAL DE LA CUENTA (Equity)
            positions_value = sum(p["shares"] * p["current_price"] for p in open_positions)
            total_equity = cash + positions_value
            equity_records.append({
                "date": current_date_str,
                "equity": total_equity,
                "cash": cash,
                "positions_count": len(open_positions),
            })

            # D) GENERACIÓN DE SEÑALES Y RANKING AL CIERRE DE LA VELA t
            # Solo si no estamos en la última fecha del backtest
            if idx < len(all_dates) - 1:
                daily_candidates = []
                for sym, df_sym in asset_data.items():
                    # Evitar comprar el mismo activo si ya está abierto
                    if any(p["symbol"] == sym for p in open_positions):
                        continue
                    if current_dt not in df_sym.index:
                        continue

                    bar = df_sym.loc[current_dt]
                    close_p = float(bar["close"])

                    # 1. Filtros de Setup Cuantitativo Institucional ("Menos Fallos = Selectividad")
                    is_bull_trend = (
                        (close_p > float(bar.get("ema_50", close_p))) and
                        (float(bar.get("ema_21", 0)) > float(bar.get("ema_50", 0))) and
                        (float(bar.get("ema_50", 0)) > float(bar.get("ema_200", 0)))  # Tendencia secular alcista
                    )
                    # No perseguir precios sobreextendidos (pullback cercano a EMA 21)
                    is_pullback_favorable = -0.02 <= float(bar.get("dist_ema_21", 0.0)) <= 0.035
                    is_momentum_ok = 42.0 <= float(bar.get("rsi_14", 50.0)) <= 62.0
                    is_volume_confirmed = float(bar.get("rvol_20", 1.0)) >= 1.0
                    # Régimen macro: benchmark general alcista
                    is_market_aligned = (float(bar.get("benchmark_above_ema50", 1.0)) == 1.0) and (float(bar.get("benchmark_above_ema200", 1.0)) == 1.0)

                    if is_bull_trend and is_pullback_favorable and is_momentum_ok and is_market_aligned:
                        atr_val = float(bar.get("atr_14", close_p * 0.02))
                        risk_dist = max(1.2 * atr_val, close_p * 0.008)

                        stop_loss = round(close_p - risk_dist, 2)
                        target_mult = max(self.min_risk_reward, 2.0)
                        tp1 = round(close_p + (target_mult * risk_dist), 2)
                        tp2 = round(close_p + (3.0 * risk_dist), 2)

                        # Estimación calibrada de probabilidad y expectativa
                        base_prob = 0.60 + (0.04 if is_volume_confirmed else 0.0) + (0.03 if float(bar.get("pattern_bullish_engulfing", 0)) == 1.0 else 0.0)
                        calibrated_prob = min(base_prob, 0.72)
                        expected_r = (calibrated_prob * target_mult) - ((1.0 - calibrated_prob) * 1.0)

                        if calibrated_prob >= self.min_prob_threshold and expected_r >= self.min_expectancy_r:
                            daily_candidates.append({
                                "symbol": sym,
                                "calibrated_prob": calibrated_prob,
                                "expected_r": expected_r,
                                "stop_loss": stop_loss,
                                "take_profit_1": tp1,
                                "take_profit_2": tp2,
                            })

                # Ordenar por Expectancy esperada ajustada por probabilidad
                daily_candidates.sort(key=lambda x: (x["expected_r"], x["calibrated_prob"]), reverse=True)

                # Tomar los mejores que quepan en el cupo de posiciones abiertas
                slots_available = max(0, self.max_open_positions - len(open_positions))
                pending_orders = daily_candidates[:slots_available]

        # 3. Métricas finales y robustez
        equity_df = pd.DataFrame(equity_records).set_index(pd.to_datetime([r["date"] for r in equity_records]))
        metrics = calculate_backtest_metrics(closed_trades, equity_df, self.initial_capital)
        monte_carlo = run_monte_carlo_simulation(closed_trades, self.initial_capital, iterations=1000)
        regimes = evaluate_regimes(closed_trades)

        # Benchmark SPY CAGR
        benchmark_cagr = 0.0
        if bench_df is not None and not bench_df.empty:
            bench_slice = bench_df.loc[(bench_df.index >= pd.to_datetime(start_date, utc=True)) &
                                       (bench_df.index <= pd.to_datetime(end_date, utc=True))]
            if len(bench_slice) > 1:
                b_start = float(bench_slice["close"].iloc[0])
                b_end = float(bench_slice["close"].iloc[-1])
                years = max(0.1, (bench_slice.index[-1] - bench_slice.index[0]).days / 365.25)
                benchmark_cagr = round((((b_end / b_start) ** (1.0 / years)) - 1.0) * 100.0, 2)

        return {
            "backtest_id": f"bt_{uuid.uuid4().hex[:12]}",
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": self.initial_capital,
            "final_equity": round(float(equity_df["equity"].iloc[-1]), 2),
            "benchmark_spy_cagr": benchmark_cagr,
            "metrics": metrics,
            "equity_curve": equity_records,
            "closed_trades": closed_trades,
            "monte_carlo": monte_carlo,
            "regime_breakdown": regimes,
        }
