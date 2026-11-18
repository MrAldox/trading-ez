"""
Trading EZ - Router de Asesor Financiero IA y Horarios Bancarios (Kill Zones).
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from src.ai_advisor.agent import advisor_agent
from src.institutional.kill_zones import kill_zones_engine
from src.opportunities.engine import opportunity_engine

router = APIRouter(prefix="/api/advisor", tags=["Asesor Financiero IA"])

class AdvisorChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

@router.post("/chat")
def chat_with_advisor(req: AdvisorChatRequest):
    """
    Interacción conversacional en tiempo real con el Asesor Cuantitativo.
    """
    res = advisor_agent.chat(user_message=req.message, conversation_history=req.history)
    return res

@router.get("/kill-zones")
def get_kill_zones():
    """
    Estado en tiempo real de las ventanas bancarias (London Open, NY Open, Silver Bullet).
    """
    return kill_zones_engine.get_market_sessions_status()

@router.get("/daily-briefing")
def get_daily_briefing():
    """
    Resumen ejecutivo matutino con la mejor oportunidad del día y el análisis del asesor.
    """
    session = kill_zones_engine.get_market_sessions_status()
    opps = opportunity_engine.get_daily_opportunities(asset_class="all")
    top_picks = opps.get("opportunities", [])[:3]

    briefing_text = (
        f"Buenos días. La sesión de Wall Street se encuentra actualmente en: {session.get('status_indicator', 'Mercado')}. "
        f"Se han identificado {len(top_picks)} oportunidades con confluencia institucional. "
        f"Recomendación principal: respetar la ventana de ejecución de las 09:30 a 11:00 EST y mantener el riesgo en 1% por operación."
    )

    return {
        "session_state": session,
        "briefing": briefing_text,
        "top_picks": top_picks,
    }
