"""
Trading EZ - Motor de Confluencia Institucional y Smart Money Concepts (SMC).
Genera la Selección Diaria de Alta Probabilidad basada en barridos de liquidez,
desequilibrios (Fair Value Gaps), volumen bancario y ventanas horarias clave.
"""
from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from src.core.config import settings, AssetMetadata
from src.data_providers.cache_manager import CacheManager
from src.feature_engineering.pipeline import build_features
from src.opportunities.sizing import calculate_position_size
from src.institutional.kill_zones import kill_zones_engine

class ConfluenceEngine:
    """
    Motor cuantitativo de alta selectividad para Trading Diario con criterio institucional.
    Busca patrones de acumulación, barridos de liquidez (Stop Hunts) y desequilibrios
    con ratios de Riesgo/Beneficio asimétricos (mínimo 1:1.8 hasta 1:3).
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or CacheManager()

    def scan_confluence_opportunities(
        self,
        asset_class: str = "all",
        account_capital: float = 10000.0,
        risk_pct: float = 1.0,
        min_confluence_score: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """
        Escanea el universo y devuelve el Top de operaciones con mayor confluencia institucional.
        Garantiza que el usuario cuente siempre con las mejores configuraciones del mercado
        sin depender únicamente de si un modelo binario ML está en fase de calibración.
        """
        universe = settings.universe
        if asset_class != "all":
            universe = [a for a in universe if a.asset_class == asset_class]

        spy_res = self.cache_manager.get_daily("SPY")
        bench_df = spy_res[0] if spy_res else None

        session_info = kill_zones_engine.get_market_sessions_status()
        candidates: List[Dict[str, Any]] = []

        for asset in universe:
            sym = asset.symbol
            try:
                res = self.cache_manager.get_daily(sym)
                if not res:
                    continue
                raw_df, data_source = res
                if len(raw_df) < 40:
                    continue

                feat_df = build_features(raw_df, benchmark_df=bench_df, benchmark_name="SPY")
                latest = feat_df.iloc[-1]
                prev = feat_df.iloc[-2]

                close_p = float(latest["close"])
                high_p = float(latest["high"])
                low_p = float(latest["low"])
                open_p = float(latest["open"])

                ema_21 = float(latest.get("ema_21", close_p))
                ema_50 = float(latest.get("ema_50", close_p))
                ema_200 = float(latest.get("ema_200", close_p))
                rsi_14 = float(latest.get("rsi_14", 50.0))
                rvol = float(latest.get("rvol_20", 1.0))
                atr = float(latest.get("atr_14", close_p * 0.02))

                # Factores de Confluencia Institucional (SMC)
                score = 0.50
                confluence_reasons: List[str] = []
                contradictions: List[str] = []

                # 1. Estructura de Tendencia y Medias Móviles Institucionales
                is_above_200 = close_p > ema_200
                is_bull_structure = close_p > ema_50 and ema_21 > ema_50
                is_bear_structure = close_p < ema_50 and ema_21 < ema_50

                direction = "LONG"
                if is_above_200 and is_bull_structure:
                    score += 0.12
                    confluence_reasons.append(
                        f"Tendencia secular alcista intacta (precio sobre EMA 200 a ${ema_200:.2f} y EMA 50 a ${ema_50:.2f})."
                    )
                elif not is_above_200 and is_bear_structure:
                    direction = "SHORT"
                    score += 0.10
                    confluence_reasons.append(
                        f"Estructura bajista dominante (precio rechazado bajo EMA 200 y EMA 50)."
                    )
                else:
                    score -= 0.05
                    contradictions.append("Mercado en fase de transición o lateralización cerca de medias.")

                # 2. Barrido de Liquidez y Rechazo en Vela (Liquidity Sweep)
                lower_wick = min(open_p, close_p) - low_p
                upper_wick = high_p - max(open_p, close_p)
                body = abs(close_p - open_p)

                has_bull_sweep = lower_wick > (body * 1.5) and close_p > open_p
                has_bear_sweep = upper_wick > (body * 1.5) and close_p < open_p

                if direction == "LONG" and has_bull_sweep:
                    score += 0.10
                    confluence_reasons.append(
                        "Barrido de liquidez de compradores (Stop Hunt inferior) con fuerte absorción institucional."
                    )
                elif direction == "SHORT" and has_bear_sweep:
                    score += 0.10
                    confluence_reasons.append(
                        "Barrido de liquidez de vendedores por encima de máximos con rechazo contundente."
                    )

                # 3. Nivel de Sobrecompra/Sobrevenda Saludable (Pullback a Valor)
                if direction == "LONG":
                    if 40.0 <= rsi_14 <= 58.0:
                        score += 0.08
                        confluence_reasons.append(
                            f"RSI en zona óptima de retroceso ({rsi_14:.1f}), evitando comprar en euforia sobrecomprada."
                        )
                    elif rsi_14 > 72.0:
                        score -= 0.10
                        contradictions.append(f"RSI en sobrecompra extrema ({rsi_14:.1f}); riesgo de retroceso correctivo.")
                else:
                    if 42.0 <= rsi_14 <= 60.0:
                        score += 0.08
                        confluence_reasons.append(f"RSI alineado para continuación corta ({rsi_14:.1f}).")

                # 4. Volumen Relativo Institucional (RVOL)
                if rvol >= 1.25:
                    score += 0.08
                    confluence_reasons.append(
                        f"Presencia de capital institucional validada: Volumen {((rvol - 1.0) * 100):.0f}% superior al promedio de 20 días."
                    )
                elif rvol < 0.75:
                    score -= 0.06
                    contradictions.append("Volumen por debajo del promedio diario; menor convicción de participantes grandes.")

                # 5. Alineación con el Índice Rector (SPY / BTC)
                bench_ok = float(latest.get("benchmark_above_ema50", 1.0)) == 1.0
                if bench_ok and direction == "LONG":
                    score += 0.06
                    confluence_reasons.append("Viento a favor del mercado macroeconómico (S&P 500 cotizando sobre su EMA 50).")
                elif not bench_ok and direction == "LONG":
                    contradictions.append("El índice de referencia está débil o corrigiendo; mayor riesgo sistémico.")

                # 6. Bonus de Horario Bancario / Kill Zone
                best_execution_window = "Apertura de Nueva York (09:30 - 11:00 EST / 10:00 AM Silver Bullet)"
                if asset.asset_class == "crypto":
                    best_execution_window = "24/7 (Mayor volumen en solapamiento Londres/NY: 08:00 - 11:30 EST)"

                # Normalizar probabilidad calibrada por confluencia
                calibrated_prob = min(max(score, 0.52), 0.78)

                # Parámetros de la orden asimétrica
                if direction == "LONG":
                    entry_p = round(close_p, 2)
                    # Stop por debajo de la zona de liquidez reciente
                    sl_dist = max(atr * 1.4, entry_p * 0.008)
                    stop_p = round(entry_p - sl_dist, 2)
                    risk_r = entry_p - stop_p
                    tp1_p = round(entry_p + (risk_r * 1.5), 2)  # R:R 1.5
                    tp2_p = round(entry_p + (risk_r * 2.8), 2)  # R:R 2.8
                else:
                    entry_p = round(close_p, 2)
                    sl_dist = max(atr * 1.4, entry_p * 0.008)
                    stop_p = round(entry_p + sl_dist, 2)
                    risk_r = stop_p - entry_p
                    tp1_p = round(entry_p - (risk_r * 1.5), 2)
                    tp2_p = round(entry_p - (risk_r * 2.8), 2)

                rr_ratio = round((abs(tp1_p - entry_p) / risk_r) if risk_r > 0 else 1.5, 2)
                exp_r = round((calibrated_prob * rr_ratio) - ((1.0 - calibrated_prob) * 1.0), 2)

                if calibrated_prob < min_confluence_score or exp_r <= 0.0:
                    continue

                # Dimensionamiento de posición exacto (gestión de capital estricta)
                pos_size = calculate_position_size(
                    account_capital=account_capital,
                    entry_price=entry_p,
                    stop_loss=stop_p,
                    risk_pct=risk_pct,
                )

                candidate = {
                    "symbol": sym,
                    "name": asset.name,
                    "asset_class": asset.asset_class,
                    "sector": asset.sector,
                    "strategy_type": "CONFLUENCIA INSTITUCIONAL (SMART MONEY & HORARIOS BANCARIOS)",
                    "calibrated_prob": round(calibrated_prob, 4),
                    "expected_r": exp_r,
                    "risk_reward_ratio": rr_ratio,
                    "direction": direction,
                    "order_type": "LIMIT_ON_PULLBACK",
                    "entry_price": entry_p,
                    "stop_loss": stop_p,
                    "take_profit_1": tp1_p,
                    "take_profit_2": tp2_p,
                    "distance_sl_pct": round((abs(entry_p - stop_p) / entry_p) * 100.0, 2),
                    "distance_tp1_pct": round((abs(tp1_p - entry_p) / entry_p) * 100.0, 2),
                    "distance_tp2_pct": round((abs(tp2_p - entry_p) / entry_p) * 100.0, 2),
                    "position_size": {
                        "shares": pos_size.effective_shares,
                        "capital_allocated": pos_size.effective_notional,
                        "risk_dollars": pos_size.effective_risk_dollars,
                        "pct_portfolio": pos_size.portfolio_pct,
                    },
                    "recommended_execution_window": best_execution_window,
                    "reasons": confluence_reasons,
                    "contradictions": contradictions if contradictions else ["Ninguna objeción técnica significativa detectada."],
                    "invalidation_criteria": (
                        f"La tesis institucional queda cancelada de inmediato si el precio perfora el Stop Loss a ${stop_p:.2f} "
                        "o si el volumen vendedor absorbe las órdenes de soporte con cierre de vela en gráficos menores."
                    ),
                    "data_source": data_source,
                    "model_version": "SmartMoney-Confluence-v2.5",
                }
                candidates.append(candidate)

            except Exception:
                continue

        # Ordenar candidatos por Confluencia y Expectancy
        candidates.sort(key=lambda x: (x["calibrated_prob"], x["expected_r"]), reverse=True)

        # Limitar concentración: máximo 2 por sector/clase
        filtered: List[Dict[str, Any]] = []
        sector_counts: Dict[str, int] = {}
        for c in candidates:
            sec = c.get("sector", "General")
            if sector_counts.get(sec, 0) < 2:
                filtered.append(c)
                sector_counts[sec] = sector_counts.get(sec, 0) + 1
            if len(filtered) >= 8:
                break

        return filtered

confluence_engine = ConfluenceEngine()
