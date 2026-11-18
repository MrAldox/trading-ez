"""
Trading EZ - Excepciones de Dominio y Errores Tipados.
"""

class TradingEZError(Exception):
    """Excepción base del sistema Trading EZ."""
    pass

class DataIntegrityError(TradingEZError):
    """Lanzada cuando un conjunto de datos viola las reglas de integridad de mercado."""
    def __init__(self, symbol: str, reason: str, details: dict | None = None):
        super().__init__(f"Error de integridad en activo '{symbol}': {reason}")
        self.symbol = symbol
        self.reason = reason
        self.details = details or {}

class DataStaleError(TradingEZError):
    """Lanzada cuando los datos de mercado superan el umbral de obsolescencia permitido."""
    def __init__(self, symbol: str, last_timestamp: str, hours_elapsed: float, max_allowed: float):
        super().__init__(
            f"Datos obsoletos para '{symbol}'. Última actualización: {last_timestamp} "
            f"({hours_elapsed:.1f}h transcurridas, máximo permitido: {max_allowed:.1f}h)"
        )
        self.symbol = symbol
        self.last_timestamp = last_timestamp
        self.hours_elapsed = hours_elapsed
        self.max_allowed = max_allowed

class CircuitBreakerError(TradingEZError):
    """Lanzada cuando el circuito de corte del terminal bloquea las señales."""
    def __init__(self, reason: str, details: dict | None = None):
        super().__init__(f"CIRCUITO DE CORTE ACTIVADO - OPERACIONES BLOQUEADAS: {reason}")
        self.reason = reason
        self.details = details or {}

class ProviderError(TradingEZError):
    """Error al comunicarse con un proveedor externo de datos de mercado."""
    def __init__(self, provider: str, symbol: str, message: str):
        super().__init__(f"Error en proveedor '{provider}' para activo '{symbol}': {message}")
        self.provider = provider
        self.symbol = symbol

class LookaheadError(TradingEZError):
    """Error crítico: se detectó fuga de datos futuros (lookahead bias)."""
    def __init__(self, context: str):
        super().__init__(f"VIOLACIÓN DE INTEGRIDAD TEMPORAL (Lookahead Bias): {context}")
        self.context = context

class ModelNotValidatedError(TradingEZError):
    """Lanzada cuando se intenta solicitar un ranking y el modelo no pasa la validación OOS."""
    def __init__(self, reason: str):
        super().__init__(f"Modelo no validado para producción: {reason}")
        self.reason = reason
