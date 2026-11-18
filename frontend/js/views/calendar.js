/**
 * Trading EZ - Vista de Calendario Económico y Eventos Macro
 */
import { api } from "../api.js";

export async function initCalendarView() {
  const container = document.getElementById("view-calendar");
  if (!container) return;

  container.innerHTML = `
    <div class="glass-card" style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">📅 Calendario Económico y Eventos Macro</h2>
      <div style="font-size: 12px; color: var(--text-secondary);">Decisiones de tasas (FOMC), inflación (CPI), nóminas no agrícolas (NFP) y PIB con enlaces a fuentes oficiales.</div>
    </div>

    <div class="glass-card">
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Evento</th>
              <th>Fecha Programada</th>
              <th>Impacto</th>
              <th>Descripción</th>
              <th>Fuente Oficial</th>
            </tr>
          </thead>
          <tbody id="calendar-events-tbody">
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Cargando eventos oficiales...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  await loadCalendar();
}

export async function loadCalendar() {
  const tbody = document.getElementById("calendar-events-tbody");
  if (!tbody) return;

  try {
    const data = await api.getCalendar();
    const events = data.events || [];

    if (!events.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No hay eventos macro programados para los próximos días.</td></tr>`;
      return;
    }

    tbody.innerHTML = events
      .map((ev) => {
        const isHigh = ev.impact === "ALTO";
        const badgeCls = isHigh ? "blocked" : "uncalibrated";

        return `
          <tr>
            <td><strong>${ev.event}</strong></td>
            <td>${ev.date}</td>
            <td><span class="status-badge ${badgeCls}">${ev.impact}</span></td>
            <td style="color: var(--text-secondary);">${ev.description || "-"}</td>
            <td>
              <a href="${ev.source_url}" target="_blank" rel="noopener noreferrer" style="color: var(--color-brand); text-decoration: underline;">
                Fuente ↗
              </a>
            </td>
          </tr>
        `;
      })
      .join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="color: var(--color-loss);">Error al cargar calendario: ${err.message}</td></tr>`;
  }
}
