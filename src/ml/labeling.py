"""
Trading EZ - Etiquetado por Método de Triple Barrera Causal (Marcos López de Prado).
Genera targets supervisados (clasificación binaria y R neto) sin lookahead bias.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd

@dataclass
class TradeOutcome:
    entry_idx: int
    entry_date: pd.Timestamp
    entry_price: float
    stop_loss: float
    take_profit: float
    r_dollar: float
    exit_idx: int
    exit_date: pd.Timestamp
    exit_price: float
    exit_reason: str  # 'stop_loss' | 'take_profit' | 'time_expiry'
    r_multiple_gross: float
    r_multiple_net: float
    is_winner: int  # 1 si r_multiple_net > 0, 0 en caso contrario

class TripleBarrierLabeler:
    """
    Simulador de triple barrera:
    1. Barrera de Pérdida (Stop Loss): entrada - k * ATR(14)
    2. Barrera de Beneficio (Take Profit): entrada + target_r * R
    3. Barrera de Tiempo (Horizonte): máximo N velas

    Regla conservadora institucional: Si en la misma vela se tocan Stop Loss y Take Profit,
    SE ASUME SIEMPRE QUE EL STOP LOSS SALTÓ PRIMERO.
    """

    def __init__(
        self,
        atr_multiplier: float = 1.5,
        target_r: float = 1.5,
        max_holding_bars: int = 10,
        est_cost_bps: float = 10.0,  # 10 bps = 0.10% total comisiones + spread + slippage
    ):
        self.atr_multiplier = atr_multiplier
        self.target_r = target_r
        self.max_holding_bars = max_holding_bars
        self.est_cost_bps = est_cost_bps

    def label_dataset(
        self,
        df: pd.DataFrame,
        atr_col: str = "atr_14",
    ) -> pd.DataFrame:
        """
        Para cada barra t, define la operación hipotética que entraría en Open(t+1)
        y evalúa su desenlace en las siguientes barras [t+1 ... t+1+max_holding_bars].
        """
        res = df.copy()
        n = len(res)

        target_winner = np.full(n, np.nan)
        target_r_net = np.full(n, np.nan)
        trade_entry_price = np.full(n, np.nan)
        trade_stop_loss = np.full(n, np.nan)
        trade_take_profit = np.full(n, np.nan)
        trade_exit_reason = [""] * n
        trade_bars_held = np.zeros(n, dtype=int)

        opens = res["open"].values
        highs = res["high"].values
        lows = res["low"].values
        closes = res["close"].values
        atrs = res[atr_col].values if atr_col in res.columns else np.full(n, 1.0)

        cost_factor = self.est_cost_bps / 10000.0

        # Iterar hasta n - 2 (para poder entrar en t+1 y evaluar al menos 1 vela)
        for t in range(n - 1):
            entry_idx = t + 1
            entry_price = opens[entry_idx]

            atr_val = atrs[t]
            if np.isnan(atr_val) or atr_val <= 0:
                continue

            risk_distance = max(self.atr_multiplier * atr_val, entry_price * 0.005)
            stop_loss = entry_price - risk_distance
            take_profit = entry_price + (self.target_r * risk_distance)

            max_exit_idx = min(entry_idx + self.max_holding_bars, n - 1)

            exit_idx = max_exit_idx
            exit_price = closes[max_exit_idx]
            exit_reason = "time_expiry"

            # Evaluar barras futuras desde entry_idx hasta max_exit_idx
            for bar_i in range(entry_idx, max_exit_idx + 1):
                b_high = highs[bar_i]
                b_low = lows[bar_i]
                b_open = opens[bar_i]

                hit_stop = b_low <= stop_loss
                hit_tp = b_high >= take_profit

                if hit_stop and hit_tp:
                    # REGLA OBLIGATORIA: Si ambos se tocan en la misma barra, STOP PRIMERO
                    exit_idx = bar_i
                    # Gap down si el open fue menor al stop
                    exit_price = min(stop_loss, b_open)
                    exit_reason = "stop_loss"
                    break
                elif hit_stop:
                    exit_idx = bar_i
                    exit_price = min(stop_loss, b_open)
                    exit_reason = "stop_loss"
                    break
                elif hit_tp:
                    exit_idx = bar_i
                    exit_price = max(take_profit, b_open)
                    exit_reason = "take_profit"
                    break

            # Cálculo de múltiplos de R
            gross_pnl = exit_price - entry_price
            gross_r = gross_pnl / risk_distance

            # Coste en múltiplos de R:
            # Coste en dólares = entry_price * cost_factor
            cost_in_r = (entry_price * cost_factor) / risk_distance
            net_r = gross_r - cost_in_r

            # Asignar a la barra t (momento en que se tomó la decisión)
            target_winner[t] = 1.0 if net_r > 0.0 else 0.0
            target_r_net[t] = net_r
            trade_entry_price[t] = entry_price
            trade_stop_loss[t] = stop_loss
            trade_take_profit[t] = take_profit
            trade_exit_reason[t] = exit_reason
            trade_bars_held[t] = exit_idx - entry_idx

        res["target_winner"] = target_winner
        res["target_r_net"] = target_r_net
        res["candidate_entry"] = trade_entry_price
        res["candidate_stop"] = trade_stop_loss
        res["candidate_tp"] = trade_take_profit
        res["candidate_exit_reason"] = trade_exit_reason
        res["candidate_bars_held"] = trade_bars_held

        return res
