"""
Pruebas unitarias para el motor de confluencia institucional Smart Money.
"""
from src.opportunities.confluence_engine import confluence_engine

def test_confluence_engine_scan():
    picks = confluence_engine.scan_confluence_opportunities(
        asset_class="all",
        account_capital=10000.0,
        risk_pct=1.0,
        min_confluence_score=0.55,
    )
    assert isinstance(picks, list)
    if picks:
        first = picks[0]
        assert "symbol" in first
        assert "entry_price" in first
        assert "stop_loss" in first
        assert "take_profit_1" in first
        assert "take_profit_2" in first
        assert "recommended_execution_window" in first
        assert "reasons" in first
        assert len(first["reasons"]) > 0
        assert first["expected_r"] > 0
