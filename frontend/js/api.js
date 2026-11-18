/**
 * Trading EZ - Cliente API Asíncrono (Vanilla ES6+)
 * Conecta todas las vistas del frontend con los endpoints FastAPI.
 */

const API_BASE = "/api";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const defaultHeaders = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errorMsg = `Error HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) errorMsg = errorJson.detail;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return await response.json();
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Salud y configuración
  health: () => request("/health"),

  // Oportunidades
  getOpportunities: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/opportunities${query ? `?${query}` : ""}`);
  },

  explainOpportunity: (symbol, body) =>
    request(`/opportunities/${symbol}/explain`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Mercado en vivo e histórico
  getLiveQuotes: (symbols = "") => {
    const query = symbols ? `?symbols=${encodeURIComponent(symbols)}` : "";
    return request(`/market/live${query}`);
  },

  getMarketHistory: (symbol, resolution = "1d", bars = 250) =>
    request(`/market/history?symbol=${encodeURIComponent(symbol)}&resolution=${resolution}&bars=${bars}`),

  getHeatmap: () => request("/market/heatmap"),

  // Backtest
  runBacktest: (config) =>
    request("/backtest", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  getLatestBacktest: () => request("/backtest/latest"),
  getBacktestById: (id) => request(`/backtest/${id}`),

  // Estado del modelo
  getModelStatus: () => request("/model/status"),
  rollbackModel: (targetVersion) =>
    request("/model/rollback", {
      method: "POST",
      body: JSON.stringify({ target_version: targetVersion }),
    }),

  // Paper Trading
  getPaperPortfolio: () => request("/paper/portfolio"),
  executePaperOrder: (order) =>
    request("/paper/order", {
      method: "POST",
      body: JSON.stringify(order),
    }),
  closePaperPosition: (positionId, reason = "MANUAL", exitPrice = null) =>
    request("/paper/close", {
      method: "POST",
      body: JSON.stringify({
        position_id: positionId,
        reason: reason,
        exit_price: exitPrice,
      }),
    }),
  getClosedTrades: () => request("/paper/closed"),
  getPaperNotifications: () => request("/paper/notifications"),
  resetPaperPortfolio: (capital = 10000.0) =>
    request("/paper/reset", {
      method: "POST",
      body: JSON.stringify({ capital }),
    }),

  // Escáner
  runScreener: (filters = {}) => {
    const cleanParams = {};
    for (const [k, v] of Object.entries(filters)) {
      if (v !== null && v !== undefined && v !== "") {
        cleanParams[k] = v;
      }
    }
    const query = new URLSearchParams(cleanParams).toString();
    return request(`/screener${query ? `?${query}` : ""}`);
  },

  // Noticias
  getNews: (ticker = "") => {
    const query = ticker ? `?ticker=${encodeURIComponent(ticker)}` : "";
    return request(`/news${query}`);
  },

  // Calendario
  getCalendar: () => request("/calendar"),

  // Diario
  getJournalEntries: () => request("/journal"),
  addJournalEntry: (entry) =>
    request("/journal", {
      method: "POST",
      body: JSON.stringify(entry),
    }),

  // Alertas
  getAlerts: () => request("/alerts"),
  createAlert: (alert) =>
    request("/alerts", {
      method: "POST",
      body: JSON.stringify(alert),
    }),
  deleteAlert: (alertId) =>
    request(`/alerts/${alertId}`, {
      method: "DELETE",
    }),

  // Asesor Financiero IA y Horarios Bancarios
  getKillZones: () => request("/advisor/kill-zones"),
  getAdvisorBriefing: () => request("/advisor/daily-briefing"),
  askAdvisor: (message, history = []) =>
    request("/advisor/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
    }),
};
