/**
 * Trading EZ - Vista de Backtesting Riguroso y Verificación Institucional
 */
import { api } from "../api.js";
import { store } from "../store.js";

export async function initBacktestView() {
  const container = document.getElementById("view-backtest");
  if (!container) return;

  container.innerHTML = `
    <!-- Formulario de Configuración del Backtest -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">⚙️ Simulación Event-Driven sin Sesgo Prospectivo</h2>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: flex-end;">
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Fecha Inicio:</label>
          <input type="date" id="bt-start-date" value="2022-01-01" />
        </div>
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Fecha Fin:</label>
          <input type="date" id="bt-end-date" value="2026-11-16" />
        </div>
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Capital Inicial ($):</label>
          <input type="number" id="bt-capital" value="100000" step="5000" />
        </div>
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Riesgo / Trade (%):</label>
          <input type="number" id="bt-risk-pct" value="1.0" step="0.2" min="0.2" max="3.0" />
        </div>
        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Prob. Mínima:</label>
          <input type="number" id="bt-min-prob" value="0.58" step="0.02" min="0.50" max="0.80" />
        </div>
        <div>
          <button id="btn-run-backtest" class="btn btn-primary" style="width: 100%; height: 42px;">
            🚀 Ejecutar Simulación
          </button>
        </div>
      </div>
    </div>

    <!-- Contenedor de Resultados del Backtest -->
    <div id="bt-results-container">
      <div class="empty-state">
        <div class="empty-state-icon">📈</div>
        <div class="empty-state-title">Cargando último reporte de validación...</div>
      </div>
    </div>
  `;

  document.getElementById("btn-run-backtest").addEventListener("click", () => runNewBacktest());

  await loadLatestBacktest();
}

export async function loadLatestBacktest() {
  const container = document.getElementById("bt-results-container");
  if (!container) return;

  try {
    const data = await api.getLatestBacktest();
    renderBacktestResults(data);
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔬</div>
        <div class="empty-state-title">Aún no se ha ejecutado un backtest en la sesión</div>
        <div class="empty-state-desc">Haz clic en "Ejecutar Simulación" arriba para correr el motor event-driven sobre los 5 años del universo.</div>
      </div>
    `;
  }
}

export async function runNewBacktest() {
  const container = document.getElementById("bt-results-container");
  const btn = document.getElementById("btn-run-backtest");
  if (!container) return;

  const startDate = document.getElementById("bt-start-date").value;
  const endDate = document.getElementById("bt-end-date").value;
  const capital = parseFloat(document.getElementById("bt-capital").value || "100000");
  const riskPct = parseFloat(document.getElementById("bt-risk-pct").value || "1.0");
  const minProb = parseFloat(document.getElementById("bt-min-prob").value || "0.58");

  try {
    btn.disabled = true;
    btn.textContent = "⏳ Simulando...";

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚙️</div>
        <div class="empty-state-title">Ejecutando Simulación Event-Driven...</div>
        <div class="empty-state-desc">Auditando velas día por día, ejecutando a la apertura de t+1, deduciendo costes y verificando salidas con prioridad de Stop Loss.</div>
      </div>
    `;

    const res = await api.runBacktest({
      start_date: startDate,
      end_date: endDate,
      initial_capital: capital,
      risk_pct: riskPct,
      min_prob: minProb,
    });

    renderBacktestResults(res);
    store.showToast("Backtest completado con éxito", "success");
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="border-color: var(--color-loss);">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Error al ejecutar backtest</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.textContent = "🚀 Ejecutar Simulación";
  }
}

function renderBacktestResults(res) {
  const container = document.getElementById("bt-results-container");
  if (!container) return;

  const m = res.summary_metrics || res.metrics || {};
  const mc = res.monte_carlo || {};
  const regimes = res.regime_breakdown || {};
  const isVal = res.is_validated ?? (m.profit_factor >= 1.3 && m.expectancy_r > 0);

  const statusCls = isVal ? "validated" : "uncalibrated";
  const statusTxt = isVal ? "ESTADO: VALIDADA" : "ESTADO: NO VALIDADA (Bajo Criterios Institucionales)";

  container.innerHTML = `
    <!-- Sello Institucional de Validación Fuera de Muestra -->
    <div class="glass-card" style="margin-bottom: 16px; border-left: 4px solid ${isVal ? "var(--color-profit)" : "var(--color-warning)"};">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
        <div>
          <span class="status-badge ${statusCls}">${statusTxt}</span>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 6px;">
            Periodo: <strong>${res.start_date}</strong> a <strong>${res.end_date}</strong> | 
            ${isVal ? "La estrategia supera los umbrales de Profit Factor (>1.3) y expectativa neta positiva." : "La estrategia no alcanza Profit Factor > 1.30 neto de costes. Se reporta honestamente tal cual exige la regla."}
          </div>
        </div>
        <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">
          ID: ${res.backtest_id || "bt_current"}
        </div>
      </div>
    </div>

    <!-- Grilla de Métricas Financieras -->
    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-label">CAGR Estrategia</span>
        <span class="metric-value ${m.total_cagr >= 0 ? "profit" : "loss"}">${store.formatPercent(m.total_cagr || 0)}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">CAGR SPY Benchmark</span>
        <span class="metric-value">${store.formatPercent(m.benchmark_spy_cagr || 0)}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Profit Factor</span>
        <span class="metric-value ${m.profit_factor >= 1.3 ? "profit" : "warning"}">${(m.profit_factor || 0).toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Win Rate</span>
        <span class="metric-value">${store.formatPercent((m.win_rate || 0) * 100, false)}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Expectancy (R)</span>
        <span class="metric-value ${m.expectancy_r > 0 ? "profit" : "loss"}">${store.formatR(m.expectancy_r || 0)}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Max Drawdown</span>
        <span class="metric-value loss">-${Math.abs(m.max_drawdown_pct || 0).toFixed(2)}%</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Sharpe Ratio</span>
        <span class="metric-value">${(m.sharpe_ratio || 0).toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Total Operaciones</span>
        <span class="metric-value">${m.total_trades || 0}</span>
      </div>
    </div>

    <!-- Gráfico de Curva de Capital (Canvas) -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px;">Curva de Equidad Simulación vs Benchmark</h3>
      <div style="width: 100%; height: 320px; position: relative;">
        <canvas id="bt-equity-canvas" style="width: 100%; height: 100%; display: block;"></canvas>
      </div>
    </div>

    <!-- Robustez Monte Carlo y Rendimiento por Régimen -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
      <div class="glass-card">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">🎲 Simulación Monte Carlo (1,000 Iteraciones)</h3>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Barajado aleatorio del orden de operaciones para evaluar riesgo de ruina.</div>
        <table class="data-table">
          <tbody>
            <tr><td>Mediana CAGR:</td><td style="font-weight: 700;">${store.formatPercent(mc.median_cagr || 0)}</td></tr>
            <tr><td>Peor 5% Drawdown (VaR 95%):</td><td style="color: var(--color-loss); font-weight: 700;">-${Math.abs(mc.worst_5pct_drawdown || 0).toFixed(2)}%</td></tr>
            <tr><td>Mejor 5% CAGR:</td><td style="color: var(--color-profit); font-weight: 700;">${store.formatPercent(mc.best_5pct_cagr || 0)}</td></tr>
          </tbody>
        </table>
      </div>

      <div class="glass-card">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">🌪️ Desglose por Régimen de Mercado</h3>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Protección de capital en mercados bajistas vs alcistas.</div>
        <table class="data-table">
          <thead>
            <tr><th>Régimen</th><th>Trades</th><th>Retorno</th><th>Max DD</th></tr>
          </thead>
          <tbody>
            ${Object.entries(regimes)
              .map(([regime, val]) => `
                <tr>
                  <td><strong>${regime}</strong></td>
                  <td>${val.trades || 0}</td>
                  <td style="color: ${(val.return_pct || 0) >= 0 ? "var(--color-profit)" : "var(--color-loss)"}; font-weight: 700;">
                    ${store.formatPercent(val.return_pct || 0)}
                  </td>
                  <td style="color: var(--color-loss);">-${Math.abs(val.max_dd || 0).toFixed(2)}%</td>
                </tr>
              `)
              .join("") || `<tr><td colspan="4" style="text-align: center;">Sin desglose de régimen</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;

  // Dibujar curva de equidad
  setTimeout(() => {
    drawEquityCurve(res.equity_curve || []);
  }, 50);
}

function drawEquityCurve(points) {
  const canvas = document.getElementById("bt-equity-canvas");
  if (!canvas || !points.length) return;

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  const values = points.map((p) => p.equity);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  // Fondo sutil de gradiente
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(59, 130, 246, 0.25)");
  grad.addColorStop(1, "rgba(59, 130, 246, 0.0)");

  // Trazo
  ctx.beginPath();
  points.forEach((pt, i) => {
    const x = (i / (points.length - 1)) * (w - 40) + 20;
    const y = h - 30 - ((pt.equity - minVal) / range) * (h - 60);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.strokeStyle = "#3b82f6";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Línea base y etiquetas
  ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
  ctx.font = "11px monospace";
  ctx.fillText(`Max: $${Math.round(maxVal).toLocaleString()}`, 20, 18);
  ctx.fillText(`Min: $${Math.round(minVal).toLocaleString()}`, 20, h - 10);
  ctx.fillText(`Final: $${Math.round(values[values.length - 1]).toLocaleString()}`, w - 120, 18);
}
