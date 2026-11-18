"""
Trading EZ - Tests Unitarios de la Capa de IA Generativa y Validador Anti-Alucinaciones (Fase 7).
"""
import pytest
from src.ai_explainer.validator import ExplainerValidator
from src.ai_explainer.client import AIExplainerClient

@pytest.fixture
def sample_ticket():
    return {
        "symbol": "NVDA",
        "entry_market": 142.50,
        "entry_limit": 141.20,
        "stop_loss": 138.90,
        "take_profit_1": 147.90,
        "take_profit_2": 153.30,
        "risk_reward_ratio": 2.50,
        "calibrated_prob": 0.65,
        "reasons": ["Ruptura de consolidación con volumen relativo 1.8x.", "Precio sobre EMA 21."],
        "contradictions": ["RSI en 66.8."],
        "warnings": ["Earnings en 14 días."],
        "invalidation_condition": "Cierre bajo 138.90.",
    }

def test_validator_accepts_coherent_ai_response(sample_ticket):
    ai_response = {
        "summary": "Oportunidad alcista en NVDA con entrada de mercado en 142.50 y objetivo 147.90.",
        "indicator_news_synthesis": "Volumen consistente con noticias de semiconductores.",
        "top_3_risks": ["Riesgo de pullback a 141.20.", "Volatilidad del sector.", "Pérdida del stop en 138.90."],
        "invalidation_rule": "Cierre bajo 138.90 anula la idea.",
    }

    sanitized, passed = ExplainerValidator.validate_and_sanitize(ai_response, sample_ticket)
    assert passed is True
    assert sanitized["validation_status"] == "PASSED"
    assert len(sanitized["top_3_risks"]) == 3

def test_validator_rejects_hallucinated_price_numbers(sample_ticket):
    # La IA alucina un precio inventado (p. ej. "Stop en 120.00" o "Objetivo 185.00")
    hallucinated_response = {
        "summary": "Comprar NVDA pero poner stop en 125.00 y objetivo en 180.00.",
        "indicator_news_synthesis": "Noticias inventadas.",
        "top_3_risks": ["Riesgo A", "Riesgo B", "Riesgo C"],
        "invalidation_rule": "Caída a 125.00.",
    }

    sanitized, passed = ExplainerValidator.validate_and_sanitize(hallucinated_response, sample_ticket)
    # Debe ser descartada y reemplazada por el fallback determinista
    assert passed is False
    assert sanitized["validation_status"] == "DETERMINISTIC_FALLBACK"
    assert "138.90" in sanitized["invalidation_rule"]

def test_client_fallback_without_api_keys(sample_ticket):
    client = AIExplainerClient()
    explanation = client.explain_opportunity(sample_ticket)
    assert explanation is not None
    assert "summary" in explanation
    assert len(explanation["top_3_risks"]) == 3
    assert explanation["validation_status"] in ("PASSED", "DETERMINISTIC_FALLBACK")
