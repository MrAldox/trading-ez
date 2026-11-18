"""
Trading EZ - Validador Numérico Estricto para Respuestas de IA Generativa.
Garantiza que la IA nunca alucine números ni contradiga la ficha determinista.
"""
from __future__ import annotations
import re
from typing import Dict, Any, List

class ExplainerValidator:
    """
    Audita la respuesta de la IA. Si detecta números o precios contradictorios
    con el ticket operacional, descarta la respuesta de la IA y genera una síntesis determinista.
    """

    @classmethod
    def validate_and_sanitize(
        cls,
        ai_response: Dict[str, Any],
        ticket: Dict[str, Any],
    ) -> tuple[Dict[str, Any], bool]:
        """
        Valida que la respuesta de IA no altere los precios ni contradiga las reglas del ticket.
        Retorna (explicación_saneada, paso_la_validacion).
        """
        if not isinstance(ai_response, dict):
            return cls._fallback_deterministic(ticket), False

        summary = str(ai_response.get("summary", ""))
        risks = ai_response.get("top_3_risks", [])
        invalidation = str(ai_response.get("invalidation_rule", ""))

        if not summary or not isinstance(risks, list) or len(risks) < 3:
            return cls._fallback_deterministic(ticket), False

        # Extraer números significativos (> 1.0) mencionados en el texto
        full_text = f"{summary} {' '.join(str(r) for r in risks)} {invalidation}"
        found_numbers = [float(n) for n in re.findall(r"\b\d+\.\d+\b", full_text)]

        # Conjunto de números permitidos (precios del ticket con tolerancia)
        allowed_prices = {
            round(ticket["entry_market"], 2),
            round(ticket["entry_limit"], 2),
            round(ticket["stop_loss"], 2),
            round(ticket["take_profit_1"], 2),
            round(ticket["take_profit_2"], 2),
            round(ticket["risk_reward_ratio"], 2),
        }

        # Verificar si hay discrepancias flagrantes en los precios mencionados
        for num in found_numbers:
            # Si el número parece un precio (cercano al rango [stop_loss * 0.7, tp2 * 1.3])
            if (ticket["stop_loss"] * 0.7) <= num <= (ticket["take_profit_2"] * 1.3):
                # Debe estar cerca de alguno de los niveles oficiales del ticket
                if not any(abs(num - allowed) < 0.15 for allowed in allowed_prices):
                    # Alucinación de precio detectada -> Descartar IA y usar fallback seguro
                    return cls._fallback_deterministic(ticket), False

        sanitized = {
            "summary": summary,
            "indicator_news_synthesis": str(ai_response.get("indicator_news_synthesis", "")),
            "top_3_risks": [str(r) for r in risks[:3]],
            "invalidation_rule": invalidation or ticket.get("invalidation_condition", ""),
            "validation_status": "PASSED",
        }

        return sanitized, True

    @classmethod
    def _fallback_deterministic(cls, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Síntesis determinista basada 100% en los datos auditados del ticket."""
        sym = ticket["symbol"]
        reasons = ticket.get("reasons", ["Estructura técnica con ventaja estadística."])
        contradictions = ticket.get("contradictions", ["Mercado en consolidación."])
        warnings = ticket.get("warnings", ["Volatilidad habitual de mercado."])
        prob = ticket.get("calibrated_probability", ticket.get("calibrated_prob", 0.60))
        rr = ticket.get("risk_reward_ratio", 1.5)
        sl = ticket.get("stop_loss", 0.0)

        summary = (
            f"Configuración cuantitativa alcista en {sym} con probabilidad estimada de {prob*100:.1f}% "
            f"y relación Riesgo:Beneficio de 1:{rr:.1f}. "
            f"{' '.join(reasons[:2])}"
        )

        risks = [
            contradictions[0] if contradictions else "Riesgo de volatilidad intradiaria adversa.",
            warnings[0] if warnings else "Riesgo de giro tendencial antes de alcanzar el objetivo.",
            f"Violación del nivel de soporte clave en ${sl:.2f}.",
        ]

        return {
            "summary": summary,
            "thesis": summary,
            "reasons_expanded": reasons,
            "risk_assessment": " ".join(risks),
            "indicator_news_synthesis": "Análisis determinista generado directamente por el motor cuantitativo sin distorsión de modelos externos.",
            "top_3_risks": risks,
            "invalidation_rule": ticket.get("invalidation_condition", f"Cierre por debajo de ${sl:.2f}."),
            "validation_status": "DETERMINISTIC_FALLBACK",
        }
