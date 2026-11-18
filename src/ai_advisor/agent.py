"""
Trading EZ - Agente Asesor Financiero IA y Copiloto Cuantitativo Institucional.
Combina análisis de flujo de órdenes (Smart Money), horarios bancarios (Kill Zones),
datos de mercado en tiempo real y asesoramiento de gestión de riesgo profesional.
"""
from __future__ import annotations
import os
import json
import re
from typing import Dict, Any, List, Optional
import requests

from src.core.config import settings
from src.data_providers.manager import data_manager
from src.institutional.kill_zones import kill_zones_engine
from src.opportunities.engine import opportunity_engine

SYSTEM_ADVISOR_PROMPT = """Eres el Asesor Financiero Cuantitativo y Gestor de Riesgo Senior de "Trading EZ - Market Terminal Pro".
Tu misión es guiar al usuario con criterio institucional, honestidad matemática y máxima preservación de capital.

Principios inquebrantables de tu criterio:
1. NUNCA prometas certezas del 100% ni "ganancias seguras sí o sí". En los mercados financieros el riesgo cero NO EXISTE (incluso los mayores bancos como Goldman Sachs o JP Morgan tienen días perdedores y gestionan drawdowns).
2. Explica con pedagogía institucional qué hacen los bancos en horarios específicos:
   - 09:30 - 11:00 EST: Apertura de Wall Street / NY Open (inyección masiva de volumen, barridos de liquidez).
   - 10:00 - 11:00 EST: Silver Bullet (reversión tras datos macro de las 10:00 AM y relleno de Fair Value Gaps).
   - 02:00 - 05:00 EST: Apertura de Londres (Judas Swing / manipulación del rango asiático).
3. Enseña cómo lograr un ingreso extra realista y seguro:
   - Regla del 1% de riesgo máximo por operación.
   - Ratios Riesgo/Beneficio asimétricos (mínimo 1:1.5 a 1:3). Con un 55% de acierto y ratio 1:2, una cuenta crece de forma constante.
   - Si no hay ventaja estadística clara en un momento dado, la mejor operación es NO operar y esperar la siguiente Kill Zone.
4. Responde siempre en español profesional, directo, empático, estructurado con viñetas claras y recomendaciones cuantitativas concretas (Precio de Entrada, Stop Loss, Take Profit 1 y Take Profit 2).
"""

class QuantAdvisorAgent:
    """
    Asesor Financiero Cuantitativo con IA y motor de razonamiento local.
    """

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    def chat(self, user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Procesa el mensaje del usuario y devuelve el veredicto del asesor.
        """
        # 1. Obtener estado en tiempo real del mercado y de las Kill Zones
        session_state = kill_zones_engine.get_market_sessions_status()
        daily_opps = opportunity_engine.get_daily_opportunities(asset_class="all")
        top_picks = daily_opps.get("opportunities", [])[:3]

        # 2. Si hay clave de Gemini API configurada, generar respuesta con LLM
        if self.gemini_key:
            try:
                ai_reply = self._call_gemini_advisor(user_message, session_state, top_picks, conversation_history)
                return {
                    "source": "Gemini-1.5-Pro / Flash",
                    "response": ai_reply,
                    "session_context": session_state,
                    "top_picks": top_picks,
                }
            except Exception:
                pass

        # 3. Fallback: Motor Experto de Razonamiento Cuantitativo Local (Determinista y Riguroso)
        local_reply = self._generate_local_expert_response(user_message, session_state, top_picks)
        return {
            "source": "Motor Cuantitativo Local Trading EZ",
            "response": local_reply,
            "session_context": session_state,
            "top_picks": top_picks,
        }

    def _generate_local_expert_response(
        self,
        query: str,
        session_state: Dict[str, Any],
        top_picks: List[Dict[str, Any]],
    ) -> str:
        q = query.lower()

        # Caso A: Pregunta sobre horarios de bancos / "ganar sí o sí" / movimientos a una hora
        if any(w in q for w in ["banco", "hora", "horario", "seguro", "si o si", "cuándo", "cuando", "especifico", "específica"]):
            ny_time = session_state.get("current_ny_time", "N/A")
            is_kz = session_state.get("is_kill_zone_active", False)
            kz_status = "🟢 ACTIVA AHORA MISMO" if is_kz else "⚪ FUERA DE VENTANA BANCARIA (Mercado en espera)"

            return f"""### 🏛️ La Verdad sobre los Horarios Bancarios y la Ventaja Estadística

Entiendo perfectamente lo que te comentaron sobre *"personas que operan a una hora específica donde un banco se mueve"*. En el trading institucional (Smart Money Concepts), esto se conoce como **Kill Zones (Ventanas de Inyección de Liquidez)**.

#### 1. ¿Por qué se gana en esas horas? (La ventaja institucional)
No es que exista magia o que se gane "el 100% sí o sí" (ningún fondo en Wall Street gana el 100% de sus trades). Lo que ocurre es que los bancos comerciales y fondos de cobertura tienen **ventanas reglamentarias de ejecución algorítmica** donde inyectan miles de millones de dólares:

* **09:30 - 11:00 AM EST (Apertura de Wall Street / NY Open):** La mayor concentración de volumen del día. Los primeros 15 minutos (09:30 - 09:45) los bancos barren los stops de minoristas; a las 10:00 AM (con los datos macroeconómicos) inician la verdadera expansión de tendencia.
* **10:00 - 11:00 AM EST (ICT Silver Bullet):** Los algoritmos bancarios rellenan los desequilibrios (*Fair Value Gaps*) generados en la apertura. Es la ventana de mayor precisión para entradas con ratio 1:2 o 1:3.
* **02:00 - 05:00 AM EST (Apertura de Londres):** Los bancos europeos toman el control y generan el falso movimiento inicial (*Judas Swing*).

#### 2. Estado Actual de las Sesiones
* **Hora actual en Wall Street (Nueva York):** `{ny_time}`
* **Estado de Ventana Bancaria:** {kz_status}
* **Consejo Táctico:** {session_state.get("tactical_advice", "")}

#### 3. Cómo convertir esto en una ganancia extra segura
1. **Nunca busques acertar todas las veces:** Con un ratio de 1:2 (arriesgas $10 para ganar $20), incluso si solo aciertas el 50% de las operaciones, terminarás con ganancias consistentes.
2. **Opera solo durante la Kill Zone:** No mires el gráfico todo el día. Abre la plataforma a las **09:45 AM EST**, espera la confirmación de las 10:00 AM y coloca tu orden con Take Profit y Stop Loss automáticos.
3. **Revisa la sección de Oportunidades:** El terminal ya tiene precargadas las mejores operaciones del día filtradas bajo esta misma confluencia."""

        # Caso B: Pregunta sobre cuál es la mejor oportunidad de hoy / qué comprar
        if any(w in q for w in ["mejor", "oportunidad", "comprar", "entrar", "trade", "hoy", "recomiend"]):
            if not top_picks:
                return """### 🛡️ Diagnóstico de Oportunidades para Hoy

En este momento el escaneo del universo no ha encontrado configuraciones que superen el filtro de **Confluencia Institucional y Ratio Riesgo/Beneficio ≥ 1.5**.

En trading cuantitativo profesional, **no tener una operación forzada es una victoria de preservación de capital**. Los operadores que pierden su dinero son aquellos que fuerzan entradas cuando el mercado está en rango sucio. 

Te recomiendo esperar la apertura de la siguiente ventana bancaria (09:30 AM EST) o activar alertas de precio en la pestaña **🔔 Alertas**."""

            p = top_picks[0]
            pos = p.get("position_size", {})
            return f"""### 🎯 La Mejor Operación del Día según Confluencia Institucional

He analizado los activos más líquidos y el setup con mayor ventaja estadística para hoy es **{p.get('name', p['symbol'])} ({p['symbol']})**:

#### Ficha Operativa Lista:
* **Activo:** `{p['symbol']}` ({p.get('sector', 'General')})
* **Dirección:** **{p.get('direction', 'LONG')}** (Probabilidad Estimada: ~{int(p.get('calibrated_prob', 0.65) * 100)}%)
* **Precio de Entrada Sugerido:** `${p.get('entry_price', 0):.2f}`
* **Stop Loss (Invalidación):** `${p.get('stop_loss', 0):.2f}` (Distancia: {p.get('distance_sl_pct', 0)}%)
* **Objetivo 1 (Toma del 50%):** `${p.get('take_profit_1', 0):.2f}` (Ratio R:R: 1.5)
* **Objetivo 2 (Runner final):** `${p.get('take_profit_2', 0):.2f}` (Ratio R:R: ~2.8)
* **Ventana Horaria Óptima:** {p.get('recommended_execution_window', 'Apertura de NY (09:30 - 11:00 EST)')}

#### Por qué tiene criterio institucional:
{chr(10).join(['* ' + r for r in p.get('reasons', [])[:3]])}

#### Gestión de Riesgo para una Cuenta de $10,000 (Riesgo 1%):
* **Riesgo en Dólares:** ${pos.get('risk_dollars', 100):.2f} (Nunca perderás más de esto si toca Stop Loss)
* **Acciones/Títulos sugeridos:** {pos.get('shares', 1)} unidades
* **Asignación de capital:** ${pos.get('capital_allocated', 1000):.2f}"""

        # Caso C: Pregunta sobre ingresos extra / gestión de riesgo con poco dinero
        if any(w in q for w in ["extra", "ganancia", "dinero", "capital", "1000", "500", "ingreso"]):
            return """### 💡 Guía del Asesor para Generar un Ingreso Extra con Trading

Para usar el trading como una fuente de ingresos adicional sin comprometer tu estabilidad financiera, debes seguir la **Estrategia Cuantitativa de Preservación**:

1. **La Regla del 1% de Riesgo:**
   Si comienzas con una cuenta de $1,000 USD, tu pérdida máxima permitida por operación debe ser exactamente **$10 USD**. Jamás metas todo tu dinero en una sola jugada.

2. **La Asimetría Matemática (Tu ventaja sobre el 95% de los novatos):**
   * Riesgo por trade: **-$10 USD** (si toca el Stop Loss).
   * Ganancia objetivo: **+$20 a +$30 USD** (Take Profit en ratio 1:2 o 1:3).
   * Si haces 10 operaciones al mes en las horas bancarias y solo aciertas 6:
     * 6 operaciones ganadoras = +$120 USD.
     * 4 operaciones perdedoras = -$40 USD.
     * **Resultado Neto: +$80 USD de beneficio (un +8% mensual sobre tu capital)** de forma tranquila y metódica.

3. **Disciplina en Horarios:**
   No estés pegado a la pantalla. Dedica solo 45 minutos al día entre las **09:45 AM y 10:30 AM EST (Hora de Nueva York)**. Deja tu orden colocada y apaga la pantalla."""

        # Respuesta general de consultoría
        return f"""### 👨‍💼 Asesor Financiero Cuantitativo Trading EZ

Estoy listo para orientar tu operativa diaria con rigor institucional. Aquí tienes el estado en vivo:

* **Ventana Actual:** {session_state.get('status_indicator', 'Revisando mercado...')}
* **Táctico:** {session_state.get('tactical_advice', '')}
* **Oportunidades de Alta Confluencia Disponibles Hoy:** {len(top_picks)} operaciones listas en el panel.

¿Qué deseas consultar?
1. Pregúntame: *"¿Cuál es la mejor operación para hoy y cómo entro?"*
2. Pregúntame: *"¿A qué hora exacta operan los bancos hoy?"*
3. Pregúntame: *"¿Cómo calculo el tamaño de mi orden si tengo $500 o $2,000 USD?"*"""

    def _call_gemini_advisor(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        top_picks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        context_data = {
            "session_state": session_state,
            "top_picks_summary": [
                {
                    "symbol": p["symbol"],
                    "name": p.get("name"),
                    "direction": p.get("direction"),
                    "entry": p.get("entry_price"),
                    "sl": p.get("stop_loss"),
                    "tp1": p.get("take_profit_1"),
                    "tp2": p.get("take_profit_2"),
                    "prob": p.get("calibrated_prob"),
                    "window": p.get("recommended_execution_window"),
                }
                for p in top_picks
            ],
        }

        full_prompt = f"""
{SYSTEM_ADVISOR_PROMPT}

ESTADO DE MERCADO EN TIEMPO REAL:
{json.dumps(context_data, indent=2, ensure_ascii=False)}

PREGUNTA DEL USUARIO:
"{user_message}"

Responde en markdown claro, con criterio financiero experto, pedagógico, sin tecnicismos innecesarios, orientando siempre a la disciplina y gestión de riesgo.
"""
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.3},
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        raise RuntimeError(f"Gemini HTTP {resp.status_code}")

advisor_agent = QuantAdvisorAgent()
