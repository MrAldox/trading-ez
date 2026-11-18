/**
 * Trading EZ - Vista de Noticias Financieras y Sentimiento
 */
import { api } from "../api.js";

export async function initNewsView() {
  const container = document.getElementById("view-news");
  if (!container) return;

  container.innerHTML = `
    <div class="glass-card" style="margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h2 style="font-size: 16px; font-weight: 700;">📰 Feed de Noticias y Sentimiento</h2>
          <div style="font-size: 12px; color: var(--text-secondary);">Titulares de impacto procesados para advertencia de riesgo y contexto.</div>
        </div>
        <button id="btn-refresh-news" class="btn btn-secondary">
          🔄 Actualizar
        </button>
      </div>
    </div>

    <div id="news-list-container" style="display: flex; flex-direction: column; gap: 12px;">
      <div class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <div class="empty-state-title">Cargando noticias...</div>
      </div>
    </div>
  `;

  document.getElementById("btn-refresh-news").addEventListener("click", () => loadNews());
  try {
    await loadNews();
  } catch (e) {
    console.warn("News initial load error:", e);
  }
}

export async function loadNews() {
  const container = document.getElementById("news-list-container");
  if (!container) return;

  try {
    const data = await api.getNews();
    const items = data.news || [];

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📰</div>
          <div class="empty-state-title">No hay noticias recientes en este momento</div>
        </div>
      `;
      return;
    }

    container.innerHTML = items
      .map((item) => {
        const isBull = item.sentiment_score > 0.1;
        const isBear = item.sentiment_score < -0.1;
        const badgeCls = isBull ? "validated" : isBear ? "blocked" : "uncalibrated";
        const badgeTxt = isBull ? "Sentimiento Alcista" : isBear ? "Sentimiento Bajista" : "Sentimiento Neutral";

        return `
          <div class="glass-card" style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
              <h3 style="font-size: 15px; font-weight: 700; line-height: 1.4;">
                <a href="${item.url}" target="_blank" rel="noopener noreferrer" style="color: var(--text-primary); text-decoration: none;">
                  ${item.title} ↗
                </a>
              </h3>
              <span class="status-badge ${badgeCls}" style="flex-shrink: 0;">${badgeTxt}</span>
            </div>

            <div style="display: flex; gap: 12px; font-size: 12px; color: var(--text-muted); align-items: center;">
              <span>Activo: <strong>${item.ticker}</strong></span>
              <span>•</span>
              <span>Fuente: ${item.source}</span>
              <span>•</span>
              <span>${item.published_at}</span>
            </div>
          </div>
        `;
      })
      .join("");

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="border-color: var(--color-loss);">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Error al cargar noticias</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>
    `;
  }
}
