"""
Trading EZ - Router de Oportunidades y Explicación con IA (FastAPI).
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.opportunities.engine import opportunity_engine
from src.ai_explainer.client import ai_explainer

router = APIRouter(prefix="/api/opportunities", tags=["Oportunidades"])

class ExplainRequest(BaseModel):
    ticket: Dict[str, Any]
    recent_headlines: Optional[List[str]] = None
    upcoming_events: Optional[List[Dict[str, Any]]] = None

@router.get("")
def get_opportunities(
    asset_class: str = Query("all", description="all | stocks | crypto | etf | commodities"),
    horizon: str = Query("medium", description="short | medium | long"),
    capital: Optional[float] = Query(None, description="Capital de la cuenta en USD"),
    risk_pct: Optional[float] = Query(None, description="Porcentaje de riesgo por operación"),
    min_prob: Optional[float] = Query(None, description="Probabilidad mínima requerida (ej. 0.60)"),
    force_refresh: bool = Query(False, description="Forzar recálculo del ranking"),
):
    """
    Retorna el ranking de las mejores oportunidades del mercado.
    Aplica selectividad extrema: si ninguna supera los umbrales estadísticos,
    devuelve un resultado transparente de 'no hay ventaja suficiente'.
    """
    return opportunity_engine.get_daily_opportunities(
        asset_class=asset_class,
        horizon=horizon,
        capital=capital,
        risk_pct=risk_pct,
        min_prob=min_prob,
        force_refresh=force_refresh,
    )

@router.post("/{symbol}/explain")
def explain_opportunity(symbol: str, req: ExplainRequest):
    """
    Genera una explicación analítica de apoyo utilizando IA sobre la ficha determinista.
    Aplica validación estricta contra alucinaciones de precios.
    """
    explanation = ai_explainer.explain_opportunity(
        ticket=req.ticket,
        recent_headlines=req.recent_headlines,
        upcoming_events=req.upcoming_events,
    )
    return {
        "symbol": symbol.upper(),
        "ai_explanation": explanation,
    }
