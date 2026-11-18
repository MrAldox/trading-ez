/**
 * Trading EZ - Vista de Diario de Trading Cuantitativo
 */
import { api } from "../api.js";
import { store } from "../store.js";

export async function initJournalView() {
  const container = document.getElementById("view-journal");
  if (!container) return;

  container.innerHTML = `
    <!-- Formulario para Registrar Nueva Entrada -->
    <div class="glass-card" style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">📓 Registrar Bitácora de Operación</h2>
      <form id="journal-form" style="display: flex; flex-direction: column; gap: 12px;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
          <div>
            <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Activo (Ticker):</label>
            <input type="text" id="j-symbol" placeholder="ej. NVDA" required />
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Prob. Señal (%):</label>
            <input type="number" id="j-prob" placeholder="ej. 65" min="0" max="100" />
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Resultado en R:</label>
            <input type="number" id="j-outcome" placeholder="ej. 1.5 o -1.0" step="0.1" />
          </div>
        </div>

        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Notas / Observaciones de la Operación:</label>
          <textarea id="j-notes" rows="2" placeholder="Motivos de entrada, gestión de la posición, ejecución..."></textarea>
        </div>

        <div>
          <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Lecciones Aprendidas / Errores Evitados:</label>
          <textarea id="j-lessons" rows="2" placeholder="¿Se respetó el plan? ¿Hubo deslizamiento? ¿Se movió el Stop Loss prematuramente?"></textarea>
        </div>

        <button type="submit" class="btn btn-primary" style="align-self: flex-start;">
          💾 Guardar Entrada en Diario
        </button>
      </form>
    </div>

    <!-- Historial de Entradas -->
    <div class="glass-card">
      <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px;">Historial del Diario</h3>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Activo</th>
              <th>Prob. Estimada</th>
              <th>Resultado R</th>
              <th>Notas</th>
              <th>Lecciones</th>
            </tr>
          </thead>
          <tbody id="journal-entries-tbody">
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Cargando bitácora...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById("journal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const sym = document.getElementById("j-symbol").value.trim().toUpperCase();
    const prob = parseFloat(document.getElementById("j-prob").value || "0") / 100.0;
    const outcome = parseFloat(document.getElementById("j-outcome").value || "0");
    const notes = document.getElementById("j-notes").value.trim();
    const lessons = document.getElementById("j-lessons").value.trim();

    try {
      await api.addJournalEntry({
        symbol: sym,
        signal_prob: prob,
        actual_outcome_r: outcome,
        notes: notes,
        lessons_learned: lessons,
      });

      store.showToast("Entrada registrada en el diario", "success");
      document.getElementById("journal-form").reset();
      await loadJournalEntries();
    } catch (err) {
      store.showToast(err.message, "error");
    }
  });

  await loadJournalEntries();
}

export async function loadJournalEntries() {
  const tbody = document.getElementById("journal-entries-tbody");
  if (!tbody) return;

  try {
    const data = await api.getJournalEntries();
    const entries = data.entries || [];

    if (!entries.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Aún no has registrado notas en el diario.</td></tr>`;
      return;
    }

    tbody.innerHTML = entries
      .map((entry) => {
        const outR = entry.actual_outcome_r || 0;
        const outColor = outR > 0 ? "var(--color-profit)" : outR < 0 ? "var(--color-loss)" : "inherit";

        return `
          <tr>
            <td>${store.formatDate(entry.created_at)}</td>
            <td><strong>${entry.symbol}</strong></td>
            <td>${entry.signal_prob ? `${Math.round(entry.signal_prob * 100)}%` : "-"}</td>
            <td style="color: ${outColor}; font-weight: 700;">${store.formatR(outR)}</td>
            <td style="max-width: 250px; white-space: normal;">${entry.notes || "-"}</td>
            <td style="max-width: 250px; white-space: normal; color: var(--text-secondary);">${entry.lessons_learned || "-"}</td>
          </tr>
        `;
      })
      .join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: var(--color-loss);">Error al cargar diario: ${err.message}</td></tr>`;
  }
}
