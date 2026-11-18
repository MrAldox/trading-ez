"""
Trading EZ - Constructor Determinista de Fichas Operativas de Oportunidad.
Genera la ficha completa lista para copiar y pegar, sin ambigüedades ni inventar números.
"""
from __future__ import annotations
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd

from src.core.config import settings, AssetMetadata
from src.opportunities.sizing import calculate_position_size, SizingResult

class TicketBuilder:
    """
    Construye de forma algorítmica y determinista el ticket de operación de Trading EZ.
    """

    @classmethod
    def build_ticket(
        cls,
        symbol: str,
        asset: AssetMetadata,
        latest_bar: pd.Series,
        calibrated_prob: float,
        expected_r: float,
        model_version: str,
        account_capital: float = 10000.0,
        risk_pct: float = 1.0,
        earnings_info: Optional[Dict[str, Any]] = None,
        data_source: str = "live",
    ) -> Dict[str, Any]:
        close_p = float(latest_bar["close"])
        atr_val = float(latest_bar.get("atr_14", close_p * 0.02))

        # 1. Definición de niveles de precios (LONG)
        risk_dist = max(1.2 * atr_val, close_p * 0.008)
        entry_market = round(close_p, 2)
        # Entrada alternativa en retroceso (pullback al EMA 9 o EMA 21)
        entry_limit = round(min(close_p, float(latest_bar.get("ema_9", close_p * 0.99))), 2)

        stop_loss = round(entry_market - risk_dist, 2)
        take_profit_1 = round(entry_market + (1.6 * risk_dist), 2)
        take_profit_2 = round(entry_market + (3.0 * risk_dist), 2)
        rr_ratio = round((take_profit_1 - entry_market) / (entry_market - stop_loss), 2)

        # 2. Gestión de capital y dimensionamiento
        sizing = calculate_position_size(
            account_capital=account_capital,
            entry_price=entry_market,
            stop_loss=stop_loss,
            risk_pct=risk_pct,
            max_position_size_pct=settings.sizing.max_position_size_pct,
        )

        # 3. Desglose de puntuación por dominio
        trend_score = 0.85 if float(latest_bar.get("trend_alignment_bullish", 0)) == 1.0 else 0.70
        momentum_score = 0.80 if float(latest_bar.get("macd_accelerating", 0)) == 1.0 else 0.65
        vol_score = 0.75 if float(latest_bar.get("rvol_20", 1.0)) >= 1.2 else 0.50
        market_score = 0.90 if float(latest_bar.get("benchmark_above_ema50", 1.0)) == 1.0 else 0.40

        # 4. Motivos algorítmicos (Reasons)
        reasons: List[str] = []
        if float(latest_bar.get("trend_alignment_bullish", 0)) == 1.0:
            reasons.append("Alineación alcista canónica: precio sobre EMA 21, 50 y 200 con pendientes positivas.")
        else:
            reasons.append("Estructura técnica de soporte sobre media móvil EMA 50.")

        if float(latest_bar.get("rvol_20", 1.0)) >= 1.2:
            reasons.append(f"Volumen relativo institucional (RVOL {float(latest_bar['rvol_20']):.1f}x) respaldando el impulso.")

        if float(latest_bar.get("pattern_bullish_engulfing", 0)) == 1.0:
            reasons.append("Confirmación con patrón de vela Envolvente Alcista (Bullish Engulfing).")
        elif float(latest_bar.get("pattern_hammer", 0)) == 1.0:
            reasons.append("Rechazo de mínimos con vela Martillo (Hammer) en zona de soporte.")

        if float(latest_bar.get("relative_strength_momentum", 0)) > 0:
            reasons.append("Fuerza relativa positiva sostenida contra el índice de referencia de mercado.")

        # 5. Contradicciones y advertencias
        contradictions: List[str] = []
        rsi_val = float(latest_bar.get("rsi_14", 50.0))
        if rsi_val > 65.0:
            contradictions.append(f"RSI(14) en {rsi_val:.1f} aproximándose a zona de sobrecompra técnica.")
        elif rsi_val < 45.0:
            contradictions.append(f"RSI(14) en {rsi_val:.1f} mostrando debilidad momentánea en el impulso.")

        if float(latest_bar.get("bb_bandwidth", 0)) > 0.20:
            contradictions.append("Ancho de Bandas de Bollinger expandido, indicando volatilidad reciente elevada.")

        warnings: List[str] = []
        if earnings_info and earnings_info.get("days_away", 999) <= 14:
            warnings.append(f"Publicación de resultados trimestrales (Earnings) en {earnings_info['days_away']} días. Reducir o cerrar antes del anuncio.")

        vol_regime = float(latest_bar.get("volatility_regime_pct", 0.50))
        if vol_regime > 0.75:
            warnings.append(f"Régimen de volatilidad en el percentil {int(vol_regime*100)} histórico. Riesgo de sacudidas de precio.")

        invalidation = f"Cierre de vela diaria por debajo de ${stop_loss:.2f} o pérdida del mínimo previo invalida la hipótesis alcista."

        # 6. Formatos de orden listos para copiar
        text_order = (
            f"COMPRAR {sizing.effective_shares} {symbol} @ mercado (ref. {entry_market:.2f}) | "
            f"STOP {stop_loss:.2f} | TP1 {take_profit_1:.2f} | TP2 {take_profit_2:.2f} | "
            f"Riesgo ${sizing.effective_risk_dollars:.2f} ({sizing.effective_risk_pct:.2f}%) | R:B 1:{rr_ratio:.1f}"
        )

        bracket_json = {
            "symbol": symbol,
            "qty": sizing.effective_shares,
            "side": "buy",
            "type": "market",
            "time_in_force": "gtc",
            "order_class": "bracket",
            "stop_loss": {"stop_price": stop_loss},
            "take_profit": {"limit_price": take_profit_1},
        }

        now_str = datetime.now(timezone.utc).isoformat()
        opp_id = f"opp_{now_str[:10].replace('-', '')}_{symbol}"

        return {
            "id": opp_id,
            "symbol": symbol,
            "name": asset.name,
            "asset_class": asset.asset_class,
            "sector": asset.sector,
            "direction": "LONG",
            "horizon": "medium",
            "calibrated_prob": round(calibrated_prob, 3),
            "expected_r": round(expected_r, 2),
            "entry_market": entry_market,
            "entry_limit": entry_limit,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "risk_reward_ratio": rr_ratio,
            "sizing": {
                "account_capital": sizing.account_capital,
                "risk_pct": sizing.risk_pct,
                "capital_at_risk": sizing.capital_at_risk,
                "position_size": sizing.effective_shares,
                "effective_notional": sizing.effective_notional,
                "portfolio_pct": sizing.portfolio_pct,
                "capped_by_rule": sizing.capped_by_rule,
                "effective_capital_at_risk": sizing.effective_risk_dollars,
            },
            "score_breakdown": {
                "trend_score": trend_score,
                "momentum_score": momentum_score,
                "volatility_regime": round(1.0 - vol_regime, 2),
                "market_alignment": market_score,
                "volume_support": vol_score,
            },
            "reasons": reasons,
            "contradictions": contradictions,
            "warnings": warnings,
            "invalidation_condition": invalidation,
            "order_formats": {
                "text": text_order,
                "bracket_json": bracket_json,
            },
            "data_source": data_source,
            "timestamp": now_str,
        }
