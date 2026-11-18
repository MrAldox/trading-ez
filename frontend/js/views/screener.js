/**
 * Trading EZ - Vista de Escáner Técnico Multicriterio
 */
import { api } from "../api.js";
import { store } from "../store.js";
import { loadSymbolChart } from "./market.js";

export async function initScreenerView() {
  const container = document.getElementById("view-screener");
  if (!container) return;

  container.innerHTML = `
    <!-- Barra de Filtros Combinables -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">🔍 Escáner Técnico Multicriterio</h2>
      <div style="display: flex; flex-wrap: wrap; gap: 14px; align-items: center;">
        
        <div class="filter-group">
          <label>RSI Máx:</label>
          <input type="number" id="sc-rsi-max" placeholder="ej. 35" style="width: 80px;" />
        </div>

        <div class="filter-group">
          <label>RSI Mín:</label>
          <input type="number" id="sc-rsi-min" placeholder="ej. 60" style="width: 80px;" />
        </div>

        <div class="filter-group">
          <label>RVOL &ge;:</label>
          <input type="number" id="sc-rvol-min" placeholder="ej. 1.2" step="0.1" style="width: 80px;" />
        </div>

        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input type="checkbox" id="sc-above-ema50" style="width: auto;" />
          Sobre EMA 50
        </label>

        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input type="checkbox" id="sc-above-ema200" style="width: auto;" />
          Sobre EMA 200 (Alcista Secular)
        </label>

        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input type="checkbox" id="sc-golden-cross" style="width: auto;" />
          Cruce Dorado (EMA 50 &gt; 200)
        </label>

        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input type="checkbox" id="sc-bb-squeeze" style="width: auto;" />
          Compresión Bollinger
        </label>

        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input type="checkbox" id="sc-hammer" style="width: auto;" />
          Vela Martillo
        </label>

        <button id="btn-run-screener" class="btn btn-primary" style="margin-left: auto;">
          🔍 Filtrar Universo
        </button>
      </div>
    </div>

    <!-- Resultados del Escáner -->
    <div class="glass-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="font-size: 14px; font-weight: 700;">Resultados Coincidentes</h3>
        <span id="screener-count" style="font-size: 12px; color: var(--text-secondary);">0 activos encontrados</span>
      </div>

      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Símbolo</th>
              <th>Sector / Clase</th>
              <th>Precio Cierre</th>
              <th>RSI (14)</th>
              <th>RVOL (20)</th>
              <th>Tendencia EMA</th>
              <th>Patrón Vela</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody id="screener-results-tbody">
            <tr><td colspan="8" style="text-align: center; color: var(--text-muted);">Configura los filtros o haz clic en Filtrar.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById("btn-run-screener").addEventListener("click", () => executeScreener());
  await executeScreener();
}

export async function executeScreener() {
  const tbody = document.getElementById("screener-results-tbody");
  const countEl = document.getElementById("screener-count");
  if (!tbody) return;

  const filters = {};
  const rsiMax = document.getElementById("sc-rsi-max")?.value;
  if (rsiMax) filters.rsi_max = parseFloat(rsiMax);

  const rsiMin = document.getElementById("sc-rsi-min")?.value;
  if (rsiMin) filters.rsi_min = parseFloat(rsiMin);

  const rvolMin = document.getElementById("sc-rvol-min")?.value;
  if (rvolMin) filters.rvol_min = parseFloat(rvolMin);

  if (document.getElementById("sc-above-ema50")?.checked) filters.above_ema50 = true;
  if (document.getElementById("sc-above-ema200")?.checked) filters.above_ema200 = true;
  if (document.getElementById("sc-golden-cross")?.checked) filters.golden_cross = true;
  if (document.getElementById("sc-bb-squeeze")?.checked) filters.bb_squeeze = true;
  if (document.getElementById("sc-hammer")?.checked) filters.hammer = true;

  try {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center;">Escaneando indicadores del universo...</td></tr>`;

    const data = await api.runScreener(filters);
    const matches = data.matches || [];

    if (countEl) countEl.textContent = `${matches.length} activos coincidentes`;

    if (!matches.length) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">Ningún activo cumple con los criterios seleccionados.</td></tr>`;
      return;
    }

    tbody.innerHTML = matches
      .map((m) => {
        const emaBadge = m.above_ema200
          ? `<span class="status-badge validated" style="font-size: 10px;">Sobre EMA 200</span>`
          : `<span class="status-badge blocked" style="font-size: 10px;">Bajo EMA 200</span>`;

        const patternBadge = m.pattern !== "Normal"
          ? `<span class="status-badge uncalibrated" style="font-size: 10px;">${m.pattern}</span>`
          : `<span style="color: var(--text-muted); font-size: 12px;">-</span>`;

        return `
          <tr>
            <td>
              <strong>${m.symbol}</strong>
              <div style="font-size: 11px; color: var(--text-muted);">${m.name || ""}</div>
            </td>
            <td>${m.sector || m.asset_class}</td>
            <td>${store.formatPrice(m.close)}</td>
            <td style="font-weight: 700;">${m.rsi_14}</td>
            <td style="color: ${m.rvol_20 >= 1.5 ? "var(--color-profit)" : "inherit"}; font-weight: 700;">${m.rvol_20}x</td>
            <td>${emaBadge}</td>
            <td>${patternBadge}</td>
            <td>
              <button class="btn btn-secondary btn-screen-view" data-sym="${m.symbol}" style="padding: 3px 8px; font-size: 11px;">
                📊 Gráfico
              </button>
            </td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll(".btn-screen-view").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sym = btn.getAttribute("data-sym");
        const tabBtn = document.querySelector(`.nav-tab-btn[data-tab="market"]`);
        if (tabBtn) tabBtn.click();
        setTimeout(() => loadSymbolChart(sym), 50);
      });
    });

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="color: var(--color-loss);">Error al ejecutar escáner: ${err.message}</td></tr>`;
  }
}
