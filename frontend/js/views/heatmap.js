/**
 * Trading EZ - Vista de Mapa de Calor (Heatmap) Sectorial
 */
import { api } from "../api.js";
import { store } from "../store.js";
import { loadSymbolChart } from "./market.js";

export async function initHeatmapView() {
  const container = document.getElementById("view-heatmap");
  if (!container) return;

  container.innerHTML = `
    <div class="glass-card" style="margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h2 style="font-size: 16px; font-weight: 700;">🗺️ Mapa de Calor del Mercado</h2>
          <div style="font-size: 12px; color: var(--text-secondary);">Rendimiento relativo diario clasificado por sector y clase de activo.</div>
        </div>
        <button id="btn-refresh-heatmap" class="btn btn-secondary">
          🔄 Actualizar
        </button>
      </div>
    </div>

    <div id="heatmap-content-container">
      <div class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <div class="empty-state-title">Cargando sectores y rendimientos...</div>
      </div>
    </div>
  `;

  document.getElementById("btn-refresh-heatmap").addEventListener("click", () => loadHeatmap());
  try {
    await loadHeatmap();
  } catch (e) {
    console.warn("Heatmap error:", e);
  }
}

export async function loadHeatmap() {
  const container = document.getElementById("heatmap-content-container");
  if (!container) return;

  try {
    const data = await api.getHeatmap();
    const heatmap = data.heatmap || [];

    if (!heatmap.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <div class="empty-state-title">No hay datos de mapa de calor</div>
        </div>
      `;
      return;
    }

    let html = "";
    heatmap.forEach((sec) => {
      const avgUp = sec.avg_change_pct >= 0;
      const avgColor = avgUp ? "var(--color-profit)" : "var(--color-loss)";
      const avgSign = avgUp ? "+" : "";

      html += `
        <div class="glass-card" style="margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; margin-bottom: 12px;">
            <h3 style="font-size: 14px; font-weight: 700;">${sec.sector}</h3>
            <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: ${avgColor};">
              Promedio: ${avgSign}${sec.avg_change_pct.toFixed(2)}%
            </span>
          </div>

          <div class="heatmap-grid">
            ${sec.assets
              .map((a) => {
                const chg = a.change_pct || 0;
                const up = chg >= 0;
                const sign = up ? "+" : "";
                
                // Cálculo de intensidad de color
                const absChg = Math.min(Math.abs(chg), 5.0);
                const alpha = 0.2 + (absChg / 5.0) * 0.6;
                const bg = up
                  ? `rgba(16, 185, 129, ${alpha.toFixed(2)})`
                  : `rgba(239, 68, 68, ${alpha.toFixed(2)})`;
                const textCol = up ? "#a7f3d0" : "#fca5a5";

                return `
                  <div class="heatmap-tile" data-sym="${a.symbol}" style="background: ${bg}; color: #ffffff;">
                    <div class="heatmap-sym">${a.symbol}</div>
                    <div class="heatmap-change" style="color: ${textCol};">${sign}${chg.toFixed(2)}%</div>
                    <div class="heatmap-sec">${store.formatPrice(a.price)}</div>
                  </div>
                `;
              })
              .join("")}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Al hacer click en una baldosa, cargar en la pestaña de mercado
    container.querySelectorAll(".heatmap-tile").forEach((tile) => {
      tile.addEventListener("click", () => {
        const sym = tile.getAttribute("data-sym");
        const tabBtn = document.querySelector(`.nav-tab-btn[data-tab="market"]`);
        if (tabBtn) tabBtn.click();
        setTimeout(() => loadSymbolChart(sym), 50);
      });
    });

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="border-color: var(--color-loss);">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Error al cargar mapa de calor</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>
    `;
  }
}
