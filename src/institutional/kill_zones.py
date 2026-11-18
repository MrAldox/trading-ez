"""
Trading EZ - Motor de Horarios Bancarios y Kill Zones Institucionales.
Monitorea en tiempo real las ventanas horarias de inyección de liquidez de bancos
y algoritmos institucionales (Smart Money Concepts / ICT).
"""
from __future__ import annotations
from datetime import datetime, timezone, time
from typing import Dict, Any, List, Optional
import zoneinfo

class KillZonesEngine:
    """
    Rastrea las ventanas operativas institucionales en hora de Nueva York (EST/EDT).
    Identifica cuándo los bancos comerciales y fondos de cobertura ejecutan rebalanceos,
    barridos de liquidez y desequilibrios (Fair Value Gaps).
    """

    # Definición de ventanas institucionales en zona horaria America/New_York
    ZONES = [
        {
            "id": "ASIAN_RANGE",
            "name": "Rango de Tokio / Asia",
            "start": time(19, 0),
            "end": time(2, 0),
            "description": "Sesión de consolidación y formación de liquidez en extremos (altos y bajos asiáticos).",
            "action": "Observar o operar solo en cripto. Identificar el rango para el barrido europeo.",
            "impact": "MEDIO",
            "is_kill_zone": False,
        },
        {
            "id": "LONDON_OPEN",
            "name": "Apertura de Londres (London Kill Zone)",
            "start": time(2, 0),
            "end": time(5, 0),
            "description": "Inyección masiva de liquidez europea. Suele crear la manipulación inicial (Judas Swing) barriendo los extremos asiáticos antes de la verdadera tendencia diaria.",
            "action": "Buscar reversiones tras barridos de liquidez del rango asiático.",
            "impact": "ALTO",
            "is_kill_zone": True,
        },
        {
            "id": "NY_OPEN",
            "name": "Apertura de Wall Street (NY Open Kill Zone)",
            "start": time(9, 30),
            "end": time(11, 0),
            "description": "El mayor volumen del planeta. Apertura oficial de la Bolsa de Nueva York. Los algoritmos bancarios ejecutan órdenes TWAP/VWAP y se absorbe la liquidez de los minoristas.",
            "action": "Ventana estelar para acciones, índices (SPY, QQQ) y cripto. Operar a favor de la tendencia tras los primeros 15 minutos.",
            "impact": "CRÍTICO",
            "is_kill_zone": True,
        },
        {
            "id": "SILVER_BULLET_AM",
            "name": "Silver Bullet Institucional (10:00 - 11:00 AM)",
            "start": time(10, 0),
            "end": time(11, 0),
            "description": "Ventana favorita de los operadores de Smart Money. Publicación de datos macroeconómicos de EE.UU. a las 10:00 AM y posterior relleno de desequilibrios (Fair Value Gaps).",
            "action": "Entradas de alta precisión buscando un ratio 1:2 o 1:3 hacia la liquidez opuesta.",
            "impact": "CRÍTICO",
            "is_kill_zone": True,
        },
        {
            "id": "LONDON_CLOSE",
            "name": "London Fix & Cierre de Londres (11:00 - 12:00 PM)",
            "start": time(11, 0),
            "end": time(12, 0),
            "description": "Cierre de la jornada en Londres y fijación de precios de divisas (London 4 PM Fix). Toma de ganancias institucional y contracciones de tendencia.",
            "action": "Cerrar posiciones intradiarias o asegurar ganancias en TP1.",
            "impact": "ALTO",
            "is_kill_zone": True,
        },
        {
            "id": "NY_PM_MOC",
            "name": "Cierre de Wall Street & MOC (3:00 - 4:00 PM)",
            "start": time(15, 0),
            "end": time(16, 0),
            "description": "Market On Close: Fondos mutuos y ETFs (SPY/QQQ) rebalancean miles de millones de dólares antes de la campana de cierre a las 16:00.",
            "action": "Operar movimientos tendenciales de fin de jornada o evitar el ruido del último minuto.",
            "impact": "ALTO",
            "is_kill_zone": True,
        },
    ]

    @classmethod
    def get_current_ny_time(cls) -> datetime:
        """Devuelve la fecha y hora actual en la zona de Nueva York."""
        try:
            tz = zoneinfo.ZoneInfo("America/New_York")
            return datetime.now(tz)
        except Exception:
            # Fallback en caso de que falte tzdata
            return datetime.now(timezone.utc)

    @classmethod
    def get_market_sessions_status(cls) -> Dict[str, Any]:
        """
        Determina qué sesión y kill zone bancaria está activa en este instante.
        """
        ny_now = cls.get_current_ny_time()
        current_time = ny_now.time()
        is_weekend = ny_now.weekday() in (5, 6)

        active_zones = []
        is_active_kill_zone = False

        for zone in cls.ZONES:
            s = zone["start"]
            e = zone["end"]

            # Si la ventana cruza la medianoche (como Asia: 19:00 a 02:00)
            if s > e:
                in_range = current_time >= s or current_time < e
            else:
                in_range = s <= current_time < e

            if in_range:
                active_zones.append(zone)
                if zone["is_kill_zone"]:
                    is_active_kill_zone = True

        primary_zone = active_zones[0] if active_zones else None

        # Mensaje de asesoría táctica según el horario
        if is_weekend:
            tactical_advice = (
                "Mercados tradicionales cerrados por fin de semana. "
                "Criptomonedas activas 24/7 (BTC/ETH). Mayor probabilidad de barridos en rangos estrechos."
            )
            status_indicator = "FIN DE SEMANA (CRIPTO ACTIVO)"
            indicator_color = "warning"
        elif is_active_kill_zone and primary_zone:
            tactical_advice = (
                f"🚨 VENTANA BANCARIA ACTIVA: {primary_zone['name']}. "
                f"{primary_zone['action']}"
            )
            status_indicator = f"VENTANA ACTIVA: {primary_zone['name']}"
            indicator_color = "profit"
        else:
            tactical_advice = (
                "Fuera de ventanas bancarias principales. "
                "El volumen suele ser menor y los spreads pueden ampliarse. "
                "La mayor ventaja estadística ocurre durante la apertura de NY (09:30 - 11:00 EST)."
            )
            status_indicator = "MERCADO EN ESPERA (FUERA DE KILL ZONE)"
            indicator_color = "neutral"

        return {
            "current_ny_time": ny_now.strftime("%Y-%m-%d %H:%M:%S EST"),
            "ny_hour_decimal": ny_now.hour + (ny_now.minute / 60.0),
            "is_weekend": is_weekend,
            "is_kill_zone_active": is_active_kill_zone and not is_weekend,
            "status_indicator": status_indicator,
            "indicator_color": indicator_color,
            "active_zones": active_zones,
            "primary_zone": primary_zone,
            "tactical_advice": tactical_advice,
            "all_zones": cls.ZONES,
        }

kill_zones_engine = KillZonesEngine()
