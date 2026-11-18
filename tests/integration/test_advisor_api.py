"""
Pruebas de integración para los endpoints del Asesor Financiero IA y Horarios Bancarios.
"""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_advisor_chat_endpoint():
    payload = {"message": "¿A qué hora operan los bancos y cómo aprovecho el movimiento?"}
    res = client.post("/api/advisor/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert "Kill Zones" in data["response"] or "banco" in data["response"].lower()
    assert "session_context" in data

def test_advisor_kill_zones_endpoint():
    res = client.get("/api/advisor/kill-zones")
    assert res.status_code == 200
    data = res.json()
    assert "current_ny_time" in data
    assert "status_indicator" in data
    assert "all_zones" in data

def test_advisor_daily_briefing_endpoint():
    res = client.get("/api/advisor/daily-briefing")
    assert res.status_code == 200
    data = res.json()
    assert "briefing" in data
    assert "session_state" in data

def test_opportunities_with_confluence_fallback():
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "opportunities" in data
    # Ahora el sistema entrega oportunidades de confluencia institucional
    assert data["status"] in ["VALIDADO", "VALIDADO (CONFLUENCIA INSTITUCIONAL)", "CONFLUENCIA INSTITUCIONAL"]
    assert len(data["opportunities"]) > 0
