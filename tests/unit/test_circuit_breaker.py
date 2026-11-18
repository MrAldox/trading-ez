"""
Trading EZ - Tests Unitarios de Circuito de Corte y Bloqueo (Fase 6).
"""
import pytest
from src.opportunities.circuit_breaker import CircuitBreaker

def test_circuit_breaker_blocks_when_data_is_stale():
    status = CircuitBreaker.check_system_readiness(is_data_stale=True)
    assert status.is_blocked is True
    assert status.model_status == "BLOQUEADO"
    assert "desactualizados" in status.reason

def test_circuit_breaker_blocks_consecutive_losses():
    # 4 o más pérdidas seguidas
    status = CircuitBreaker.check_system_readiness(consecutive_losses=4)
    assert status.is_blocked is True
    assert status.model_status == "BLOQUEADO"
    assert "consecutivas" in status.reason
