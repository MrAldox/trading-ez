/**
 * Trading EZ - Vista de Oportunidades y Ficha de Operación
 */
import { api } from "../api.js";
import { store } from "../store.js";
import { FinancialCanvasChart } from "../chart/engine.js";

let modalChart = null;

export async function initOpportunitiesView() {
  const container = document.getElementById("view-opportunities");
  if (!container) return;

  if (!document.getElementById("opp-filter-class")) {
    container.innerHTML = `
      <!-- Barra Superior de Parámetros y Filtros Cuantitativos -->
      <div class="filters-bar">
        <div class="filter-group">
          <label>Clase:</label>
          <select id="opp-filter-class" style="width: auto;">
            <option value="all">Todos los Activos</option>
            <option value="stocks">Acciones (S&P 500 / Nasdaq)</option>
            <option value="crypto">Cripto 24/7</option>
            <option value="etf">ETFs Líquidos</option>
            <option value="commodities">Materias Primas / FX</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Horizonte:</label>
          <select id="opp-filter-horizon" style="width: auto;">
            <option value="medium" selected>Medio (10-20 velas)</option>
            <option value="short">Corto (3-5 velas)</option>
            <option value="long">Largo (30-60 velas)</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Capital USD:</label>
          <input type="number" id="opp-capital" value="10000" min="1000" step="1000" style="width: 110px;" />
        </div>

        <div class="filter-group">
          <label>Riesgo/Trade:</label>
          <select id="opp-risk" style="width: auto;">
            <option value="0.5">0.5% (Conservador)</option>
            <option value="1.0" selected>1.0% (Equilibrado)</option>
            <option value="2.0">2.0% (Agresivo)</option>
          </select>
        </div>

        <button id="btn-refresh-opps" class="btn btn-primary" style="margin-left: auto;">
          <span>🔄</span> Escanear Mercado
        </button>
      </div>

      <!-- Banner de Auditoría e Historial del Modelo -->
      <div id="opp-history-banner" class="glass-card" style="margin-bottom: 16px; display: none;"></div>

      <!-- Contenedor Principal de Tarjetas -->
      <div id="opp-cards-container">
        <div class="empty-state">
          <div class="empty-state-icon">⏳</div>
          <div class="empty-state-title">Cargando oportunidades del mercado...</div>
        </div>
      </div>
    `;
  }

  // Listeners de controles (evitar duplicados con flag dataset)
  const btnRefresh = document.getElementById("btn-refresh-opps");
  if (btnRefresh && !btnRefresh.dataset.bound) {
    btnRefresh.dataset.bound = "true";
    btnRefresh.addEventListener("click", () => loadOpportunities(true));
    document.getElementById("opp-filter-class")?.addEventListener("change", () => loadOpportunities());
    document.getElementById("opp-filter-horizon")?.addEventListener("change", () => loadOpportunities());
    document.getElementById("opp-capital")?.addEventListener("change", () => loadOpportunities());
    document.getElementById("opp-risk")?.addEventListener("change", () => loadOpportunities());
  }

  await loadOpportunities();
}

export async function loadOpportunities(forceRefresh = false) {
  const container = document.getElementById("opp-cards-container");
  const banner = document.getElementById("opp-history-banner");
  if (!container) return;

  const assetClass = document.getElementById("opp-filter-class")?.value || "all";
  const horizon = document.getElementById("opp-filter-horizon")?.value || "medium";
  const capital = parseFloat(document.getElementById("opp-capital")?.value || "10000");
  const riskPct = parseFloat(document.getElementById("opp-risk")?.value || "1.0");

  try {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <div class="empty-state-title">Analizando universo con modelos calibrados...</div>
        <div class="empty-state-desc">Filtrando liquidez, regímenes y expectativas netas de comisiones.</div>
      </div>
    `;

    const data = await api.getOpportunities({
      asset_class: assetClass,
      horizon: horizon,
      capital: capital,
      risk_pct: riskPct,
      force_refresh: forceRefresh,
    });

    // Actualizar badge de estado en el header de forma segura
    const statusVal = data.status || data.system_status?.model_status || "SIN CALIBRAR";
    const statusBadge = document.getElementById("global-system-status");
    if (statusBadge) {
      statusBadge.className = `status-badge ${String(statusVal).toLowerCase().replace(/[\s-]+/g, "_")}`;
      statusBadge.innerHTML = `<span class="indicator-dot"></span> ${statusVal}`;
    }

    // Banner de métricas históricas de honestidad
    if (data.system_metrics && banner) {
      banner.style.display = "block";
      const m = data.system_metrics;
      banner.innerHTML = `
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
          <div>
            <span style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Transparencia Cuantitativa</span>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">
              Historial real del ranking: <strong>${m.total_closed_signals || 0}</strong> señales ejecutadas | 
              Win Rate: <strong style="color: var(--color-profit);">${store.formatPercent(m.realized_win_rate_pct || 0, false)}</strong> | 
              Expectancy Media: <strong style="color: var(--color-profit);">${store.formatR(m.realized_avg_r || 0)}</strong> | 
              Max DD: <strong style="color: var(--color-loss);">${store.formatPercent(m.max_drawdown_pct || 0)}</strong>
            </div>
          </div>
          <div style="font-size: 12px; color: var(--text-muted);">
            Regla de oro: <em>Menos fallos = Selectividad Extrema</em>
          </div>
        </div>
      `;
    }

    const opps = data.opportunities || [];
    store.setState({ opportunities: opps, systemStatus: data.status });

    if (data.status === "BLOQUEADO") {
      container.innerHTML = `
        <div class="empty-state" style="border-color: var(--color-loss); background: rgba(239, 68, 68, 0.05);">
          <div class="empty-state-icon">🛑</div>
          <div class="empty-state-title" style="color: var(--color-loss);">SISTEMA BLOQUEADO POR CIRCUIT BREAKER</div>
          <div class="empty-state-desc">
            ${data.message || "Se ha activado una salvaguarda institucional de riesgo por datos obsoletos o racha de pérdidas consecutivas."}
          </div>
        </div>
      `;
      return;
    }

    if (opps.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🛡️</div>
          <div class="empty-state-title">Hoy no hay oportunidades con ventaja estadística suficiente</div>
          <div class="empty-state-desc">
            El sistema opera bajo selectividad extrema (probabilidad calibrada &ge; 60%, expectativa positiva neta de comisiones y R:B &ge; 1.5).
            Preservar capital es la primera regla. No forzar operaciones es un resultado cuantitativamente válido y esperado en muchos días.
          </div>
        </div>
      `;
      return;
    }

    // Renderizar grilla de tarjetas
    let html = `<div class="opportunities-grid">`;
    opps.forEach((opp, idx) => {
      const probPct = Math.round((opp.calibrated_prob ?? opp.calibrated_probability ?? 0.65) * 100);
      const probClass = probPct >= 65 ? "prob-high" : probPct >= 60 ? "prob-medium" : "prob-low";
      const assetClassTxt = (opp.asset_class || "stocks").toUpperCase();
      const assetName = opp.name || opp.asset_name || opp.symbol;
      const windowTxt = opp.recommended_execution_window || (opp.horizon ? opp.horizon.toUpperCase() : "NY OPEN");
      const dollarAlloc = opp.position_size?.capital_allocated || opp.position_size?.dollar_allocation || 0;
      const strategyTag = opp.strategy_type ? "SMC & KILL ZONES" : "ML PURGADO";

      html += `
        <div class="glass-card opportunity-card" data-index="${idx}">
          <div class="opp-card-header">
            <div class="opp-asset-info">
              <h3>
                ${opp.symbol}
                <span class="status-badge" style="background: rgba(255,255,255,0.06); font-size: 10px;">${assetClassTxt}</span>
                <span class="status-badge validated" style="font-size: 9px; padding: 2px 6px;">${strategyTag}</span>
              </h3>
              <span>${assetName}</span>
              <div style="font-size: 11px; color: var(--color-brand); margin-top: 2px; font-weight: 600;">
                ⏰ ${windowTxt}
              </div>
            </div>
            <div class="prob-badge ${probClass}" title="Probabilidad calculada fuera de muestra y calibrada">
              <span>🎯</span> ${probPct}%
            </div>
          </div>

          <div class="opp-levels-grid">
            <div class="opp-level-item">
              <label>Entrada (t+1)</label>
              <span class="level-entry">${store.formatPrice(opp.entry_price)}</span>
            </div>
            <div class="opp-level-item">
              <label>Stop Loss</label>
              <span class="level-stop">${store.formatPrice(opp.stop_loss)}</span>
            </div>
            <div class="opp-level-item">
              <label>Take Profit 1</label>
              <span class="level-tp">${store.formatPrice(opp.take_profit_1)}</span>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-secondary); margin: 6px 0;">
            <div>Riesgo/Beneficio: <strong style="color: var(--text-primary);">${opp.risk_reward_ratio || 1.5}R</strong></div>
            <div>Posición: <strong style="color: var(--color-brand);">${opp.position_size?.shares || 1} uds (${store.formatPrice(dollarAlloc)})</strong></div>
          </div>

          <div style="margin-top: 8px; display: grid; grid-template-columns: 1.3fr 1fr auto; gap: 8px;">
            <button class="btn btn-primary btn-quick-paper" data-index="${idx}" title="Abrir y ejecutar esta operación directamente en Paper Trading">
              <i class="fa-solid fa-wallet"></i> Operar en Paper
            </button>
            <button class="btn btn-secondary btn-view-ticket" data-index="${idx}" title="Ver ficha técnica completa y gráfico">
              <i class="fa-solid fa-chart-line"></i> Ficha &amp; Gráfico
            </button>
            <button class="btn btn-secondary btn-quick-copy" data-index="${idx}" title="Copiar texto de la orden">
              <i class="fa-regular fa-copy"></i>
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;
    container.innerHTML = html;

    // Vincular botón directo Operar en Paper
    container.querySelectorAll(".btn-quick-paper").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute("data-index"), 10);
        executeOpportunityInPaper(opps[idx], btn);
      });
    });

    // Vincular clicks en las tarjetas
    container.querySelectorAll(".btn-view-ticket").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute("data-index"), 10);
        openTicketModal(opps[idx]);
      });
    });

    container.querySelectorAll(".opportunity-card").forEach((card) => {
      card.addEventListener("click", () => {
        const idx = parseInt(card.getAttribute("data-index"), 10);
        openTicketModal(opps[idx]);
      });
    });

    container.querySelectorAll(".btn-quick-copy").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute("data-index"), 10);
        copyTicketText(opps[idx]);
      });
    });

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="border-color: var(--color-loss);">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Error al consultar oportunidades</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>
    `;
  }
}

export async function openTicketModal(ticket) {
  if (!ticket) return;
  const modal = document.getElementById("ticket-modal");
  if (!modal) return;

  store.setState({ selectedOpportunity: ticket });

  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  };

  const setValue = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  };

  const probVal = Math.round((ticket.calibrated_prob ?? ticket.calibrated_probability ?? 0.65) * 100);
  const assetName = ticket.name || ticket.asset_name || ticket.symbol;
  const pos = ticket.position_size || {};
  const dollarAlloc = pos.capital_allocated ?? pos.dollar_allocation ?? 0;
  const dollarRisk = pos.risk_dollars ?? pos.dollar_risk ?? 0;
  const distSl = ticket.risk_distance_pct || ticket.distance_sl_pct || 0;
  const invalidationTxt = ticket.invalidation_criteria || ticket.invalidation_condition || `Cierre de vela por debajo de Stop Loss (${store.formatPrice(ticket.stop_loss)}) antes de alcanzar TP1.`;

  // Título e identificadores
  setTxt("modal-ticket-title", `${ticket.symbol} · ${assetName}`);
  setTxt("modal-ticket-badge", `${ticket.direction || "LONG"} (${probVal}% Prob. Calibrada)`);

  // Resumen de niveles y tamaño
  setTxt("modal-entry-price", store.formatPrice(ticket.entry_price));
  setTxt("modal-stop-loss", `${store.formatPrice(ticket.stop_loss)} (-${distSl}%)`);
  setTxt("modal-tp1", `${store.formatPrice(ticket.take_profit_1)} (+1.5R)`);
  setTxt("modal-tp2", `${store.formatPrice(ticket.take_profit_2)} (+3.0R)`);

  setTxt("modal-position-shares", `${pos.shares || 1} uds`);
  setTxt("modal-position-capital", store.formatPrice(dollarAlloc));
  setTxt("modal-position-risk", store.formatPrice(dollarRisk));

  // Listas de razones, contradicciones y advertencias
  const reasonsEl = document.getElementById("modal-reasons-list");
  if (reasonsEl) {
    reasonsEl.innerHTML = (ticket.reasons || []).map((r) => `<li>✅ ${r}</li>`).join("") || "<li>Estructura técnica y confluencia institucional favorables</li>";
  }

  const contraEl = document.getElementById("modal-contradictions-list");
  if (contraEl) {
    contraEl.innerHTML = (ticket.contradictions || []).map((c) => `<li>⚠️ ${c}</li>`).join("") || "<li>Ninguna contradicción de peso detectada</li>";
  }

  const warnEl = document.getElementById("modal-warnings-list");
  if (warnEl) {
    warnEl.innerHTML = (ticket.warnings || []).map((w) => `<li>🛑 ${w}</li>`).join("") || "<li>Volatilidad habitual de mercado</li>";
  }

  setTxt("modal-invalidation-text", invalidationTxt);

  // Formatos de copia
  const copyText = `--- ORDEN DE TRADING EZ ---
Activo: ${ticket.symbol} (${assetName})
Dirección: ${ticket.direction || "LONG"}
Entrada Apertura: ${store.formatPrice(ticket.entry_price)}
Stop Loss: ${store.formatPrice(ticket.stop_loss)}
Take Profit 1: ${store.formatPrice(ticket.take_profit_1)}
Take Profit 2: ${store.formatPrice(ticket.take_profit_2)}
Tamaño sugerido: ${pos.shares || 1} unidades (~${store.formatPrice(dollarAlloc)})
Riesgo monetario: ${store.formatPrice(dollarRisk)}
Probabilidad Calibrada: ${probVal}%
Invalidación: ${invalidationTxt}`;

  setValue("modal-copy-text", copyText);

  const bracketJson = {
    symbol: ticket.symbol,
    action: (ticket.direction || "LONG") === "LONG" ? "BUY" : "SELL",
    quantity: pos.shares || 1,
    orderType: "STOP_LIMIT",
    limitPrice: ticket.entry_price,
    stopLoss: { price: ticket.stop_loss },
    takeProfit: { price: ticket.take_profit_1 },
  };
  setValue("modal-copy-json", JSON.stringify(bracketJson, null, 2));

  // Explicación de IA inicial (reset)
  const aiBox = document.getElementById("modal-ai-explanation-content");
  if (aiBox) {
    aiBox.innerHTML = `
      <p>Haz clic en el botón <strong>"Generar Análisis IA"</strong> para obtener una explicación detallada en lenguaje natural validada contra alucinaciones.</p>
    `;
  }

  // Vincular botón Operar Directo en Paper Trading dentro del modal
  const btnModalPaper = document.getElementById("btn-modal-execute-paper") || document.getElementById("btn-modal-paper-trade");
  if (btnModalPaper) {
    btnModalPaper.onclick = (e) => {
      e.preventDefault();
      executeOpportunityInPaper(ticket, btnModalPaper);
    };
  }

  // Abrir modal inmediatamente
  modal.classList.add("open");

  // Inicializar o actualizar gráfico Canvas
  setTimeout(async () => {
    try {
      const histData = await api.getMarketHistory(ticket.symbol, "1d", 120);
      const canvas = document.getElementById("modal-chart-canvas");
      if (canvas && histData?.candles?.length) {
        modalChart = new FinancialCanvasChart("modal-chart-canvas", {
          showVolume: true,
          showIndicators: true,
          showTradeLevels: true,
          tradeLevels: {
            entry: ticket.entry_price,
            stopLoss: ticket.stop_loss,
            takeProfit1: ticket.take_profit_1,
            takeProfit2: ticket.take_profit_2,
          },
        });
        modalChart.setData(histData.candles);
      }
    } catch (e) {
      console.warn("No se pudo cargar el gráfico en el modal:", e);
    }
  }, 100);
}

export async function executeOpportunityInPaper(ticket, btn = null) {
  if (!ticket) return;

  const originalContent = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Ejecutando...`;
  }

  try {
    const pos = ticket.position_size || {};
    const shares = Math.max(1, pos.shares || ticket.suggested_shares || 1);
    const stopLoss = ticket.stop_loss || 0.0;
    const tp1 = ticket.take_profit_1 || 0.0;
    const tp2 = ticket.take_profit_2 || 0.0;

    const res = await api.executePaperOrder({
      symbol: ticket.symbol,
      direction: ticket.direction || "LONG",
      shares: shares,
      stop_loss: stopLoss,
      take_profit_1: tp1,
      take_profit_2: tp2,
    });

    store.showToast(
      res.message || `Orden ejecutada: ${shares} ${ticket.symbol} en Paper Trading`,
      "success"
    );

    // Cerrar modal de ficha si estaba abierto
    const modal = document.getElementById("ticket-modal");
    if (modal) modal.classList.remove("open");

    // Cambiar a la pestaña de Paper Trading
    const paperBtn = document.querySelector('[data-tab="paper"]');
    if (paperBtn) {
      paperBtn.click();
    }
  } catch (err) {
    console.error("Error al ejecutar orden en paper:", err);
    store.showToast(`Error al ejecutar en Paper Trading: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalContent;
    }
  }
}

export function copyTicketText(ticket) {
  if (!ticket) return;
  const pos = ticket.position_size || {};
  const probVal = Math.round((ticket.calibrated_prob ?? ticket.calibrated_probability ?? 0.65) * 100);
  const assetName = ticket.name || ticket.asset_name || ticket.symbol;
  const dollarAlloc = pos.capital_allocated ?? pos.dollar_allocation ?? 0;
  const dollarRisk = pos.risk_dollars ?? pos.dollar_risk ?? 0;

  const copyText = `--- ORDEN DE TRADING EZ ---
Activo: ${ticket.symbol} (${assetName})
Dirección: ${ticket.direction || "LONG"}
Entrada Apertura: ${store.formatPrice(ticket.entry_price)}
Stop Loss: ${store.formatPrice(ticket.stop_loss)}
Take Profit 1: ${store.formatPrice(ticket.take_profit_1)}
Take Profit 2: ${store.formatPrice(ticket.take_profit_2)}
Tamaño sugerido: ${pos.shares || 1} unidades (~${store.formatPrice(dollarAlloc)})
Riesgo monetario: ${store.formatPrice(dollarRisk)}
Probabilidad Calibrada: ${probVal}%`;

  navigator.clipboard.writeText(copyText).then(() => {
    store.showToast(`Orden para ${ticket.symbol} copiada al portapapeles`, "success");
  }).catch(() => {
    store.showToast("No se pudo acceder al portapapeles", "warning");
  });
}
