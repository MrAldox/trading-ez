/**
 * Trading EZ - Vista de Paper Trading y Cartera Virtual
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
        <span class="metric-label">Equidad Total</span>
        <span id="paper-total-equity" class="metric-value">$10,000.00</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Efectivo Disponible</span>
        <span id="paper-cash" class="metric-value">$10,000.00</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">En Posiciones</span>
        <span id="paper-positions-val" class="metric-value">$0.00</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">P&L No Realizado</span>
        <span id="paper-unrealized-pnl" class="metric-value profit">$0.00 (+0.00%)</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Operaciones Cerradas</span>
        <span id="paper-closed-trades-count" class="metric-value">0</span>
      </div>
    </div>

    <!-- Barra de Acciones y Orden Manual -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
        <div>
          <h2 style="font-size: 16px; font-weight: 700;">💼 Cartera de Simulación (Paper Trading)</h2>
          <div style="font-size: 12px; color: var(--text-secondary);">Opera con dinero virtual en tiempo real y ejecuta directamente las fichas del ranking.</div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-open-order-modal" class="btn btn-primary">
            ➕ Nueva Orden
          </button>
          <button id="btn-reset-portfolio" class="btn btn-secondary" style="color: var(--color-loss);">
            🔄 Reiniciar ($10k)
          </button>
        </div>
      </div>
    </div>

    <!-- Tabla de Posiciones Abiertas -->
    <div class="glass-card">
      <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px;">Posiciones Abiertas</h3>
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
              <th>P&L ($)</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody id="paper-positions-tbody">
            <tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No hay posiciones abiertas actualmente.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById("btn-open-order-modal").addEventListener("click", () => {
    const modal = document.getElementById("order-modal");
    if (modal) modal.classList.add("open");
  });

  document.getElementById("btn-reset-portfolio").addEventListener("click", async () => {
    if (confirm("¿Estás seguro de reiniciar la cartera virtual a $10,000 USD?")) {
      try {
        await api.resetPaperPortfolio(10000.0);
        store.showToast("Cartera reiniciada a $10,000 USD", "success");
        await loadPaperPortfolio();
      } catch (e) {
        store.showToast(e.message, "error");
      }
    }
  });

  await loadPaperPortfolio();
}

export async function loadPaperPortfolio() {
  const tbody = document.getElementById("paper-positions-tbody");
  if (!tbody) return;

  try {
    const data = await api.getPaperPortfolio();
    const p = data.portfolio || {};

    const totalEquity = p.total_equity || p.cash || 10000;
    const cash = p.cash || 10000;
    const posVal = p.positions_value || 0;
    const pnl = p.unrealized_pnl || 0;
    const pnlPct = p.unrealized_pnl_pct || 0;

    // Actualizar métricas
    document.getElementById("paper-total-equity").textContent = store.formatPrice(totalEquity);
    document.getElementById("paper-cash").textContent = store.formatPrice(cash);
    document.getElementById("paper-positions-val").textContent = store.formatPrice(posVal);

    const pnlEl = document.getElementById("paper-unrealized-pnl");
    pnlEl.textContent = `${store.formatPrice(pnl)} (${store.formatPercent(pnlPct)})`;
    pnlEl.className = `metric-value ${pnl >= 0 ? "profit" : "loss"}`;

    document.getElementById("paper-closed-trades-count").textContent = (p.closed_trades || []).length;

    const positions = p.open_positions || [];
    if (!positions.length) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No hay posiciones abiertas actualmente.</td></tr>`;
      return;
    }

    tbody.innerHTML = positions
      .map((pos) => {
        const pnlRow = pos.unrealized_pnl || 0;
        const color = pnlRow >= 0 ? "var(--color-profit)" : "var(--color-loss)";
        return `
          <tr>
            <td><strong>${pos.symbol}</strong></td>
            <td><span class="status-badge validated" style="font-size: 11px;">${pos.direction}</span></td>
            <td>${pos.shares}</td>
            <td>${store.formatPrice(pos.entry_price)}</td>
            <td>${store.formatPrice(pos.current_price || pos.entry_price)}</td>
            <td style="color: var(--color-loss);">${store.formatPrice(pos.stop_loss)}</td>
            <td style="color: var(--color-profit);">${store.formatPrice(pos.take_profit_1)}</td>
            <td style="color: ${color}; font-weight: 700;">${store.formatPrice(pnlRow)}</td>
            <td>
              <button class="btn btn-secondary btn-close-pos" data-sym="${pos.symbol}" style="padding: 3px 8px; font-size: 11px;">
                Cerrar
              </button>
            </td>
          </tr>
        `;
      })
      .join("");

  } catch (err) {
    console.warn("Error cargando cartera de paper trading:", err);
  }
}
