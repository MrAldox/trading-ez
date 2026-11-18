/**
 * Trading EZ - Vista de Alertas de Precios y Notificaciones
 */
import { api } from "../api.js";
import { store } from "../store.js";

export async function initAlertsView() {
  const container = document.getElementById("view-alerts");
  if (!container) return;

  container.innerHTML = `
    <!-- Formulario de Creación de Alertas -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">🔔 Crear Nueva Alerta de Precio</h2>
      <form id="alert-form" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end;">
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Símbolo:</label>
          <input type="text" id="alert-symbol" placeholder="ej. BTC-USD" required style="width: 120px;" />
        </div>
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Condición:</label>
          <select id="alert-condition" style="width: 130px;">
            <option value="ABOVE">Cruza por Encima (&gt;)</option>
            <option value="BELOW">Cruza por Debajo (&lt;)</option>
          </select>
        </div>
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Precio Objetivo ($):</label>
          <input type="number" id="alert-price" placeholder="ej. 95000" step="0.01" required style="width: 140px;" />
        </div>
        <button type="submit" class="btn btn-primary" style="height: 42px;">
          ➕ Establecer Alerta
        </button>
      </form>
    </div>

    <!-- Lista de Alertas Activas -->
    <div class="glass-card">
      <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px;">Alertas Configuradas</h3>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Activo</th>
              <th>Regla de Activación</th>
              <th>Precio Objetivo</th>
              <th>Estado</th>
              <th>Fecha Creación</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody id="alerts-list-tbody">
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Cargando alertas...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById("alert-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const sym = document.getElementById("alert-symbol").value.trim().toUpperCase();
    const cond = document.getElementById("alert-condition").value;
    const price = parseFloat(document.getElementById("alert-price").value);

    try {
      await api.createAlert({
        symbol: sym,
        condition: cond,
        target_value: price,
      });

      store.showToast(`Alerta para ${sym} guardada`, "success");
      document.getElementById("alert-form").reset();
      await loadAlerts();
    } catch (err) {
      store.showToast(err.message, "error");
    }
  });

  await loadAlerts();
}

export async function loadAlerts() {
  const tbody = document.getElementById("alerts-list-tbody");
  if (!tbody) return;

  try {
    const data = await api.getAlerts();
    const alerts = data.alerts || [];

    if (!alerts.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No tienes alertas de precios activas actualmente.</td></tr>`;
      return;
    }

    tbody.innerHTML = alerts
      .map((a) => {
        const condTxt = a.condition === "ABOVE" ? "Mayor o igual que (≥)" : "Menor o igual que (≤)";
        const statusTxt = a.is_triggered ? "Activada" : "Monitoreando";
        const statusCls = a.is_triggered ? "uncalibrated" : "validated";

        return `
          <tr>
            <td><strong>${a.symbol}</strong></td>
            <td>${condTxt}</td>
            <td style="font-weight: 700;">${store.formatPrice(a.target_value)}</td>
            <td><span class="status-badge ${statusCls}">${statusTxt}</span></td>
            <td>${store.formatDate(a.created_at)}</td>
            <td>
              <button class="btn btn-secondary btn-delete-alert" data-id="${a.id}" style="padding: 3px 8px; font-size: 11px; color: var(--color-loss);">
                Eliminar
              </button>
            </td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll(".btn-delete-alert").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        try {
          await api.deleteAlert(id);
          store.showToast("Alerta eliminada", "info");
          await loadAlerts();
        } catch (e) {
          store.showToast(e.message, "error");
        }
      });
    });

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: var(--color-loss);">Error al cargar alertas: ${err.message}</td></tr>`;
  }
}
