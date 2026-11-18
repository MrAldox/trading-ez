"""
Trading EZ - Tests Unitarios de Triple Barrera y Regla Stop-Primero (Fase 3).
"""
import pytest
import pandas as pd
import numpy as np

from src.ml.labeling import TripleBarrierLabeler

@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2024-01-01", periods=20, freq="D", tz="UTC")
    # Serie controlada
    df = pd.DataFrame({
        "open": [100.0] * 20,
        "high": [102.0] * 20,
        "low": [98.0] * 20,
        "close": [100.0] * 20,
        "volume": [1000] * 20,
        "atr_14": [2.0] * 20,
    }, index=dates)
    return df

def test_entry_at_next_bar_open(sample_ohlcv):
    labeler = TripleBarrierLabeler(atr_multiplier=1.5, target_r=1.5, max_holding_bars=5)
    labeled = labeler.label_dataset(sample_ohlcv)

    # La entrada de la señal generada en t=0 debe ser el Open de t=1
    assert labeled["candidate_entry"].iloc[0] == sample_ohlcv["open"].iloc[1]
    # Stop loss: 100 - (1.5 * 2.0) = 97.0
    assert labeled["candidate_stop"].iloc[0] == 97.0
    # Take profit: 100 + (1.5 * 3.0) = 104.5
    assert labeled["candidate_tp"].iloc[0] == 104.5

def test_conservative_stop_first_rule_on_same_candle(sample_ohlcv):
    # En la barra 2 (donde se evalúa el trade entrado en barra 1):
    # Forzar que la vela toque AMBOS niveles (High=105 >= 104.5 y Low=95 <= 97.0)
    conflict_df = sample_ohlcv.copy()
    conflict_df.iloc[2, conflict_df.columns.get_loc("high")] = 106.0
    conflict_df.iloc[2, conflict_df.columns.get_loc("low")] = 95.0

    labeler = TripleBarrierLabeler(atr_multiplier=1.5, target_r=1.5, max_holding_bars=5)
    labeled = labeler.label_dataset(conflict_df)

    # El resultado DEBE ser stop_loss debido a la regla obligatoria de no asumir beneficio si hubo conflicto
    assert labeled["candidate_exit_reason"].iloc[0] == "stop_loss"
    assert labeled["target_winner"].iloc[0] == 0.0

def test_time_expiry_exit(sample_ohlcv):
    # Los precios nunca tocan Stop (97) ni TP (104.5) dentro de 5 velas
    labeler = TripleBarrierLabeler(atr_multiplier=1.5, target_r=1.5, max_holding_bars=5)
    labeled = labeler.label_dataset(sample_ohlcv)

    # Debe salir por expiración de tiempo
    assert labeled["candidate_exit_reason"].iloc[0] == "time_expiry"
    assert labeled["candidate_bars_held"].iloc[0] == 5

def test_net_costs_reduce_r_multiple(sample_ohlcv):
    # Forzar un ganador claro en barra 2 (High=106, Low=99)
    win_df = sample_ohlcv.copy()
    win_df.iloc[2, win_df.columns.get_loc("high")] = 106.0
    win_df.iloc[2, win_df.columns.get_loc("low")] = 99.0

    labeler = TripleBarrierLabeler(atr_multiplier=1.5, target_r=1.5, est_cost_bps=20.0)
    labeled = labeler.label_dataset(win_df)

    assert labeled["candidate_exit_reason"].iloc[0] == "take_profit"
    # El R bruto es 1.5, pero el R neto DEBE ser menor por el impacto de los costes
    assert labeled["target_r_net"].iloc[0] < 1.5
    assert labeled["target_r_net"].iloc[0] > 1.4  # Costes razonables de 20 bps
