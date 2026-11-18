"""
Trading EZ - Tests Unitarios de Position Sizing y Gestión de Riesgo (Fase 6).
"""
import pytest
from src.opportunities.sizing import calculate_position_size

def test_sizing_standard_risk_limited():
    # Capital $10,000, Riesgo 1.0% ($100)
    # Entrada $100, Stop $95 (distancia $5/acción)
    # Acciones calculadas = 100 / 5 = 20 acciones
    # Nocional = 20 * 100 = $2,000 (20% de la cuenta, menor al límite de 25%)
    res = calculate_position_size(
        account_capital=10000.0,
        entry_price=100.0,
        stop_loss=95.0,
        risk_pct=1.0,
        max_position_size_pct=25.0,
    )
    assert res.effective_shares == 20
    assert res.effective_notional == 2000.0
    assert res.portfolio_pct == 20.0
    assert res.effective_risk_dollars == 100.0
    assert res.capped_by_rule is None

def test_sizing_capped_by_max_position_25_pct():
    # Capital $10,000, Riesgo 1.0% ($100)
    # Entrada $100, Stop $98 (distancia $2/acción)
    # Cálculo crudo = 100 / 2 = 50 acciones -> Nocional $5,000 (50% de la cuenta)
    # DEBE topar al 25% de la cuenta = $2,500 / 100 = 25 acciones
    res = calculate_position_size(
        account_capital=10000.0,
        entry_price=100.0,
        stop_loss=98.0,
        risk_pct=1.0,
        max_position_size_pct=25.0,
    )
    assert res.raw_shares == 50
    assert res.effective_shares == 25
    assert res.effective_notional == 2500.0
    assert res.portfolio_pct == 25.0
    assert res.capped_by_rule == "max_single_position_25_pct"
    # El riesgo efectivo se reduce a 25 * $2 = $50 (0.50% de la cuenta)
    assert res.effective_risk_dollars == 50.0
    assert res.effective_risk_pct == 0.50

def test_sizing_invalid_zero_distance():
    with pytest.raises(ValueError):
        calculate_position_size(10000.0, 100.0, 100.0)
