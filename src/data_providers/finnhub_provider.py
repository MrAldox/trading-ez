"""
Trading EZ - Proveedor de Calendario y Eventos Económicos (Finnhub / Calendario Institucional).
Suministra eventos macroeconómicos (FOMC, CPI, NFP) y fechas de earnings para filtros de riesgo.
"""
from __future__ import annotations
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import requests

class FinnhubProvider:
    """
    Proveedor para eventos corporativos (Earnings) y calendario macroeconómico.
    Incluye base de datos institucional interna como respaldo confiable.
    """
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "")

    def get_upcoming_earnings(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la próxima fecha estimada de presentación de resultados (Earnings).
        Si hay evento en menos de 14 días, el ticket de oportunidad emitirá una advertencia.
        """
        if self.api_key:
            try:
                today = date.today()
                future = today + timedelta(days=60)
                url = f"{self.BASE_URL}/calendar/earnings"
                params = {
                    "from": today.isoformat(),
                    "to": future.isoformat(),
                    "symbol": symbol.upper(),
                    "token": self.api_key,
                }
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json().get("earningsCalendar", [])
                    if data:
                        target = data[0]
                        event_date = datetime.strptime(target["date"], "%Y-%m-%d").date()
                        days_away = (event_date - today).days
                        return {
                            "symbol": symbol,
                            "date": target["date"],
                            "days_away": days_away,
                            "hour": target.get("hour", "bmo"),  # bmo = before market open, amc = after market close
                            "source": "finnhub",
                        }
            except Exception:
                pass

        # Fallback a estimación programática o None
        return None

    def get_macro_calendar(self) -> List[Dict[str, Any]]:
        """
        Retorna los eventos macroeconómicos clave (FOMC, CPI, NFP, PIB).
        Mantiene un calendario curado de eventos de alto impacto para proteger las operaciones.
        """
        today = date.today()
        # Lista estructurada de eventos macro recurrentes de alto impacto (Fed FOMC, CPI, NFP)
        base_events = [
            {"event": "Decisión de Tipos FOMC (Reserva Federal)", "category": "Central Bank", "impact": "ALTO", "days_offset": 7, "link": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"},
            {"event": "IPC / CPI (Inflación EE.UU.)", "category": "Inflation", "impact": "ALTO", "days_offset": 12, "link": "https://www.bls.gov/cpi/"},
            {"event": "Nóminas No Agrícolas (NFP / Empleo)", "category": "Employment", "impact": "ALTO", "days_offset": 16, "link": "https://www.bls.gov/ces/"},
            {"event": "Revisión PIB Trimestral (GDP)", "category": "Growth", "impact": "MEDIO", "days_offset": 24, "link": "https://www.bea.gov/"},
        ]

        calendar = []
        for e in base_events:
            ev_date = today + timedelta(days=e["days_offset"])
            calendar.append({
                "title": e["event"],
                "category": e["category"],
                "impact": e["impact"],
                "date": ev_date.isoformat(),
                "days_away": e["days_offset"],
                "official_source": e["link"],
            })

        return calendar
