/**
 * Trading EZ - Vista de Mercado en Vivo y Watchlist Cuantitativo
 */
import { api } from "../api.js";
import { store } from "../store.js";
import { FinancialCanvasChart } from "../chart/engine.js";

let marketChart = null;
let currentSymbol = "SPY";

export async function initMarketView() {
  const container = document.getElementById("view-market");
  if (!container) return;

  container.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1.3fr; gap: 16px;">
      <!-- Panel Izquierdo: Watchlist y Filtros -->
      <div class="glass-card" style="display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h2 style="font-size: 16px; font-weight: 700;">📡 Seguimiento en Vivo</h2>
          <button id="btn-refresh-market" class="btn btn-secondary" style="padding: 4px 10px; font-size: 12px;">
            🔄 Actualizar
          </button>
        </div>

        <div class="table-responsive" style="max-height: 580px;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Precio</th>
                <th>24h %</th>
                <th>Clase</th>
              </tr>
            </thead>
            <tbody id="market-watchlist-tbody">
              <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Cargando cotizaciones...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Panel Derecho: Gráfico Canvas Interactivo -->
      <div class="glass-card" style="display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h2 id="market-chart-title" style="font-size: 16px; font-weight: 700;">SPY · S&P 500 ETF</h2>
            <div id="market-chart-sub" style="font-size: 12px; color: var(--text-secondary);">Gráfico Diario OHLCV + EMAs (9, 21, 50, 200)</div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary btn-chart-res active" data-res="1d" style="padding: 4px 8px; font-size: 11px;">1D</button>
            <button class="btn btn-secondary btn-chart-res" data-res="1h" style="padding: 4px 8px; font-size: 11px;">1H</button>
          </div>
        </div>

        <div class="chart-container" style="height: 480px;">
          <canvas id="market-chart-canvas" class="chart-canvas"></canvas>
          <div class="chart-overlay-controls">
            <span class="chart-tag" style="color: #60a5fa;">EMA 9</span>
            <span class="chart-tag" style="color: #f59e0b;">EMA 21</span>
            <span class="chart-tag" style="color: #10b981;">EMA 50</span>
            <span class="chart-tag" style="color: #ef4444;">EMA 200</span>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById("btn-refresh-market").addEventListener("click", () => loadMarketData());

  try {
    await loadMarketData();
  } catch (e) {
    console.warn("Mercado: error cargando cotizaciones iniciales:", e);
  }

  try {
    await loadSymbolChart(currentSymbol);
  } catch (e) {
    console.warn("Mercado: error cargando gráfico inicial:", e);
  }
}

export async function updateTickerTape() {
  const tapeContainer = document.getElementById("header-ticker-tape");
  if (!tapeContainer) return;

  try {
    const data = await api.getLiveQuotes();
    const quotes = data.quotes || [];

    if (!quotes.length) return;

    // Duplicar elementos para animación infinita continua
    const items = [...quotes, ...quotes];
    tapeContainer.innerHTML = items
      .map((q) => {
        const up = (q.change_pct || 0) >= 0;
        const cls = up ? "up" : "down";
        const sign = up ? "+" : "";
        return `
          <div class="tape-item ${cls}" data-sym="${q.symbol}">
            <span class="tape-sym">${q.symbol}</span>
            <span class="tape-price">${store.formatPrice(q.price)}</span>
            <span class="tape-change">${sign}${(q.change_pct || 0).toFixed(2)}%</span>
          </div>
        `;
      })
      .join("");

    tapeContainer.querySelectorAll(".tape-item").forEach((el) => {
      el.addEventListener("click", () => {
        const sym = el.getAttribute("data-sym");
        loadSymbolChart(sym);
      });
    });
  } catch (e) {
    console.warn("Error actualizando cinta de cotizaciones:", e);
  }
}

export async function loadMarketData() {
  const tbody = document.getElementById("market-watchlist-tbody");
  if (!tbody) return;

  try {
    const data = await api.getLiveQuotes();
    const quotes = data.quotes || [];

    if (!quotes.length) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">No hay cotizaciones disponibles</td></tr>`;
      return;
    }

    tbody.innerHTML = quotes
      .map((q) => {
        const up = (q.change_pct || 0) >= 0;
        const color = up ? "var(--color-profit)" : "var(--color-loss)";
        const sign = up ? "+" : "";
        return `
          <tr class="watchlist-row" data-sym="${q.symbol}" style="cursor: pointer;">
            <td>
              <strong>${q.symbol}</strong>
              <div style="font-size: 11px; color: var(--text-muted);">${q.name || ""}</div>
            </td>
            <td>${store.formatPrice(q.price)}</td>
            <td style="color: ${color}; font-weight: 700;">${sign}${(q.change_pct || 0).toFixed(2)}%</td>
            <td><span class="status-badge" style="font-size: 10px;">${q.asset_class}</span></td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll(".watchlist-row").forEach((row) => {
      row.addEventListener("click", () => {
        const sym = row.getAttribute("data-sym");
        loadSymbolChart(sym);
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" style="color: var(--color-loss);">Error al cargar mercado: ${e.message}</td></tr>`;
  }
}

export async function loadSymbolChart(symbol) {
  currentSymbol = symbol;
  const titleEl = document.getElementById("market-chart-title");
  if (titleEl) titleEl.textContent = `${symbol} · Análisis Técnico Institucional`;

  try {
    const histData = await api.getMarketHistory(symbol, "1d", 200);
    const canvas = document.getElementById("market-chart-canvas");
    if (canvas && histData.candles?.length) {
      marketChart = new FinancialCanvasChart("market-chart-canvas", {
        showVolume: true,
        showIndicators: true,
      });
      marketChart.setData(histData.candles);
    }
  } catch (err) {
    console.warn("Error cargando histórico para gráfico:", err);
  }
}
