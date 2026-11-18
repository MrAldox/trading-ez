"""
Trading EZ - Tests de Integración de Endpoints FastAPI.
Verifica que todas las rutas respondan con los códigos de estado y esquemas correctos.
"""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

@pytest.fixture(scope="module")
def client():
    # Desactivar temporalmente scheduler en tests para evitar hilos residuales
    with TestClient(app) as c:
        yield c

def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Trading EZ" in data["app"]

def test_get_opportunities(client):
    response = client.get("/api/opportunities?asset_class=all&horizon=medium")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "opportunities" in data
    assert isinstance(data["opportunities"], list)

def test_explain_opportunity(client):
    mock_ticket = {
        "symbol": "SPY",
        "direction": "LONG",
        "entry_price": 500.0,
        "stop_loss": 490.0,
        "take_profit_1": 515.0,
        "take_profit_2": 530.0,
        "calibrated_probability": 0.65,
        "risk_distance_pct": 2.0,
        "reasons": ["RSI sobrevendido", "Sobre EMA 200"],
        "contradictions": [],
        "warnings": [],
    }
    response = client.post(
        "/api/opportunities/SPY/explain",
        json={"ticket": mock_ticket},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert "ai_explanation" in data
    assert "thesis" in data["ai_explanation"]

def test_market_live_quotes(client):
    response = client.get("/api/market/live?symbols=SPY,QQQ")
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
    assert len(data["quotes"]) >= 1

def test_market_history(client):
    response = client.get("/api/market/history?symbol=SPY&bars=30")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert "candles" in data
    assert len(data["candles"]) > 0
    first = data["candles"][0]
    assert "close" in first
    assert "volume" in first

def test_market_heatmap(client):
    response = client.get("/api/market/heatmap")
    assert response.status_code == 200
    data = response.json()
    assert "heatmap" in data
    assert isinstance(data["heatmap"], list)

def test_model_status(client):
    response = client.get("/api/model/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "available_versions_for_rollback" in data

def test_paper_trading_lifecycle(client):
    # 1. Reset portfolio
    reset_res = client.post("/api/paper/reset", json={"capital": 20000.0})
    assert reset_res.status_code == 200
    assert reset_res.json()["portfolio"]["cash"] == 20000.0

    # 2. Consultar cartera
    get_res = client.get("/api/paper/portfolio")
    assert get_res.status_code == 200
    port = get_res.json()["portfolio"]
    assert port["cash"] == 20000.0

    # 3. Ejecutar orden
    order_res = client.post(
        "/api/paper/order",
        json={
            "symbol": "SPY",
            "direction": "LONG",
            "shares": 5,
            "stop_loss": 480.0,
            "take_profit_1": 520.0,
        },
    )
    assert order_res.status_code == 200
    pos = order_res.json()["position"]
    assert pos["symbol"] == "SPY"
    assert pos["shares"] == 5

def test_screener_endpoint(client):
    response = client.get("/api/screener?above_ema200=true")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)

def test_news_endpoint(client):
    response = client.get("/api/news")
    assert response.status_code == 200
    data = response.json()
    assert "news" in data
    assert len(data["news"]) > 0

def test_calendar_endpoint(client):
    response = client.get("/api/calendar")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert len(data["events"]) > 0

def test_alerts_lifecycle(client):
    # 1. Crear alerta
    create_res = client.post(
        "/api/alerts",
        json={"symbol": "AAPL", "condition": "ABOVE", "target_value": 250.0},
    )
    assert create_res.status_code == 200
    alert_id = create_res.json()["id"]

    # 2. Listar alertas
    list_res = client.get("/api/alerts")
    assert list_res.status_code == 200
    alerts = list_res.json()["alerts"]
    assert any(a["id"] == alert_id for a in alerts)

    # 3. Eliminar alerta
    del_res = client.delete(f"/api/alerts/{alert_id}")
    assert del_res.status_code == 200

def test_journal_lifecycle(client):
    # 1. Crear nota
    create_res = client.post(
        "/api/journal",
        json={
            "symbol": "NVDA",
            "notes": "Entrada técnica en pullback sobre EMA 21",
            "signal_prob": 0.64,
            "actual_outcome_r": 1.5,
            "lessons_learned": "Respetar el ratio R:B funciona en el largo plazo",
        },
    )
    assert create_res.status_code == 200

    # 2. Listar notas
    list_res = client.get("/api/journal")
    assert list_res.status_code == 200
    entries = list_res.json()["entries"]
    assert len(entries) > 0
    assert any(e["symbol"] == "NVDA" for e in entries)
