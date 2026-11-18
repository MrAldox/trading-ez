/**
 * Trading EZ - Vista de Notificaciones & Resumen de Cierres de Operaciones
 * Presenta el feed de eventos, cálculo exacto de PnL en USD y en múltiplos de R,
 * tasa de acierto y desglose de operaciones ganadoras y perdedoras.
 */
import { api } from "../api.js";
import { store } from "../store.js";

export async function initNotificationsView() {
  const container = document.getElementById("view-notifications");
  if (!container) return;

  container.innerHTML = `
    <!-- Cabecera de Notificaciones -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
        <div>
          <h2 style="font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-bell" style="color: var(--color-accent);"></i>
            Notificaciones de Trading & Resumen de Cierres
          </h2>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
            Registro en vivo de operaciones cerradas: cálculo exacto de ganancia/pérdida en USD, múltiplos R y control de disciplina.
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-refresh-notifications" class="btn btn-primary" style="font-size: 13px; padding: 6px 14px;">
            <i class="fa-solid fa-arrows-rotate"></i> Actualizar Notificaciones
          </button>
        </div>
      </div>
    </div>

    <!-- Banner de Métricas y Rendimiento de Cierres -->
    <div class="metrics-grid" style="margin-bottom: 20px;">
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-bullseye"></i> Tasa de Acierto (Win Rate)</span>
        <span id="notif-win-rate" class="metric-value">0.0%</span>
        <span id="notif-win-ratio-text" style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">0 victorias / 0 pérdidas</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-sack-dollar"></i> Ganancia Neta Realizada</span>
        <span id="notif-total-pnl" class="metric-value">$0.00</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">En cuenta de simulación</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-chart-line"></i> Múltiplo R Acumulado</span>
        <span id="notif-total-r" class="metric-value">+0.00R</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Riesgo normalizado (R)</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-scale-balanced"></i> Factor de Beneficio</span>
        <span id="notif-profit-factor" class="metric-value">0.00</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Ganancias vs Pérdidas</span>
      </div>
      <div class="metric-card">
        <span class="metric-label"><i class="fa-solid fa-clock-rotate-left"></i> Total Cerradas</span>
        <span id="notif-total-closed" class="metric-value">0</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Historial registrado</span>
      </div>
    </div>

    <!-- Disposición en 2 Columnas: Feed de Alertas / Tabla Histórica -->
    <div style="display: grid; grid-template-columns: 1fr 1.3fr; gap: 20px;">
      <!-- Columna 1: Feed de Notificaciones de Cierre -->
      <div class="glass-card" style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
          <h3 style="font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-bolt" style="color: var(--color-accent);"></i> Feed de Cierres Recientes
          </h3>
          <span class="status-badge" style="font-size: 11px;">En Tiempo Real</span>
        </div>

        <div id="notif-feed-container" style="display: flex; flex-direction: column; gap: 12px; max-height: 560px; overflow-y: auto; padding-right: 4px;">
          <div class="empty-state" style="padding: 30px 16px;">
            <div class="empty-state-icon"><i class="fa-regular fa-bell-slash"></i></div>
            <div class="empty-state-title">Sin notificaciones de cierre aún</div>
            <div class="empty-state-desc">
              Cuando una operación en Paper Trading alcance su Take Profit 1, Take Profit 2 o Stop Loss, aquí verás la notificación instantánea con el resultado en dólares y en R.
            </div>
          </div>
        </div>
      </div>

      <!-- Columna 2: Tabla de Operaciones Cerradas -->
      <div class="glass-card" style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
          <h3 style="font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-table-list" style="color: #a78bfa;"></i> Registro Detallado de Operaciones
          </h3>
          <span id="notif-table-counter" class="status-badge" style="font-size: 11px;">0 operaciones</span>
        </div>

        <div class="table-responsive" style="max-height: 560px; overflow-y: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Activo</th>
                <th>Tipo</th>
                <th>Entrada</th>
                <th>Salida</th>
                <th>Motivo Cierre</th>
                <th>Resultado ($)</th>
                <th>Retorno R</th>
              </tr>
            </thead>
            <tbody id="notif-trades-tbody">
              <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">
                  No hay operaciones cerradas todavía.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Listener para botón de actualización
  const btnRefresh = document.getElementById("btn-refresh-notifications");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => loadNotificationsData());
  }

  // Carga inicial
  await loadNotificationsData();
}

export async function loadNotificationsData() {
  try {
    const data = await api.getClosedTrades();
    const trades = data.trades || [];
    const notifs = data.notifications || [];

    // 1. Actualizar KPIs de rendimiento
    const totalClosed = data.total_closed || 0;
    const wins = data.wins || 0;
    const losses = data.losses || 0;
    const winRate = data.win_rate || 0.0;
    const totalPnl = data.total_realized_pnl || 0.0;
    const totalR = data.total_realized_r || 0.0;
    const profitFactor = data.profit_factor || 0.0;

    const winRateEl = document.getElementById("notif-win-rate");
    if (winRateEl) {
      winRateEl.textContent = `${winRate.toFixed(1)}%`;
      winRateEl.className = `metric-value ${winRate >= 50 ? "profit" : (totalClosed > 0 ? "loss" : "")}`;
    }

    const ratioTextEl = document.getElementById("notif-win-ratio-text");
    if (ratioTextEl) {
      ratioTextEl.textContent = `${wins} ganadas / ${losses} perdidas`;
    }

    const totalPnlEl = document.getElementById("notif-total-pnl");
    if (totalPnlEl) {
      const pnlSign = totalPnl >= 0 ? "+" : "";
      totalPnlEl.textContent = `${pnlSign}${store.formatPrice(totalPnl)}`;
      totalPnlEl.className = `metric-value ${totalPnl >= 0 ? "profit" : "loss"}`;
    }

    const totalREl = document.getElementById("notif-total-r");
    if (totalREl) {
      const rSign = totalR >= 0 ? "+" : "";
      totalREl.textContent = `${rSign}${totalR.toFixed(2)}R`;
      totalREl.className = `metric-value ${totalR >= 0 ? "profit" : "loss"}`;
    }

    const pfEl = document.getElementById("notif-profit-factor");
    if (pfEl) {
      pfEl.textContent = profitFactor >= 90 ? "∞ (Sin pérdidas)" : profitFactor.toFixed(2);
    }

    const totalClosedEl = document.getElementById("notif-total-closed");
    if (totalClosedEl) {
      totalClosedEl.textContent = totalClosed;
    }

    const tableCounterEl = document.getElementById("notif-table-counter");
    if (tableCounterEl) {
      tableCounterEl.textContent = `${totalClosed} operaciones`;
    }

    // Actualizar badge de notificaciones en el header si existe
    const headerBadge = document.getElementById("notif-badge-count");
    if (headerBadge) {
      if (notifs.length > 0) {
        headerBadge.style.display = "inline-flex";
        headerBadge.textContent = notifs.length;
      } else {
        headerBadge.style.display = "none";
      }
    }

    // 2. Renderizar Feed de Notificaciones
    const feedContainer = document.getElementById("notif-feed-container");
    if (feedContainer) {
      if (!notifs.length) {
        feedContainer.innerHTML = `
          <div class="empty-state" style="padding: 30px 16px;">
            <div class="empty-state-icon"><i class="fa-regular fa-bell-slash"></i></div>
            <div class="empty-state-title">Sin notificaciones de cierre aún</div>
            <div class="empty-state-desc">
              Abre una operación en Paper Trading y ciérrala en <strong>TP1, TP2 o SL</strong> para ver la notificación automática y su desglose.
            </div>
          </div>
        `;
      } else {
        feedContainer.innerHTML = notifs
          .map((n) => {
            const isWin = n.type === "WIN";
            const borderCol = isWin ? "var(--color-profit)" : "var(--color-loss)";
            const bgGlow = isWin ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)";
            const icon = isWin ? "fa-circle-check" : "fa-circle-xmark";
            const iconCol = isWin ? "var(--color-profit)" : "var(--color-loss)";
            const sign = n.pnl_usd >= 0 ? "+" : "";
            const rSign = n.pnl_r >= 0 ? "+" : "";

            const timeStr = n.timestamp ? new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Hoy";

            return `
              <div style="background: ${bgGlow}; border: 1px solid ${borderCol}; border-radius: var(--radius-md); padding: 12px 14px; display: flex; gap: 12px; align-items: flex-start; transition: transform 0.15s ease;">
                <div style="font-size: 20px; color: ${iconCol}; margin-top: 2px;">
                  <i class="fa-solid ${icon}"></i>
                </div>
                <div style="flex: 1;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <strong style="font-size: 14px; color: var(--text-primary);">${n.title}</strong>
                    <span style="font-size: 11px; color: var(--text-muted);"><i class="fa-regular fa-clock"></i> ${timeStr}</span>
                  </div>
                  <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">
                    ${n.subtitle}
                  </div>
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-family: var(--font-mono); font-weight: 700; font-size: 13px; color: ${iconCol};">
                      ${sign}$${Number(n.pnl_usd).toFixed(2)} USD
                    </span>
                    <span class="badge-pct ${isWin ? 'badge-green' : 'badge-red'}" style="font-size: 11px;">
                      ${rSign}${Number(n.pnl_r).toFixed(2)}R
                    </span>
                  </div>
                </div>
              </div>
            `;
          })
          .join("");
      }
    }

    // 3. Renderizar Tabla Histórica
    const tbody = document.getElementById("notif-trades-tbody");
    if (tbody) {
      if (!trades.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">
              No hay operaciones cerradas todavía. ¡Ejecuta y cierra órdenes en Paper Trading para probar!
            </td>
          </tr>
        `;
      } else {
        tbody.innerHTML = trades
          .map((t) => {
            const isWin = t.is_win;
            const pnlColor = isWin ? "var(--color-profit)" : "var(--color-loss)";
            const sign = t.realized_pnl >= 0 ? "+" : "";
            const rSign = t.realized_r >= 0 ? "+" : "";
            const badgeClass = isWin ? "badge-green" : "badge-red";

            return `
              <tr>
                <td>
                  <strong>${t.symbol}</strong>
                  <div style="font-size: 11px; color: var(--text-muted);">${t.shares} acciones</div>
                </td>
                <td>
                  <span class="status-badge ${t.direction === 'LONG' ? 'validated' : 'uncalibrated'}" style="font-size: 10px;">
                    ${t.direction}
                  </span>
                </td>
                <td style="font-family: var(--font-mono); font-size: 12px;">$${Number(t.entry_price).toFixed(2)}</td>
                <td style="font-family: var(--font-mono); font-size: 12px;">$${Number(t.exit_price).toFixed(2)}</td>
                <td>
                  <span style="font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.06);">
                    ${t.close_reason}
                  </span>
                </td>
                <td style="font-family: var(--font-mono); font-weight: 700; color: ${pnlColor};">
                  ${sign}$${Number(t.realized_pnl).toFixed(2)}
                </td>
                <td>
                  <span class="badge-pct ${badgeClass}" style="font-size: 11px;">
                    ${rSign}${Number(t.realized_r).toFixed(2)}R
                  </span>
                </td>
              </tr>
            `;
          })
          .join("");
      }
    }
  } catch (err) {
    console.error("Error al cargar datos de notificaciones:", err);
  }
}
