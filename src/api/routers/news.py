"""
Trading EZ - Router de Noticias y Sentimiento de Mercado.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/news", tags=["Noticias"])

# Feed curado y estructurado de noticias financieras de impacto
SAMPLE_NEWS = [
    {
        "id": "news_1",
        "title": "La Reserva Federal evalúa la trayectoria de las tasas de interés ante datos de empleo",
        "ticker": "SPY",
        "source": "Bloomberg / Reuters",
        "sentiment_score": 0.15,
        "sentiment_label": "NEUTRAL_BULLISH",
        "url": "https://www.bloomberg.com",
        "published_at": "Hace 2 horas",
    },
    {
        "id": "news_2",
        "title": "Aceleración de demanda de infraestructura para centros de datos impulsa a semiconductores",
        "ticker": "NVDA",
        "source": "MarketWatch",
        "sentiment_score": 0.72,
        "sentiment_label": "BULLISH",
        "url": "https://www.marketwatch.com",
        "published_at": "Hace 3 horas",
    },
    {
        "id": "news_3",
        "title": "Bitcoin mantiene consolidación sobre medias móviles institucionales con acumulación de ETFs",
        "ticker": "BTC-USD",
        "source": "CoinDesk",
        "sentiment_score": 0.55,
        "sentiment_label": "BULLISH",
        "url": "https://www.coindesk.com",
        "published_at": "Hace 4 horas",
    },
    {
        "id": "news_4",
        "title": "El petróleo retrocede levemente ante previsiones de oferta de la OPEP+",
        "ticker": "USO",
        "source": "Financial Times",
        "sentiment_score": -0.25,
        "sentiment_label": "BEARISH",
        "url": "https://www.ft.com",
        "published_at": "Hace 5 horas",
    },
    {
        "id": "news_5",
        "title": "Apple expande servicios y funciones de software en nuevos mercados",
        "ticker": "AAPL",
        "source": "CNBC",
        "sentiment_score": 0.40,
        "sentiment_label": "BULLISH",
        "url": "https://www.cnbc.com",
        "published_at": "Hace 6 horas",
    },
]

@router.get("")
def get_market_news(ticker: Optional[str] = Query(None, description="Filtrar por ticker (ej. NVDA)")):
    if ticker:
        sym = ticker.strip().upper()
        filtered = [n for n in SAMPLE_NEWS if n["ticker"] == sym]
        return {"count": len(filtered), "news": filtered}
    return {"count": len(SAMPLE_NEWS), "news": SAMPLE_NEWS}
