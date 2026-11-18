"""
Trading EZ - Circuito de Corte y Bloqueo de Seguridad (Circuit Breaker).
Protege el capital bloqueando señales si el modelo no está calibrado, si hay drift
o si los datos de mercado están desactualizados.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.core.config import settings
from src.ml.registry import model_registry

@dataclass
class CircuitBreakerStatus:
    is_blocked: bool
    model_status: str  # "VALIDADO" | "SIN CALIBRAR" | "BLOQUEADO"
    reason: Optional[str]
    last_update: str

class CircuitBreaker:
    """
    Guardián de honestidad y preservación de capital.
    """

    @classmethod
    def check_system_readiness(
        cls,
        is_data_stale: bool = False,
        consecutive_losses: int = 0,
    ) -> CircuitBreakerStatus:
        from datetime import datetime, timezone

        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Chequeo de datos corruptos o desactualizados
        if is_data_stale:
            return CircuitBreakerStatus(
                is_blocked=True,
                model_status="BLOQUEADO",
                reason="Datos de mercado desactualizados (> 24 horas). Señales bloqueadas por seguridad.",
                last_update=now_str,
            )

        # 2. Chequeo de racha perdedora consecutiva (prevención de revenge trading)
        if consecutive_losses >= settings.sizing.consecutive_losses_circuit:
            return CircuitBreakerStatus(
                is_blocked=True,
                model_status="BLOQUEADO",
                reason=f"Circuito de pérdidas consecutivas activado ({consecutive_losses} pérdidas seguidas). Operativa pausada.",
                last_update=now_str,
            )

        # 3. Chequeo del modelo campeón
        champion_data = model_registry.load_champion()
        if not champion_data:
            return CircuitBreakerStatus(
                is_blocked=True,
                model_status="SIN CALIBRAR",
                reason="No existe modelo validado registrado en producción.",
                last_update=now_str,
            )

        _, metadata = champion_data
        model_valid = metadata.get("is_validated", False)
        cal_status = metadata.get("status", "SIN CALIBRAR")

        if not model_valid or cal_status != "VALIDADO":
            return CircuitBreakerStatus(
                is_blocked=True,
                model_status="SIN CALIBRAR",
                reason="El modelo actual no pasó los criterios de validación fuera de muestra (OOS).",
                last_update=now_str,
            )

        return CircuitBreakerStatus(
            is_blocked=False,
            model_status="VALIDADO",
            reason=None,
            last_update=now_str,
        )
