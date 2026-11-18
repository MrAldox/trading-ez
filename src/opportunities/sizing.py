"""
Trading EZ - Dimensionamiento Matemático de Posición (Position Sizing).
Fórmula: (Capital * RiskPct) / |Entrada - Stop|, con tope estricto de concentración (máx 25% del capital).
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class SizingResult:
    account_capital: float
    risk_pct: float
    capital_at_risk: float
    raw_shares: int
    capped_by_rule: Optional[str]
    effective_shares: int
    effective_notional: float
    portfolio_pct: float
    effective_risk_dollars: float
    effective_risk_pct: float

def calculate_position_size(
    account_capital: float,
    entry_price: float,
    stop_loss: float,
    risk_pct: float = 1.0,
    max_position_size_pct: float = 25.0,
) -> SizingResult:
    """
    Calcula el número óptimo de acciones o unidades respetando la gestión de capital institucional:
    1. Riesgo limitado a risk_pct (por defecto 1.0%).
    2. Concentración máxima en un único activo no mayor al 25% de la cuenta.
    3. Redondeo estricto hacia abajo (floor) para evitar exceder el límite de riesgo.
    """
    risk_distance = abs(entry_price - stop_loss)
    if risk_distance <= 0:
        raise ValueError("La distancia entre entrada y stop loss debe ser estrictamente mayor a 0.")

    target_risk_dollars = account_capital * (risk_pct / 100.0)
    raw_shares = math.floor(target_risk_dollars / risk_distance)

    # Límite por concentración máxima de capital (ej. 25%)
    max_notional_allowed = account_capital * (max_position_size_pct / 100.0)
    max_shares_allowed = math.floor(max_notional_allowed / entry_price)

    capped_by_rule = None
    if raw_shares > max_shares_allowed:
        effective_shares = max_shares_allowed
        capped_by_rule = f"max_single_position_{int(max_position_size_pct)}_pct"
    else:
        effective_shares = raw_shares

    effective_notional = effective_shares * entry_price
    effective_risk_dollars = effective_shares * risk_distance
    portfolio_pct = (effective_notional / account_capital * 100.0) if account_capital > 0 else 0.0
    effective_risk_pct = (effective_risk_dollars / account_capital * 100.0) if account_capital > 0 else 0.0

    return SizingResult(
        account_capital=round(account_capital, 2),
        risk_pct=round(risk_pct, 2),
        capital_at_risk=round(target_risk_dollars, 2),
        raw_shares=raw_shares,
        capped_by_rule=capped_by_rule,
        effective_shares=effective_shares,
        effective_notional=round(effective_notional, 2),
        portfolio_pct=round(portfolio_pct, 2),
        effective_risk_dollars=round(effective_risk_dollars, 2),
        effective_risk_pct=round(effective_risk_pct, 2),
    )
