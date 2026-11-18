/**
 * Trading EZ - Vista de Paper Trading y Cartera Virtual
 * Permite simular compras/ventas, gestionar riesgo, cerrar posiciones
 * en TP1, TP2, SL o Mercado, y ver el impacto directo en la cuenta.
 */
import { api } from "../api.js";
import { store } from "../store.js";

export async function initPaperView() {
  const container = document.getElementById("view-paper");
  if (!container) return;

  container.innerHTML = `
    <!-- Tarjetas de Resumen Financiero -->
    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-vault"></i> Equidad Total</span>
        <span id="paper-total-equity" class="metric-value">$10,000.00</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-wallet"></i> Efectivo Disponible</span>
        <span id="paper-cash" class="metric-value">$10,000.00</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-chart-pie"></i> En Posiciones</span>
        <span id="paper-positions-val" class="metric-value">$0.00</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-arrow-trend-up"></i> P&L No Realizado</span>
        <span id="paper-unrealized-pnl" class="metric-value profit">$0.00 (+0.00%)</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-trophy"></i> P&L Realizado Total</span>
        <span id="paper-realized-pnl" class="metric-value">$0.00</span>
      </div>
    </div>

    <!-- Barra de Acciones y Orden Manual -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
        <div>
          <h2 style="font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-wallet" style="color: var(--color-accent);"></i> Cartera de Simulación (Paper Trading)
          </h2>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
            Prueba estrategias sin arriesgar tu dinero real. Monitorea P&L exacto en USD y en múltiplos de riesgo (R).
          </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button id="btn-open-order-modal" class="btn btn-primary" style="font-size: 13px;">
            <i class="fa-solid fa-plus"></i> Nueva Orden
          </button>
          <button id="btn-goto-notifications" class="btn btn-secondary" style="font-size: 13px;">
            <i class="fa-solid fa-bell"></i> Ver Notificaciones & Cierres
          </button>
          <button id="btn-reset-portfolio" class="btn btn-secondary" style="color: var(--color-loss); font-size: 13px;">
            <i class="fa-solid fa-rotate-left"></i> Reiniciar ($10k)
          </button>
        </div>
      </div>
    </div>

    <!-- Tabla de Posiciones Abiertas -->
    <div class="glass-card" style="margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-briefcase"></i> Posiciones Abiertas en Mercado
        </h3>
        <span id="paper-open-counter" class="status-badge validated" style="font-size: 11px;">0 Abiertas</span>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Activo</th>
              <th>Dirección</th>
              <th>Unidades</th>
              <th>Entrada</th>
              <th>Actual</th>
              <th>Stop Loss</th>
              <th>TP 1</th>
              <th>P&L Flotante</th>
              <th style="min-width: 220px;">Acciones de Cierre</th>
            </tr>
          </thead>
          <tbody id="paper-positions-tbody">
            <tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">No hay posiciones abiertas actualmente.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tabla de Resumen Rápido de Cierres Recientes -->
    <div class="glass-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-circle-check" style="color: var(--color-profit);"></i> Últimas Operaciones Cerradas
        </h3>
        <button id="btn-view-all-closed" class="btn btn-secondary" style="font-size: 12px; padding: 4px 10px;">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> Ver Historial Completo
        </button>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Activo</th>
              <th>Dirección</th>
              <th>Acciones</th>
              <th>Entrada</th>
              <th>Salida</th>
              <th>Motivo Cierre</th>
              <th>P&L Realizado ($)</th>
              <th>Retorno R</th>
            </tr>
          </thead>
          <tbody id="paper-closed-quick-tbody">
            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">Cargando historial de cierres...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  // Botón abrir modal de orden
  document.getElementById("btn-open-order-modal").addEventListener("click", () => {
    const modal = document.getElementById("order-modal");
    if (modal) modal.classList.add("open");
  });

  // Botones de enlace a notificaciones
  const gotoNotif = () => {
    const notifBtn = document.querySelector('[data-tab="notifications"]');
    if (notifBtn) notifBtn.click();
  };
  document.getElementById("btn-goto-notifications").addEventListener("click", gotoNotif);
  document.getElementById("btn-view-all-closed").addEventListener("click", gotoNotif);

  // Botón reiniciar cartera
  document.getElementById("btn-reset-portfolio").addEventListener("click", async () => {
    if (confirm("¿Estás seguro de reiniciar la cartera virtual a $10,000 USD? Se eliminarán las posiciones simuladas actuales.")) {
      try {
        await api.resetPaperPortfolio(10000.0);
        store.showToast("Cartera de Paper Trading reiniciada a $10,000 USD", "success");
        await loadPaperPortfolio();
      } catch (e) {
        store.showToast(e.message, "error");
      }
    }
  });

  try {
    await loadPaperPortfolio();
  } catch (e) {
    console.warn("Paper initial load error:", e);
  }
}

export async function loadPaperPortfolio() {
  const tbody = document.getElementById("paper-positions-tbody");
  if (!tbody) return;

  try {
    const data = await api.getPaperPortfolio();
    const p = data.portfolio || {};

    const totalEquity = p.total_equity || p.cash || 10000;
    const cash = p.current_cash || p.cash || 10000;
    const realizedPnl = p.total_realized_pnl || 0.0;
    const unrealizedPnl = p.total_unrealized_pnl || p.unrealized_pnl || 0.0;
    const positions = p.open_positions || [];

    const posVal = positions.reduce((acc, pos) => acc + (pos.shares * (pos.current_price || pos.entry_price)), 0);

    // Actualizar métricas
    const totalEquityEl = document.getElementById("paper-total-equity");
    if (totalEquityEl) totalEquityEl.textContent = store.formatPrice(totalEquity);

    const cashEl = document.getElementById("paper-cash");
    if (cashEl) cashEl.textContent = store.formatPrice(cash);

    const posValEl = document.getElementById("paper-positions-val");
    if (posValEl) posValEl.textContent = store.formatPrice(posVal);

    const pnlEl = document.getElementById("paper-unrealized-pnl");
    if (pnlEl) {
      const sign = unrealizedPnl >= 0 ? "+" : "";
      pnlEl.textContent = `${sign}${store.formatPrice(unrealizedPnl)}`;
      pnlEl.className = `metric-value ${unrealizedPnl >= 0 ? "profit" : "loss"}`;
    }

    const realizedEl = document.getElementById("paper-realized-pnl");
    if (realizedEl) {
      const sign = realizedPnl >= 0 ? "+" : "";
      realizedEl.textContent = `${sign}${store.formatPrice(realizedPnl)}`;
      realizedEl.className = `metric-value ${realizedPnl >= 0 ? "profit" : "loss"}`;
    }

    const counterEl = document.getElementById("paper-open-counter");
    if (counterEl) counterEl.textContent = `${positions.length} Abiertas`;

    // Renderizar Posiciones Abiertas
    if (!positions.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; color: var(--text-muted); padding: 30px;">
            <i class="fa-solid fa-folder-open" style="font-size: 24px; opacity: 0.5; margin-bottom: 8px; display: block;"></i>
            No tienes posiciones abiertas en simulación.<br>
            Ve a <strong>🎯 Oportunidades</strong> para abrir tu primera operación con 1 clic.
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = positions
        .map((pos) => {
          const pnlRow = pos.unrealized_pnl || 0;
          const color = pnlRow >= 0 ? "var(--color-profit)" : "var(--color-loss)";
          const sign = pnlRow >= 0 ? "+" : "";
          const badgeClass = pos.direction === "LONG" ? "validated" : "uncalibrated";

          return `
            <tr data-pos-id="${pos.id}">
              <td><strong>${pos.symbol}</strong></td>
              <td><span class="status-badge ${badgeClass}" style="font-size: 11px;">${pos.direction}</span></td>
              <td style="font-family: var(--font-mono);">${pos.shares}</td>
              <td style="font-family: var(--font-mono);">${store.formatPrice(pos.entry_price)}</td>
              <td style="font-family: var(--font-mono);">${store.formatPrice(pos.current_price || pos.entry_price)}</td>
              <td style="color: var(--color-loss); font-family: var(--font-mono);">${store.formatPrice(pos.stop_loss)}</td>
              <td style="color: var(--color-profit); font-family: var(--font-mono);">${store.formatPrice(pos.take_profit_1)}</td>
              <td style="color: ${color}; font-weight: 700; font-family: var(--font-mono);">${sign}${store.formatPrice(pnlRow)}</td>
              <td>
                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                  <button class="btn btn-secondary btn-action-close" data-id="${pos.id}" data-sym="${pos.symbol}" data-reason="TP1" title="Cerrar simulando alcance de Take Profit 1" style="padding: 2px 7px; font-size: 11px; color: var(--color-profit);">
                    <i class="fa-solid fa-bullseye"></i> TP1
                  </button>
                  <button class="btn btn-secondary btn-action-close" data-id="${pos.id}" data-sym="${pos.symbol}" data-reason="TP2" title="Cerrar simulando alcance de Take Profit 2" style="padding: 2px 7px; font-size: 11px; color: #34d399;">
                    <i class="fa-solid fa-crosshairs"></i> TP2
                  </button>
                  <button class="btn btn-secondary btn-action-close" data-id="${pos.id}" data-sym="${pos.symbol}" data-reason="SL" title="Cerrar simulando ejecución de Stop Loss" style="padding: 2px 7px; font-size: 11px; color: var(--color-loss);">
                    <i class="fa-solid fa-shield-halved"></i> SL
                  </button>
                  <button class="btn btn-secondary btn-action-close" data-id="${pos.id}" data-sym="${pos.symbol}" data-reason="MANUAL" title="Cerrar a precio de mercado actual" style="padding: 2px 7px; font-size: 11px;">
                    <i class="fa-solid fa-xmark"></i> Mercado
                  </button>
                </div>
              </td>
            </tr>
          `;
        })
        .join("");

      // Conectar listeners de cierre
      tbody.querySelectorAll(".btn-action-close").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const posId = btn.getAttribute("data-id");
          const sym = btn.getAttribute("data-sym");
          const reason = btn.getAttribute("data-reason");

          btn.disabled = true;
          btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;

          try {
            const res = await api.closePaperPosition(posId, reason);
            store.showToast(res.message || `Posición ${sym} cerrada con éxito`, "success");
            await loadPaperPortfolio();
          } catch (err) {
            store.showToast(`Error al cerrar: ${err.message}`, "error");
            btn.disabled = false;
            btn.textContent = reason;
          }
        });
      });
    }

    // Cargar tabla de cierres recientes
    await loadQuickClosedTrades();

  } catch (err) {
    console.warn("Error cargando cartera de paper trading:", err);
  }
}

async function loadQuickClosedTrades() {
  const quickTbody = document.getElementById("paper-closed-quick-tbody");
  if (!quickTbody) return;

  try {
    const data = await api.getClosedTrades();
    const trades = data.trades || [];

    if (!trades.length) {
      quickTbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">
            Aún no has cerrado operaciones en simulación. Al cerrar una posición, su ganancia o pérdida quedará fijada aquí.
          </td>
        </tr>
      `;
      return;
    }

    quickTbody.innerHTML = trades.slice(0, 5)
      .map((t) => {
        const isWin = t.is_win;
        const color = isWin ? "var(--color-profit)" : "var(--color-loss)";
        const sign = t.realized_pnl >= 0 ? "+" : "";
        const rSign = t.realized_r >= 0 ? "+" : "";
        const badgeClass = isWin ? "badge-green" : "badge-red";

        return `
          <tr>
            <td><strong>${t.symbol}</strong></td>
            <td><span class="status-badge ${t.direction === 'LONG' ? 'validated' : 'uncalibrated'}" style="font-size: 10px;">${t.direction}</span></td>
            <td style="font-family: var(--font-mono);">${t.shares}</td>
            <td style="font-family: var(--font-mono); font-size: 12px;">$${Number(t.entry_price).toFixed(2)}</td>
            <td style="font-family: var(--font-mono); font-size: 12px;">$${Number(t.exit_price).toFixed(2)}</td>
            <td><span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.06);">${t.close_reason}</span></td>
            <td style="font-family: var(--font-mono); font-weight: 700; color: ${color};">${sign}$${Number(t.realized_pnl).toFixed(2)}</td>
            <td><span class="badge-pct ${badgeClass}" style="font-size: 11px;">${rSign}${Number(t.realized_r).toFixed(2)}R</span></td>
          </tr>
        `;
      })
      .join("");
  } catch (err) {
    console.warn("Error cargando resumen rápido de cerradas:", err);
  }
}
