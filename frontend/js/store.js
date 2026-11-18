/**
 * Trading EZ - Gestor de Estado Global y Bus de Eventos (Store)
 */

class TerminalStore {
  constructor() {
    let initialTheme = "dark";
    try {
      initialTheme = localStorage.getItem("trading_ez_theme") || "dark";
    } catch (_) {}

    this.state = {
      theme: initialTheme,
      currentTab: "opportunities",
      opportunities: [],
      systemStatus: "CARGANDO",
      liveQuotes: {},
      paperPortfolio: null,
      selectedOpportunity: null,
      alerts: [],
    };
    this.listeners = new Map();
  }

  getState() {
    return this.state;
  }

  setState(partialState) {
    this.state = { ...this.state, ...partialState };
    this.notify("state_changed", this.state);
  }

  subscribe(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event).delete(callback);
  }

  notify(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((cb) => {
        try {
          cb(data);
        } catch (e) {
          console.error(`[Store Event Error] ${event}:`, e);
        }
      });
    }
  }

  setTheme(theme) {
    this.state.theme = theme;
    try {
      localStorage.setItem("trading_ez_theme", theme);
    } catch (_) {}
    document.documentElement.setAttribute("data-theme", theme);
    this.notify("theme_changed", theme);
  }

  showToast(message, type = "info", durationMs = 3500) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "⚠️";
    if (type === "warning") icon = "🔔";

    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, durationMs);
  }

  // Utilidades de formato numérico institucional
  formatPrice(num) {
    if (num === null || num === undefined || isNaN(num)) return "-";
    const abs = Math.abs(num);
    const decimals = abs >= 100 ? 2 : abs >= 1 ? 2 : 4;
    return `$${num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
  }

  formatPercent(num, includeSign = true) {
    if (num === null || num === undefined || isNaN(num)) return "-";
    const sign = includeSign && num > 0 ? "+" : "";
    return `${sign}${num.toFixed(2)}%`;
  }

  formatR(num) {
    if (num === null || num === undefined || isNaN(num)) return "-";
    const sign = num > 0 ? "+" : "";
    return `${sign}${num.toFixed(2)}R`;
  }

  formatDate(dateStr) {
    if (!dateStr) return "-";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("es-ES", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch (_) {
      return dateStr;
    }
  }
}

export const store = new TerminalStore();
