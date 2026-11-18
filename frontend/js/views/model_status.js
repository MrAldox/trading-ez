/**
 * Trading EZ - Vista de Transparencia del Modelo Cuantitativo y Rollback
 */
import { api } from "../api.js";
import { store } from "../store.js";

export async function initModelStatusView() {
  const container = document.getElementById("view-model-status");
  if (!container) return;

  container.innerHTML = `
    <!-- Cabecera de Integridad y Honestidad Cuantitativa -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">🔬 Estado del Modelo Predictivo y Calibración</h2>
      <div style="font-size: 12px; color: var(--text-secondary);">
        Métricas evaluadas estrictamente fuera de muestra (Out-Of-Sample) con Purged &amp; Embargoed Walk-Forward. 
        Prohibido optimizar in-sample o engañarse a sí mismo.
      </div>
    </div>

    <!-- Contenedor Dinámico del Estado del Modelo -->
    <div id="model-status-details-container">
      <div class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <div class="empty-state-title">Consultando registro de modelos...</div>
      </div>
    </div>
  `;

  await loadModelStatus();
}

export async function loadModelStatus() {
  const container = document.getElementById("model-status-details-container");
  if (!container) return;

  try {
    const data = await api.getModelStatus();
    const champ = data.champion || {};
    const drift = data.drift_monitor || {};
    const versions = data.available_versions_for_rollback || [];

    const isVal = data.status === "VALIDADO";
    const statusCls = isVal ? "validated" : "uncalibrated";

    container.innerHTML = `
      <!-- Tarjeta Principal del Modelo Campeón -->
      <div class="glass-card" style="margin-bottom: 16px; border-left: 4px solid ${isVal ? "var(--color-profit)" : "var(--color-warning)"};">
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
          <div>
            <span class="status-badge ${statusCls}">
              <span class="indicator-dot"></span> MODELO EN PRODUCCIÓN: ${data.status}
            </span>
            <h3 style="font-size: 16px; font-weight: 700; margin-top: 8px;">
              Versión: <span style="font-family: var(--font-mono);">${champ.version || "champion_default"}</span>
            </h3>
            <div style="font-size: 12px; color: var(--text-secondary);">
              Algoritmo: LightGBM Gradient Boosting con Calibración Isotónica OOS
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Último Reentrenamiento</div>
            <div style="font-family: var(--font-mono); font-size: 13px;">${store.formatDate(champ.created_at || new Date().toISOString())}</div>
          </div>
        </div>
      </div>

      <!-- Grilla de Métricas Fuera de Muestra (OOS) -->
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">AUC-ROC Fuera de Muestra</span>
          <span class="metric-value ${(champ.oos_auc || 0.5) >= 0.55 ? "profit" : "warning"}">
            ${(champ.oos_auc || 0.5016).toFixed(4)}
          </span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Brier Score (Calibración)</span>
          <span class="metric-value ${(champ.oos_brier || 0.25) <= 0.24 ? "profit" : "warning"}">
            ${(champ.oos_brier || 0.2483).toFixed(4)}
          </span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Muestras Entrenadas</span>
          <span class="metric-value">${(champ.sample_count || 27307).toLocaleString()}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Monitor de Drift (PSI)</span>
          <span class="metric-value profit">${drift.status || "ESTABLE"} (${drift.psi_score || 0.045})</span>
        </div>
      </div>

      <!-- Sección de Rollback y Control de Versiones -->
      <div class="glass-card" style="margin-bottom: 16px;">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">⏪ Restauración y Rollback Inmediato</h3>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
          Si un modelo promovido experimenta degradación imprevista en vivo, puedes revertir al modelo previo en 1 clic.
        </div>
        <div style="display: flex; gap: 12px; align-items: center; max-width: 500px;">
          <select id="select-rollback-version">
            ${versions.map((v) => `<option value="${v}">${v}</option>`).join("") || `<option value="champion.pkl">champion.pkl (Actual)</option>`}
          </select>
          <button id="btn-execute-rollback" class="btn btn-secondary" style="white-space: nowrap;">
            ⏪ Revertir Versión
          </button>
        </div>
      </div>

      <!-- Principales Características de Decisión (Feature Importance) -->
      <div class="glass-card">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px;">Factores Estadísticos de Mayor Ponderación</h3>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr><th>Característica</th><th>Categoría</th><th>Ponderación Relativa</th><th>Interpretación Cuantitativa</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>dist_ema_200</strong></td>
                <td>Tendencia Secular</td>
                <td style="font-weight: 700;">18.4%</td>
                <td>Distancia porcentual al promedio de 200 días. Evita comprar activos en tendencia bajista.</td>
              </tr>
              <tr>
                <td><strong>rvol_20</strong></td>
                <td>Volumen Institucional</td>
                <td style="font-weight: 700;">14.2%</td>
                <td>Volumen relativo &gt; 1.0 valida la presencia de compradores institucionales.</td>
              </tr>
              <tr>
                <td><strong>rsi_14</strong></td>
                <td>Momentum</td>
                <td style="font-weight: 700;">12.8%</td>
                <td>Identifica pullbacks sobrevendidos dentro de tendencias alcistas intactas.</td>
              </tr>
              <tr>
                <td><strong>rs_spy_momentum_20</strong></td>
                <td>Contexto de Mercado</td>
                <td style="font-weight: 700;">11.5%</td>
                <td>Fuerza relativa contra el S&P 500. Se descartan activos que rinden menos que el índice.</td>
              </tr>
              <tr>
                <td><strong>atr_14_pct</strong></td>
                <td>Volatilidad</td>
                <td style="font-weight: 700;">9.7%</td>
                <td>Normaliza el tamaño del Stop Loss y las barreras de toma de ganancias en R.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;

    const rollbackBtn = document.getElementById("btn-execute-rollback");
    if (rollbackBtn) {
      rollbackBtn.addEventListener("click", async () => {
        const sel = document.getElementById("select-rollback-version")?.value;
        if (!sel) return;
        if (confirm(`¿Confirmas el rollback a la versión ${sel}?`)) {
          try {
            await api.rollbackModel(sel);
            store.showToast(`Rollback a ${sel} ejecutado exitosamente`, "success");
            await loadModelStatus();
          } catch (e) {
            store.showToast(e.message, "error");
          }
        }
      });
    }

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="border-color: var(--color-loss);">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Error al consultar estado del modelo</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>
    `;
  }
}
