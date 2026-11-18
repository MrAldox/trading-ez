"""
Trading EZ - Cliente de IA Generativa de Apoyo (Gemini / Claude con Fallback Determinista).
"""
from __future__ import annotations
import os
import json
from typing import Dict, Any, List, Optional
import requests

from src.ai_explainer.prompts import SYSTEM_EXPLAINER_PROMPT
from src.ai_explainer.validator import ExplainerValidator

class AIExplainerClient:
    """
    Cliente para generar explicaciones analíticas de apoyo a partir de las fichas cuantitativas.
    """

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    def explain_opportunity(
        self,
        ticket: Dict[str, Any],
        recent_headlines: Optional[List[str]] = None,
        upcoming_events: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Genera la explicación validada matemáticamente."""
        headlines = recent_headlines or []
        events = upcoming_events or []

        # 1. Intentar llamar a LLM si hay claves configuradas
        if self.gemini_key:
            try:
                ai_raw = self._call_gemini(ticket, headlines, events)
                sanitized, passed = ExplainerValidator.validate_and_sanitize(ai_raw, ticket)
                return sanitized
            except Exception:
                pass

        if self.anthropic_key:
            try:
                ai_raw = self._call_claude(ticket, headlines, events)
                sanitized, passed = ExplainerValidator.validate_and_sanitize(ai_raw, ticket)
                return sanitized
            except Exception:
                pass

        # 2. Fallback determinista automático (seguro, sin costes y sin alucinaciones)
        return ExplainerValidator._fallback_deterministic(ticket)

    def _call_gemini(self, ticket: Dict[str, Any], headlines: List[str], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        user_prompt = f"""
Ficha Operativa Determinista:
{json.dumps(ticket, indent=2, ensure_ascii=False)}

Titulares recientes:
{json.dumps(headlines, ensure_ascii=False)}

Eventos macro próximos:
{json.dumps(events, ensure_ascii=False)}

Devuelve el JSON solicitado sin formato markdown extra:
"""
        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_EXPLAINER_PROMPT}\n\n{user_prompt}"}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code == 200:
            txt = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(txt)
        raise RuntimeError(f"Error Gemini HTTP {resp.status_code}")

    def _call_claude(self, ticket: Dict[str, Any], headlines: List[str], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        user_msg = f"Ficha:\n{json.dumps(ticket, ensure_ascii=False)}\nNoticias:\n{json.dumps(headlines, ensure_ascii=False)}"
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "system": SYSTEM_EXPLAINER_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        if resp.status_code == 200:
            txt = resp.json()["content"][0]["text"]
            return json.loads(txt)
        raise RuntimeError(f"Error Claude HTTP {resp.status_code}")

# Instancia global del cliente
ai_explainer = AIExplainerClient()
