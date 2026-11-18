/**
 * Trading EZ - Orquestador Principal del Frontend (SPA)
 */
import { store } from "./store.js";
import { api } from "./api.js";
import { initOpportunitiesView, loadOpportunities } from "./views/opportunities.js";
import { initMarketView, updateTickerTape } from "./views/market.js";
import { initHeatmapView } from "./views/heatmap.js";
import { initPaperView, loadPaperPortfolio } from "./views/paper.js";
import { initBacktestView } from "./views/backtest.js";
import { initScreenerView } from "./views/screener.js";
import { initNewsView } from "./views/news.js";
import { initCalendarView } from "./views/calendar.js";
import { initJournalView } from "./views/journal.js";
import { initAlertsView } from "./views/alerts.js";
import { initModelStatusView } from "./views/model_status.js";
import { openGlossaryModal, closeGlossaryModal } from "./views/glossary.js";

document.addEventListener("DOMContentLoaded", async () => {
  console.log("Iniciando Trading EZ Market Terminal Pro...");

  // 1. Inicializar Tema (Dark / Light)
  const currentTheme = store.getState().theme;
  document.documentElement.setAttribute("data-theme", currentTheme);
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  if (themeToggleBtn) {
    themeToggleBtn.textContent = currentTheme === "dark" ? "☀️" : "🌙";
    themeToggleBtn.addEventListener("click", () => {
      const newTheme = store.getState().theme === "dark" ? "light" : "dark";
      store.setTheme(newTheme);
      themeToggleBtn.textContent = newTheme === "dark" ? "☀️" : "🌙";
    });
  }

  // 2. Glosario Modal Trigger
  const btnGlossary = document.getElementById("btn-open-glossary");
  if (btnGlossary) {
    btnGlossary.addEventListener("click", () => openGlossaryModal());
  }

  // 3. Sistema de Pestañas
  const tabButtons = document.querySelectorAll(".nav-tab-btn");
  const tabViews = document.querySelectorAll(".tab-view");

  const initializedTabs = new Set();

  function switchTab(tabId) {
    tabButtons.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });

    tabViews.forEach((view) => {
      view.classList.toggle("active", view.id === `view-${tabId}`);
    });

    store.setState({ currentTab: tabId });

    // Carga perezosa de la vista
    if (!initializedTabs.has(tabId)) {
      initializedTabs.add(tabId);
      switch (tabId) {
        case "opportunities":
          initOpportunitiesView();
          break;
        case "market":
          initMarketView();
          break;
        case "heatmap":
          initHeatmapView();
          break;
        case "paper":
          initPaperView();
          break;
        case "backtest":
          initBacktestView();
          break;
        case "screener":
          initScreenerView();
          break;
        case "news":
          initNewsView();
          break;
        case "calendar":
          initCalendarView();
          break;
        case "journal":
          initJournalView();
          break;
        case "alerts":
          initAlertsView();
          break;
        case "model-status":
          initModelStatusView();
          break;
      }
    }
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // 4. Modales Globales (Cierre al hacer clic fuera o botón cerrar)
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("open");
      }
    });

    overlay.querySelectorAll(".close-btn").forEach((closeBtn) => {
      closeBtn.addEventListener("click", () => {
        overlay.classList.remove("open");
      });
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.open").forEach((m) => m.classList.remove("open"));
    }
  });

  // 5. Controles dentro del Modal de Ficha de Operación
  setupTicketModalActions();

  // 6. Controles dentro del Modal de Orden de Paper Trading
  setupOrderModalActions();

  // 7. Arrancar primera vista (Oportunidades) y cinta de tickers
  switchTab("opportunities");
  await updateTickerTape();

  // Actualización periódica de cotizaciones (cada 30 segundos)
  setInterval(() => {
    updateTickerTape();
  }, 30000);
});

function setupTicketModalActions() {
  // Pestañas internas del modal
  const innerTabs = document.querySelectorAll(".modal-tab-btn");
  const innerContents = document.querySelectorAll(".modal-tab-content");

  innerTabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabTarget = btn.getAttribute("data-modal-tab");
      innerTabs.forEach((b) => b.classList.toggle("active", b === btn));
      innerContents.forEach((c) => {
        c.style.display = c.id === `modal-content-${tabTarget}` ? "block" : "none";
      });
    });
  });

  // Botón Copiar Texto
  const btnCopyText = document.getElementById("btn-modal-copy-text");
  if (btnCopyText) {
    btnCopyText.addEventListener("click", () => {
      const text = document.getElementById("modal-copy-text").value;
      navigator.clipboard.writeText(text).then(() => {
        store.showToast("Texto de la orden copiado al portapapeles", "success");
      });
    });
  }

  // Botón Copiar JSON
  const btnCopyJson = document.getElementById("btn-modal-copy-json");
  if (btnCopyJson) {
    btnCopyJson.addEventListener("click", () => {
      const jsonText = document.getElementById("modal-copy-json").value;
      navigator.clipboard.writeText(jsonText).then(() => {
        store.showToast("Bracket Order JSON copiado al portapapeles", "success");
      });
    });
  }

  // Botón Generar Explicación con IA
  const btnAiExplain = document.getElementById("btn-generate-ai-explanation");
  if (btnAiExplain) {
    btnAiExplain.addEventListener("click", async () => {
      const ticket = store.getState().selectedOpportunity;
      if (!ticket) return;

      const aiBox = document.getElementById("modal-ai-explanation-content");
      btnAiExplain.disabled = true;
      btnAiExplain.textContent = "⏳ Analizando...";

      aiBox.innerHTML = `
        <div style="padding: 12px; text-align: center; color: var(--text-secondary);">
          Consultando motor de IA y validando ausencia de alucinaciones en los precios...
        </div>
      `;

      try {
        const res = await api.explainOpportunity(ticket.symbol, { ticket: ticket });
        const exp = res.ai_explanation;

        aiBox.innerHTML = `
          <div class="ai-content">
            <h4 style="font-size: 14px; font-weight: 700; color: var(--color-brand); margin-bottom: 6px;">
              Tesis Cuantitativa &amp; Validación de Riesgo
            </h4>
            <p>${exp.thesis || ""}</p>

            <h4 style="font-size: 13px; font-weight: 700; color: var(--color-profit); margin-top: 10px; margin-bottom: 4px;">
              Argumentos a Favor
            </h4>
            <ul style="padding-left: 18px; margin-bottom: 8px;">
              ${(exp.reasons_expanded || []).map((r) => `<li>${r}</li>`).join("")}
            </ul>

            <h4 style="font-size: 13px; font-weight: 700; color: var(--color-loss); margin-top: 10px; margin-bottom: 4px;">
              Riesgos e Invalidación
            </h4>
            <p style="color: var(--text-secondary);">${exp.risk_assessment || ""}</p>
          </div>
        `;
      } catch (err) {
        aiBox.innerHTML = `
          <div style="color: var(--color-loss); padding: 8px;">
            Error generando explicación con IA: ${err.message}
          </div>
        `;
      } finally {
        btnAiExplain.disabled = false;
        btnAiExplain.textContent = "🤖 Regenerar Análisis IA";
      }
    });
  }

  // Botón Operar en Paper Trading desde el Modal
  const btnExecutePaper = document.getElementById("btn-modal-execute-paper");
  if (btnExecutePaper) {
    btnExecutePaper.addEventListener("click", async () => {
      const ticket = store.getState().selectedOpportunity;
      if (!ticket) return;

      try {
        const pos = ticket.position_size || {};
        await api.executePaperOrder({
          symbol: ticket.symbol,
          direction: ticket.direction || "LONG",
          shares: pos.shares || 1,
          stop_loss: ticket.stop_loss,
          take_profit_1: ticket.take_profit_1,
          take_profit_2: ticket.take_profit_2,
        });

        store.showToast(`Orden para ${ticket.symbol} ejecutada en Paper Trading`, "success");
        document.getElementById("ticket-modal").classList.remove("open");
        await loadPaperPortfolio();
      } catch (err) {
        store.showToast(err.message, "error");
      }
    });
  }
}

function setupOrderModalActions() {
  const form = document.getElementById("manual-order-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const sym = document.getElementById("order-symbol").value.trim().toUpperCase();
    const dir = document.getElementById("order-direction").value;
    const shares = parseInt(document.getElementById("order-shares").value, 10);
    const sl = parseFloat(document.getElementById("order-sl").value || "0");
    const tp1 = parseFloat(document.getElementById("order-tp1").value || "0");
    const tp2 = parseFloat(document.getElementById("order-tp2").value || "0");

    try {
      await api.executePaperOrder({
        symbol: sym,
        direction: dir,
        shares: shares,
        stop_loss: sl,
        take_profit_1: tp1,
        take_profit_2: tp2,
      });

      store.showToast(`Orden ejecutada para ${sym}`, "success");
      document.getElementById("order-modal").classList.remove("open");
      form.reset();
      await loadPaperPortfolio();
    } catch (err) {
      store.showToast(err.message, "error");
    }
  });
}
