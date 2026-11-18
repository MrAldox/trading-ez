import { store } from "./store.js";
import { api } from "./api.js";
import { initOpportunitiesView, loadOpportunities } from "./views/opportunities.js";
import { initAdvisorView } from "./views/advisor.js";
import { initMarketView, updateTickerTape } from "./views/market.js";
import { initHeatmapView } from "./views/heatmap.js";
import { initPaperView, loadPaperPortfolio } from "./views/paper.js";
import { initNotificationsView, loadNotificationsData } from "./views/notifications.js";
import { initBacktestView } from "./views/backtest.js";
import { initScreenerView } from "./views/screener.js";
import { initNewsView } from "./views/news.js";
import { initCalendarView } from "./views/calendar.js";
import { initJournalView } from "./views/journal.js";
import { initAlertsView } from "./views/alerts.js";
import { initModelStatusView } from "./views/model_status.js";
import { openGlossaryModal, closeGlossaryModal } from "./views/glossary.js";

let autoRefreshSeconds = 15;
let autoRefreshTimer = null;

async function bootApp() {
  console.log("Iniciando Trading EZ Market Terminal Pro (INVERT Theme)...");

  // 1. Inicializar Tema (Dark / Light)
  const currentTheme = store.getState().theme || "dark";
  document.documentElement.setAttribute("data-theme", currentTheme);
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  const themeIcon = document.getElementById("themeIcon");
  if (themeToggleBtn) {
    if (themeIcon) {
      themeIcon.className = currentTheme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
    }
    themeToggleBtn.addEventListener("click", () => {
      const newTheme = store.getState().theme === "dark" ? "light" : "dark";
      store.setTheme(newTheme);
      document.documentElement.setAttribute("data-theme", newTheme);
      if (themeIcon) {
        themeIcon.className = newTheme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
      }
    });
  }

  // 2. Glosario Modal Trigger
  const btnGlossary = document.getElementById("btn-open-glossary");
  if (btnGlossary) {
    btnGlossary.addEventListener("click", () => openGlossaryModal());
  }

  // 3. Sistema de Pestañas (4 Principales + Dropdown de Herramientas)
  const coreTabButtons = document.querySelectorAll(".nav-tabs-group .nav-tab-btn");
  const dropdownItemButtons = document.querySelectorAll(".dropdown-item-btn");
  const tabViews = document.querySelectorAll(".tab-view");
  const toolsDropdown = document.getElementById("nav-tools-dropdown");
  const toolsTrigger = document.getElementById("btn-tools-trigger");

  const initializedTabs = new Set();

  function switchTab(tabId) {
    // Actualizar botones de pestañas principales
    coreTabButtons.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });

    // Actualizar botones del dropdown
    let isSecondaryTool = false;
    dropdownItemButtons.forEach((btn) => {
      const isMatch = btn.getAttribute("data-tab") === tabId;
      btn.classList.toggle("active", isMatch);
      if (isMatch) isSecondaryTool = true;
    });

    // Indicar en el botón disparador si una herramienta secundaria está activa
    if (toolsTrigger) {
      toolsTrigger.classList.toggle("active", isSecondaryTool);
      if (isSecondaryTool) {
        toolsTrigger.style.borderColor = "var(--color-accent)";
        toolsTrigger.style.color = "var(--color-accent)";
      } else {
        toolsTrigger.style.borderColor = "var(--border-color)";
        toolsTrigger.style.color = "var(--text-secondary)";
      }
    }

    // Cerrar menú desplegable al seleccionar
    if (toolsDropdown) {
      toolsDropdown.classList.remove("open");
    }

    // Activar vista en el DOM (0ms instantáneo)
    tabViews.forEach((view) => {
      view.classList.toggle("active", view.id === `view-${tabId}`);
    });

    store.setState({ currentTab: tabId });

    // Carga perezosa de la vista seleccionada
    if (!initializedTabs.has(tabId)) {
      initializedTabs.add(tabId);
      try {
        switch (tabId) {
          case "opportunities":
            initOpportunitiesView();
            break;
          case "advisor":
            initAdvisorView();
            break;
          case "paper":
            initPaperView();
            break;
          case "notifications":
            initNotificationsView();
            break;
          case "market":
            initMarketView();
            break;
          case "heatmap":
            initHeatmapView();
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
      } catch (err) {
        console.error(`[Trading EZ] Error inicializando vista ${tabId}:`, err);
      }
    } else {
      // Si ya estaba inicializada, refrescar suavemente
      if (tabId === "notifications") {
        loadNotificationsData();
      } else if (tabId === "paper") {
        loadPaperPortfolio();
      }
    }
  }

  // Asignar listeners a pestañas principales
  coreTabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // Asignar listeners a elementos del menú desplegable
  dropdownItemButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // Toggle del menú desplegable Más Herramientas
  if (toolsTrigger && toolsDropdown) {
    toolsTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      toolsDropdown.classList.toggle("open");
    });

    document.addEventListener("click", (e) => {
      if (!toolsDropdown.contains(e.target)) {
        toolsDropdown.classList.remove("open");
      }
    });
  }

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
  updateTickerTape();

  // 8. Monitor de Horarios Bancarios (Kill Zones) en Header
  const killZonePill = document.getElementById("header-kill-zone-pill");
  if (killZonePill) {
    killZonePill.addEventListener("click", () => switchTab("advisor"));
  }
  updateHeaderKillZone();
  setInterval(() => {
    updateHeaderKillZone();
  }, 45000);

  // 9. Botón Notificaciones en Header
  const headerNotifBtn = document.getElementById("header-notif-btn");
  if (headerNotifBtn) {
    headerNotifBtn.addEventListener("click", () => switchTab("notifications"));
  }
  updateNotificationBadge();

  // 10. Botón de Refresco Manual
  const manualRefreshBtn = document.getElementById("manualRefreshBtn");
  if (manualRefreshBtn) {
    manualRefreshBtn.addEventListener("click", async () => {
      manualRefreshBtn.classList.add("fa-spin");
      try {
        await updateTickerTape();
        const activeTab = store.getState().currentTab;
        if (activeTab === "opportunities") {
          await loadOpportunities(true);
        } else if (activeTab === "paper") {
          await loadPaperPortfolio();
        } else if (activeTab === "notifications") {
          await loadNotificationsData();
        }
        await updateNotificationBadge();
        store.showToast("Datos de mercado actualizados", "success");
      } catch (err) {
        console.warn("Manual refresh warning:", err);
      } finally {
        setTimeout(() => manualRefreshBtn.classList.remove("fa-spin"), 600);
      }
    });
  }

  // 11. Contador de Auto-Refresco
  setupAutoRefreshCounter(switchTab);
}

function setupAutoRefreshCounter(switchTab) {
  const timerEl = document.getElementById("refreshTimer");
  if (!timerEl) return;

  autoRefreshSeconds = 15;
  timerEl.textContent = `${autoRefreshSeconds}s`;

  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(async () => {
    autoRefreshSeconds -= 1;
    if (autoRefreshSeconds <= 0) {
      autoRefreshSeconds = 15;
      timerEl.textContent = `${autoRefreshSeconds}s`;
      try {
        await updateTickerTape();
        await updateNotificationBadge();
      } catch (err) {
        console.warn("Auto refresh tick warning:", err);
      }
    } else {
      timerEl.textContent = `${autoRefreshSeconds}s`;
    }
  }, 1000);
}

async function updateNotificationBadge() {
  const badge = document.getElementById("notif-badge-count");
  if (!badge) return;
  try {
    const data = await api.getClosedTrades();
    const count = (data.notifications || []).length;
    if (count > 0) {
      badge.style.display = "inline-flex";
      badge.textContent = count > 9 ? "9+" : count;
    } else {
      badge.style.display = "none";
    }
  } catch (err) {
    // Silencioso
  }
}

async function updateHeaderKillZone() {
  const pill = document.getElementById("header-kill-zone-pill");
  const text = document.getElementById("header-kill-zone-text");
  if (!pill || !text) return;
  try {
    const data = await api.getKillZones();
    if (data && data.status_indicator) {
      pill.style.display = "inline-flex";
      pill.className = `kz-pill ${data.indicator_color === "profit" ? "validated" : "uncalibrated"}`;
      text.textContent = data.status_indicator.replace("VENTANA ACTIVA: ", "").substring(0, 24);
      pill.title = data.tactical_advice;
    }
  } catch (err) {
    console.warn("Kill zone update warning:", err);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootApp);
} else {
  bootApp();
}

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
      aiBox.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 13px;">
          <div class="status-dot"></div> Analizando setup cuantitativo con IA...
        </div>
      `;

      try {
        const res = await api.explainOpportunity(ticket.symbol, { ticket });
        aiBox.innerHTML = `
          <div style="font-size: 13px; line-height: 1.6; color: var(--text-primary); white-space: pre-wrap;">
            ${res.ai_explanation}
          </div>
        `;
      } catch (err) {
        aiBox.innerHTML = `
          <div style="color: var(--color-loss); font-size: 13px;">
            Error generando explicación: ${err.message}
          </div>
        `;
      }
    });
  }

  // Botón Ejecutar en Paper Trading desde Ficha
  const btnModalPaper = document.getElementById("btn-modal-paper-trade");
  if (btnModalPaper) {
    btnModalPaper.addEventListener("click", async () => {
      const ticket = store.getState().selectedOpportunity;
      if (!ticket) return;

      try {
        btnModalPaper.disabled = true;
        btnModalPaper.textContent = "Ejecutando...";

        const shares = ticket.sizing?.suggested_shares || 1;
        const res = await api.executePaperOrder({
          symbol: ticket.symbol,
          direction: ticket.direction,
          shares: shares,
          stop_loss: ticket.stop_loss,
          take_profit_1: ticket.take_profit_1,
          take_profit_2: ticket.take_profit_2,
        });

        store.showToast(`Orden ejecutada: ${shares} ${ticket.symbol} en Paper Trading`, "success");
        document.getElementById("ticket-modal").classList.remove("open");

        // Cambiar a la vista de paper trading
        const paperTabBtn = document.querySelector('[data-tab="paper"]');
        if (paperTabBtn) paperTabBtn.click();
      } catch (err) {
        store.showToast(`Error al ejecutar orden: ${err.message}`, "error");
      } finally {
        btnModalPaper.disabled = false;
        btnModalPaper.textContent = "💼 Ejecutar en Paper Trading";
      }
    });
  }
}

function setupOrderModalActions() {
  const form = document.getElementById("order-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const symbol = document.getElementById("order-symbol").value.toUpperCase().trim();
    const direction = document.getElementById("order-direction").value;
    const shares = parseInt(document.getElementById("order-shares").value, 10);
    const stopLoss = parseFloat(document.getElementById("order-sl").value) || 0.0;
    const tp1 = parseFloat(document.getElementById("order-tp1").value) || 0.0;
    const tp2 = parseFloat(document.getElementById("order-tp2").value) || 0.0;

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = "Enviando orden...";

    try {
      const res = await api.executePaperOrder({
        symbol,
        direction,
        shares,
        stop_loss: stopLoss,
        take_profit_1: tp1,
        take_profit_2: tp2,
      });

      store.showToast(res.message || `Orden simulada de ${symbol} completada`, "success");
      document.getElementById("order-modal").classList.remove("open");
      form.reset();

      // Recargar cartera si la vista está activa
      loadPaperPortfolio();
    } catch (err) {
      store.showToast(`Error al procesar orden: ${err.message}`, "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Confirmar Orden Simulada";
    }
  });
}
