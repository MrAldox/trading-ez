"""
Pruebas unitarias para el motor de Horarios Bancarios y Kill Zones Institucionales.
"""
from src.institutional.kill_zones import kill_zones_engine

def test_kill_zones_status_structure():
    status = kill_zones_engine.get_market_sessions_status()
    assert "current_ny_time" in status
    assert "is_kill_zone_active" in status
    assert "status_indicator" in status
    assert "tactical_advice" in status
    assert "all_zones" in status
    assert len(status["all_zones"]) >= 5

def test_kill_zones_definitions():
    zones = kill_zones_engine.ZONES
    zone_ids = [z["id"] for z in zones]
    assert "LONDON_OPEN" in zone_ids
    assert "NY_OPEN" in zone_ids
    assert "SILVER_BULLET_AM" in zone_ids
    assert "LONDON_CLOSE" in zone_ids
