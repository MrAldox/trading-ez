"""
Trading EZ - Router de Calendario Económico y Earnings.
"""
from __future__ import annotations
from fastapi import APIRouter
from src.data_providers.finnhub_provider import FinnhubProvider

router = APIRouter(prefix="/api/calendar", tags=["Calendario"])
finnhub_prov = FinnhubProvider()

@router.get("")
def get_economic_calendar():
    """Eventos macroeconómicos clave (FOMC, CPI, NFP, PIB) con fuentes oficiales."""
    events = finnhub_prov.get_macro_calendar()
    return {"count": len(events), "events": events}
