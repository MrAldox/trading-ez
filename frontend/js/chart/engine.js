/**
 * Trading EZ - Motor de Gráficos Canvas Nativo en HTML5 (Sin dependencias externas).
 * Soporte de devicePixelRatio para pantallas Retina, dibujo de velas, volumen, EMAs,
 * líneas de orden (Entrada, Stop Loss, TP1, TP2) y crosshair interactivo.
 */

export class CanvasChartEngine {
  constructor(canvasElement, options = {}) {
    this.canvas = canvasElement;
    this.ctx = this.canvas.getContext("2d");
    this.data = [];
    this.levels = options.levels || null; // { entry, stop, tp1, tp2 }
    this.crosshair = { active: false, x: 0, y: 0 };

    this.padding = { top: 20, right: 65, bottom: 25, left: 10 };
    this.colors = {
      bg: "#080d1a",
      grid: "rgba(255, 255, 255, 0.05)",
      text: "#9ca3af",
      bullish: "#10b981",
      bearish: "#ef4444",
      volume: "rgba(59, 130, 246, 0.25)",
      ema21: "#38bdf8",
      ema50: "#fbbf24",
      entry: "#38bdf8",
      stop: "#ef4444",
      tp: "#10b981",
    };

    this._bindEvents();
    this.resize();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.width = rect.width;
    this.height = rect.height;

    this.canvas.width = Math.floor(rect.width * dpr);
    this.canvas.height = Math.floor(rect.height * dpr);
    this.ctx.scale(dpr, dpr);
    this.render();
  }

  setData(candles, levels = null) {
    this.data = candles || [];
    this.levels = levels;
    this.render();
  }

  _bindEvents() {
    window.addEventListener("resize", () => this.resize());

    this.canvas.addEventListener("mousemove", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.crosshair.active = true;
      this.crosshair.x = e.clientX - rect.left;
      this.crosshair.y = e.clientY - rect.top;
      this.render();
    });

    this.canvas.addEventListener("mouseleave", () => {
      this.crosshair.active = false;
      this.render();
    });
  }

  render() {
    if (!this.width || !this.height) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    if (!this.data || this.data.length === 0) {
      ctx.fillStyle = this.colors.text;
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Sin datos de gráfico disponibles", this.width / 2, this.height / 2);
      return;
    }

    const plotW = this.width - this.padding.left - this.padding.right;
    const plotH = this.height - this.padding.top - this.padding.bottom;

    // Calcular escalas de precio
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    let maxVol = 0;

    for (const c of this.data) {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
      if (c.volume > maxVol) maxVol = c.volume;
    }

    // Incluir niveles de stop y tp en el rango visible si existen
    if (this.levels) {
      if (this.levels.stop && this.levels.stop < minPrice) minPrice = this.levels.stop;
      if (this.levels.tp2 && this.levels.tp2 > maxPrice) maxPrice = this.levels.tp2;
      if (this.levels.tp1 && this.levels.tp1 > maxPrice) maxPrice = this.levels.tp1;
    }

    const priceMargin = (maxPrice - minPrice) * 0.08 || 1.0;
    minPrice -= priceMargin;
    maxPrice += priceMargin;
    const priceRange = maxPrice - minPrice;

    const getY = (p) => this.padding.top + (1.0 - (p - minPrice) / priceRange) * plotH;
    const n = this.data.length;
    const barSpacing = plotW / Math.max(n, 1);
    const candleW = Math.max(2, barSpacing * 0.7);

    // 1. Rejilla y Eje de Precios (Y)
    ctx.strokeStyle = this.colors.grid;
    ctx.lineWidth = 1;
    ctx.fillStyle = this.colors.text;
    ctx.font = "10px monospace";
    ctx.textAlign = "left";

    const ySteps = 5;
    for (let i = 0; i <= ySteps; i++) {
      const priceVal = minPrice + (priceRange * (i / ySteps));
      const y = getY(priceVal);
      ctx.beginPath();
      ctx.moveTo(this.padding.left, y);
      ctx.lineTo(this.width - this.padding.right, y);
      ctx.stroke();

      ctx.fillText(priceVal.toFixed(2), this.width - this.padding.right + 6, y + 3);
    }

    // 2. Dibujar Volumen (Barras semitransparentes en el fondo)
    const volHeightMax = plotH * 0.22;
    for (let i = 0; i < n; i++) {
      const c = this.data[i];
      const x = this.padding.left + (i * barSpacing) + (barSpacing / 2);
      const volH = (c.volume / (maxVol || 1)) * volHeightMax;
      const volY = this.padding.top + plotH - volH;

      ctx.fillStyle = c.close >= c.open ? "rgba(16, 185, 129, 0.18)" : "rgba(239, 68, 68, 0.18)";
      ctx.fillRect(x - candleW / 2, volY, candleW, volH);
    }

    // 3. Dibujar Medias Móviles (EMA 21 y EMA 50)
    const drawLine = (prop, color) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      let started = false;
      for (let i = 0; i < n; i++) {
        const val = this.data[i][prop];
        if (val != null) {
          const x = this.padding.left + (i * barSpacing) + (barSpacing / 2);
          const y = getY(val);
          if (!started) { ctx.moveTo(x, y); started = true; }
          else { ctx.lineTo(x, y); }
        }
      }
      ctx.stroke();
    };
    drawLine("ema_21", this.colors.ema21);
    drawLine("ema_50", this.colors.ema50);

    // 4. Dibujar Velas Japonesas (Candlesticks)
    for (let i = 0; i < n; i++) {
      const c = this.data[i];
      const x = this.padding.left + (i * barSpacing) + (barSpacing / 2);
      const isUp = c.close >= c.open;
      const color = isUp ? this.colors.bullish : this.colors.bearish;

      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 1;

      // Mechas (Wicks)
      ctx.beginPath();
      ctx.moveTo(x, getY(c.high));
      ctx.lineTo(x, getY(c.low));
      ctx.stroke();

      // Cuerpo (Body)
      const openY = getY(c.open);
      const closeY = getY(c.close);
      const bodyY = Math.min(openY, closeY);
      const bodyH = Math.max(Math.abs(closeY - openY), 1);

      ctx.fillRect(x - candleW / 2, bodyY, candleW, bodyH);
    }

    // 5. Dibujar Niveles de Operación (Entrada, Stop Loss, TP1, TP2)
    if (this.levels) {
      const drawLevel = (price, label, color) => {
        if (!price) return;
        const y = getY(price);
        ctx.strokeStyle = color;
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(this.padding.left, y);
        ctx.lineTo(this.width - this.padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Etiqueta lateral
        ctx.fillStyle = color;
        ctx.fillRect(this.width - this.padding.right, y - 8, 62, 16);
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 9px monospace";
        ctx.textAlign = "center";
        ctx.fillText(`${label} ${price.toFixed(1)}`, this.width - this.padding.right + 31, y + 4);
      };

      drawLevel(this.levels.entry, "ENTRY", this.colors.entry);
      drawLevel(this.levels.stop, "STOP", this.colors.stop);
      drawLevel(this.levels.tp1, "TP1", this.colors.tp);
      if (this.levels.tp2) drawLevel(this.levels.tp2, "TP2", this.colors.tp);
    }

    // 6. Crosshair Interactivo y Ejes Dinámicos
    if (this.crosshair.active) {
      const cx = this.crosshair.x;
      const cy = this.crosshair.y;

      if (cx >= this.padding.left && cx <= this.width - this.padding.right &&
          cy >= this.padding.top && cy <= this.height - this.padding.bottom) {

        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);

        // Línea vertical
        ctx.beginPath();
        ctx.moveTo(cx, this.padding.top);
        ctx.lineTo(cx, this.height - this.padding.bottom);
        ctx.stroke();

        // Línea horizontal
        ctx.beginPath();
        ctx.moveTo(this.padding.left, cy);
        ctx.lineTo(this.width - this.padding.right, cy);
        ctx.stroke();
        ctx.setLineDash([]);

        // Precio apuntado en eje Y
        const hoverPrice = maxPrice - ((cy - this.padding.top) / plotH) * priceRange;
        ctx.fillStyle = "#3b82f6";
        ctx.fillRect(this.width - this.padding.right, cy - 8, 62, 16);
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 9px monospace";
        ctx.textAlign = "center";
        ctx.fillText(hoverPrice.toFixed(2), this.width - this.padding.right + 31, cy + 4);

        // Barra apuntada en eje X
        const idxHover = Math.floor((cx - this.padding.left) / barSpacing);
        if (idxHover >= 0 && idxHover < n) {
          const hoverCandle = this.data[idxHover];
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(cx - 35, this.height - this.padding.bottom, 70, 18);
          ctx.fillStyle = "#ffffff";
          ctx.fillText(hoverCandle.timestamp, cx, this.height - this.padding.bottom + 13);
        }
      }
    }
  }
}
