/**
 * Trading EZ - Vista del Asesor Financiero IA y Monitor de Horarios Bancarios (Kill Zones)
 */
import { api } from "../api.js";
import { store } from "../store.js";

let chatHistory = [];

export async function initAdvisorView() {
  const container = document.getElementById("view-advisor");
  if (!container) return;

  // Si no está inyectado el esqueleto, inyectarlo
  if (!document.getElementById("advisor-chat-form")) {
    container.innerHTML = `
      <!-- Cabecera de la Asesoría Financiera Cuantitativa -->
      <div class="glass-card" style="margin-bottom: 16px;">
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
          <div>
            <h2 style="font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px;">
              🤖 Asesor Financiero Cuantitativo &amp; Horarios Bancarios
            </h2>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
              Criterio institucional, gestión de riesgo estricta y sincronización con las ventanas de inyección de liquidez de Wall Street (Kill Zones).
            </div>
          </div>
          <div id="advisor-live-session-pill">
            <span class="status-badge uncalibrated">Consultando sesiones...</span>
          </div>
        </div>
      </div>

      <!-- Panel de Horarios Bancarios e Inyección de Liquidez (Kill Zones) -->
      <div class="glass-card" style="margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 style="font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 6px;">
            🏛️ Monitor de Ventanas Institucionales (Kill Zones de Wall Street)
          </h3>
          <span id="advisor-ny-clock" style="font-family: var(--font-mono); font-size: 12px; color: var(--color-brand);">--:--:-- EST</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 14px;" id="advisor-kill-zones-grid">
          <!-- Render dinámico de las 4 ventanas -->
        </div>

        <div id="advisor-tactical-banner" style="background: rgba(14, 165, 233, 0.1); border-left: 3px solid var(--color-brand); padding: 10px 14px; border-radius: 4px; font-size: 13px; color: var(--text-primary);">
          Cargando consejo táctico de la sesión...
        </div>
      </div>

      <!-- Interfaz de Chat con el Asesor Financiero -->
      <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 style="font-size: 15px; font-weight: 700;">
            💬 Conversa con tu Asesor de Trading
          </h3>
          <button id="btn-clear-chat" class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px;">
            🧹 Limpiar Chat
          </button>
        </div>

        <!-- Sugerencias de Consultas Rápidas -->
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px;">
          <button class="btn btn-secondary quick-prompt-btn" data-prompt="¿Cuál es la mejor operación para hoy y a qué hora entrar?">
            🎯 ¿Cuál es la mejor operación de hoy?
          </button>
          <button class="btn btn-secondary quick-prompt-btn" data-prompt="¿A qué hora exacta operan los bancos y cómo aprovecho el movimiento?">
            ⏰ ¿A qué hora operan los bancos?
          </button>
          <button class="btn btn-secondary quick-prompt-btn" data-prompt="¿Cómo gano un ingreso extra seguro si solo tengo $1,000 USD?">
            💰 Ingreso extra con $1,000
          </button>
          <button class="btn btn-secondary quick-prompt-btn" data-prompt="¿Por qué dicen que en ciertas horas bancarias se gana sí o sí?">
            🛡️ ¿Es verdad que se gana 'sí o sí'?
          </button>
        </div>

        <!-- Ventana de Mensajes -->
        <div id="advisor-chat-messages" style="min-height: 280px; max-height: 480px; overflow-y: auto; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 12px; margin-bottom: 14px;">
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <div style="font-size: 24px;">🤖</div>
            <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 13px; line-height: 1.5; max-width: 85%;">
              <strong>¡Hola! Soy tu Asesor Financiero Cuantitativo en Trading EZ.</strong><br/>
              Estoy aquí para ayudarte a operar con <strong>criterio institucional</strong>, aprovechar las horas donde los bancos inyectan volumen real y proteger tu capital para generar un ingreso extra sin correr riesgos innecesarios.<br/><br/>
              <em>Hazme cualquier pregunta o selecciona una de las consultas rápidas arriba.</em>
            </div>
          </div>
        </div>

        <!-- Formulario de Entrada del Usuario -->
        <form id="advisor-chat-form" style="display: flex; gap: 10px;">
          <input 
            type="text" 
            id="advisor-user-input" 
            placeholder="Escribe tu consulta al asesor (ej. ¿A qué hora entro hoy a NVDA? o ¿Cómo gestionar mi riesgo?)..." 
            required 
            style="flex: 1;"
          />
          <button type="submit" id="advisor-send-btn" class="btn btn-primary" style="white-space: nowrap; padding: 0 20px;">
            <span>Enviar Consulta</span> ↗
          </button>
        </form>
      </div>
    `;
  }

  // Listeners de la vista (evitar binds duplicados)
  setupAdvisorListeners();

  try {
    await loadKillZonesData();
  } catch (e) {
    console.warn("Advisor load error:", e);
  }
}

function setupAdvisorListeners() {
  const form = document.getElementById("advisor-chat-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = document.getElementById("advisor-user-input");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      await handleUserQuery(text);
    });
  }

  document.querySelectorAll(".quick-prompt-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      handleUserQuery(prompt);
    });
  });

  const clearBtn = document.getElementById("btn-clear-chat");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      chatHistory = [];
      const messagesContainer = document.getElementById("advisor-chat-messages");
      if (messagesContainer) {
        messagesContainer.innerHTML = `
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <div style="font-size: 24px;">🤖</div>
            <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 13px; line-height: 1.5; max-width: 85%;">
              Chat reiniciado. ¿En qué puedo orientarte hoy?
            </div>
          </div>
        `;
      }
    });
  }
}

export async function loadKillZonesData() {
  const sessionPill = document.getElementById("advisor-live-session-pill");
  const clockEl = document.getElementById("advisor-ny-clock");
  const grid = document.getElementById("advisor-kill-zones-grid");
  const tacticalBanner = document.getElementById("advisor-tactical-banner");

  if (!grid) return;

  const data = await api.getKillZones();
  if (clockEl) clockEl.textContent = data.current_ny_time || "";

  if (sessionPill) {
    const isKz = data.is_kill_zone_active;
    const badgeCls = isKz ? "validated" : "uncalibrated";
    sessionPill.innerHTML = `
      <span class="status-badge ${badgeCls}">
        <span class="indicator-dot"></span> ${data.status_indicator}
      </span>
    `;
  }

  if (tacticalBanner) {
    tacticalBanner.innerHTML = `<strong>Tesis Táctica:</strong> ${data.tactical_advice}`;
  }

  const keyWindows = [
    { title: "London Open Kill Zone", time: "02:00 - 05:00 EST", desc: "Manipulación europea (Judas Swing) y barrido del rango asiático." },
    { title: "NY Open Kill Zone", time: "09:30 - 11:00 EST", desc: "Apertura oficial de Wall Street. Máxima inyección de liquidez y volumen institucional." },
    { title: "ICT Silver Bullet", time: "10:00 - 11:00 EST", desc: "Relleno de desequilibrios (Fair Value Gaps) tras los datos macro de las 10:00 AM." },
    { title: "London Fix / Cierre", time: "11:00 - 12:00 EST", desc: "Fijación institucional de precios de divisas y toma de ganancias parciales." },
  ];

  grid.innerHTML = keyWindows
    .map((w) => `
      <div style="background: var(--bg-card); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color);">
        <div style="font-size: 11px; text-transform: uppercase; color: var(--color-brand); font-weight: 700;">${w.time}</div>
        <div style="font-weight: 700; font-size: 13px; margin: 4px 0;">${w.title}</div>
        <div style="font-size: 11px; color: var(--text-secondary);">${w.desc}</div>
      </div>
    `)
    .join("");
}

async function handleUserQuery(queryText) {
  const container = document.getElementById("advisor-chat-messages");
  const sendBtn = document.getElementById("advisor-send-btn");
  if (!container) return;

  // Render mensaje del usuario
  appendMessage("user", queryText);

  // Deshabilitar botón mientras responde
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.innerHTML = `<span>Analizando con criterio...</span> ⏳`;
  }

  // Indicador de escribiendo
  const loadingId = "msg-loading-" + Date.now();
  appendLoadingBubble(loadingId);

  try {
    const res = await api.askAdvisor(queryText, chatHistory);
    removeLoadingBubble(loadingId);

    // Formatear respuesta en markdown simple
    appendMessage("bot", res.response);

    chatHistory.push({ role: "user", content: queryText });
    chatHistory.push({ role: "assistant", content: res.response });

  } catch (err) {
    removeLoadingBubble(loadingId);
    appendMessage("bot", `⚠️ Error consultando al asesor: ${err.message}`);
  } finally {
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.innerHTML = `<span>Enviar Consulta</span> ↗`;
    }
  }
}

function appendMessage(sender, text) {
  const container = document.getElementById("advisor-chat-messages");
  if (!container) return;

  const isUser = sender === "user";
  const avatar = isUser ? "👤" : "🤖";
  const align = isUser ? "flex-end" : "flex-start";
  const bg = isUser ? "var(--bg-secondary)" : "var(--bg-card)";
  const border = isUser ? "border: 1px solid var(--color-brand);" : "border: 1px solid var(--border-color);";

  const formattedContent = formatSimpleMarkdown(text);

  const wrapper = document.createElement("div");
  wrapper.style.display = "flex";
  wrapper.style.flexDirection = isUser ? "row-reverse" : "row";
  wrapper.style.gap = "10px";
  wrapper.style.alignItems = "flex-start";

  wrapper.innerHTML = `
    <div style="font-size: 24px;">${avatar}</div>
    <div style="background: ${bg}; ${border} padding: 12px 16px; border-radius: 8px; font-size: 13px; line-height: 1.5; max-width: 85%;">
      ${formattedContent}
    </div>
  `;

  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

function appendLoadingBubble(id) {
  const container = document.getElementById("advisor-chat-messages");
  if (!container) return;

  const wrapper = document.createElement("div");
  wrapper.id = id;
  wrapper.style.display = "flex";
  wrapper.style.gap = "10px";
  wrapper.style.alignItems = "flex-start";

  wrapper.innerHTML = `
    <div style="font-size: 24px;">🤖</div>
    <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 10px 14px; border-radius: 8px; font-size: 12px; color: var(--text-secondary);">
      Consultando liquidez institucional, spreads y horas bancarias...
    </div>
  `;

  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

function removeLoadingBubble(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatSimpleMarkdown(txt) {
  if (!txt) return "";

  let html = txt
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h4 style="font-size: 14px; font-weight: 700; color: var(--color-brand); margin: 8px 0 4px 0;">$1</h4>');
  html = html.replace(/^#### (.*$)/gim, '<h5 style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 6px 0 2px 0;">$1</h5>');

  // Negrita
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Cursiva
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Código en línea
  html = html.replace(/`(.*?)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 4px; border-radius: 3px; font-family: var(--font-mono); font-size: 12px;">$1</code>');

  // Listas con viñetas
  html = html.replace(/^\* (.*$)/gim, '<li style="margin-left: 18px; margin-bottom: 3px;">$1</li>');

  // Saltos de línea
  html = html.replace(/\n\n/g, '<div style="margin-bottom: 8px;"></div>');
  html = html.replace(/\n/g, '<br/>');

  return html;
}
