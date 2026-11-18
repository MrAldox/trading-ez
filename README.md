# Trading EZ · Market Terminal Pro

Plataforma cuantitativa institucional para predicción, selección y ranking de operaciones financieras sobre acciones (S&P 500 / Nasdaq), criptomonedas 24/7, ETFs y materias primas.

> **Aviso Legal:** Herramienta cuantitativa de apoyo a la decisión, no es asesoría financiera. El trading conlleva riesgo real de pérdida de capital.

---

## 🎯 Filosofía Central: "Menos Fallos = Selectividad Extrema"

A diferencia de las plataformas convencionales que fuerzan señales diarias para generar actividad, **Trading EZ** se rige por la disciplina institucional:
- **No se fuerzan señales:** Si ninguna oportunidad supera los umbrales estadísticos rigurosos, el terminal indica: *"Hoy no hay oportunidades con ventaja estadística suficiente"*. Este es un resultado cuantitativamente válido y esperado en muchos días de mercado.
- **Criterios de Admisión al Ranking:**
  1. **Probabilidad Calibrada Fuera de Muestra $\ge 60\%$:** Estimada con regresión isotónica sobre datos que el modelo jamás vio.
  2. **Expectativa Matemática Positiva ($E(R) > 0$):** Neta de comisiones, horquillas (spread) y deslizamiento (slippage).
  3. **Relación Riesgo/Beneficio $\ge 1.5$:** Con stop loss adaptativo anclado a ATR y soportes estructurales.
  4. **Alineación con Tendencia Superior:** Filtro de régimen macro (SPY sobre EMA 200 y activo sobre EMA 50/200).
  5. **Circuit Breakers Institucionales:** Bloqueo automático ante datos con $> 24$ horas de retraso o $\ge 4$ pérdidas consecutivas.

---

## 🏗️ Arquitectura y Stack Tecnológico

```
                          ┌──────────────────────────────────────┐
                          │    Trading EZ Frontend (SPA)         │
                          │   Vanilla JS (ES6+) + Canvas Engine  │
                          │    Bundle ~133 KB (< 250 KB max)     │
                          └──────────────────┬───────────────────┘
                                             │ HTTP REST / JSON
                                             ▼
                          ┌──────────────────────────────────────┐
                          │         FastAPI Backend              │
                          │   (Uvicorn, Python 3.13, Pydantic)   │
                          └──────┬───────────┬────────────┬──────┘
                                 │           │            │
            ┌────────────────────┘           │            └───────────────────┐
            ▼                                ▼                                ▼
┌──────────────────────┐        ┌───────────────────────┐        ┌───────────────────────┐
│ Motor Cuantitativo   │        │ Capa de Abstracción   │        │ Almacenamiento        │
│ • LightGBM + Isotonic│        │ • yfinance (Equities) │        │ • Parquet (OHLCV)     │
│ • Triple Barrera     │        │ • Binance (Crypto 24/7│        │ • SQLite WAL Mode     │
│ • Purged Walk-Forward│        │ • Alpaca / Finnhub    │        │ • Model Registry PKL  │
│ • Backtest Event-Driv│        │ • DataIntegrityAuditor│        │ • SQLAlchemy 2.0      │
└──────────────────────┘        └───────────────────────┘        └───────────────────────┘
```

- **Backend:** Python 3.13, FastAPI, Uvicorn, pandas, numpy, scikit-learn, LightGBM, SQLAlchemy 2.0 (SQLite WAL / PostgreSQL), APScheduler.
- **Frontend:** Single Page Application (SPA) construida 100% en Vanilla ES6+ sin frameworks pesados (React/Vue/Angular ni librerías de gráficos externas). Motor de gráficos propio sobre HTML5 Canvas con soporte para pantallas Retina (`devicePixelRatio`), crosshair interactivo y niveles de trading.
- **Capa de IA:** Explicador analítico de fichas con Gemini API / fallback determinista, blindado por un validador regex contra alucinaciones numéricas en precios y niveles.

---

## 📁 Estructura del Proyecto

```
TRADING/
├── config/
│   ├── universe.yaml         # Universo de 21 activos líquidos (acciones, crypto, ETFs, materias primas)
│   └── settings.yaml         # Umbrales de probabilidad, comisiones, capital y sizing
├── data/
│   ├── cache/daily/          # Datos históricos de 5+ años en Parquet
│   ├── db/trading_ez.db      # Base de datos SQLite (WAL mode)
│   └── models/               # Registro de modelos campeones y versiones para rollback
├── frontend/
│   ├── css/                  # Sistema de diseño Bloomberg (variables, base, componentes, charts)
│   ├── js/
│   │   ├── api.js            # Cliente fetch asíncrono
│   │   ├── app.js            # Orquestador SPA y modales
│   │   ├── store.js          # Gestor de estado reactivo y bus de eventos
│   │   ├── chart/engine.js   # Motor de gráficos Canvas propio
│   │   └── views/            # 11 módulos de interfaz (Oportunidades, Mercado, Heatmap, Backtest, etc.)
│   └── index.html            # Punto de entrada HTML5 mobile-first
├── src/
│   ├── api/                  # Servidor FastAPI y 10 routers REST
│   ├── core/                 # Configuración, errores y calendario de mercados
│   ├── data_providers/       # Proveedores abstractos, auditor de integridad y caché
│   ├── feature_engineering/  # 25+ factores causales sin sesgo prospectivo
│   ├── ml/                   # Triple barrera, Purged Walk-Forward, LightGBM y calibración
│   ├── backtest/             # Motor event-driven y simulaciones Monte Carlo
│   ├── opportunities/        # Fichas operativas, dimensionamiento y circuit breaker
│   ├── paper_trading/        # Cartera virtual y bitácora
│   ├── ai_explainer/         # Tesis con IA y validador anti-alucinaciones
│   └── scheduler/            # Tareas programadas en segundo plano (APScheduler)
├── Dockerfile                # Imagen multi-etapa optimizada
├── docker-compose.yml        # Configuración de ejecución local con volúmenes
└── requirements.txt          # Dependencias fijadas
```

---

## 🚀 Guía de Instalación y Ejecución Local

### 1. Clonar y Configurar Entorno Virtual

```bash
git clone <URL_DEL_REPOSITORIO>
cd TRADING

# Crear entorno virtual con Python 3.11+
python -m venv .venv

# Activar entorno (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Activar entorno (Linux/macOS)
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Copia el archivo de ejemplo:
```bash
cp .env.example .env
```
*(Las claves de API para Gemini, Alpaca o Finnhub son opcionales; el sistema cuenta con fallbacks deterministas completos si no se configuran).*

### 3. Descargar Datos Históricos (5+ Años)

```bash
python scripts/download_universe.py
```
*Descarga y audita automáticamente los 21 activos configurados en `config/universe.yaml` guardándolos en formato Parquet.*

### 4. Entrenar y Calibrar el Modelo Cuantitativo

```bash
python scripts/train_pipeline.py
```
*Ejecuta el etiquetado por Triple Barrera, Purged Walk-Forward CV y Calibración Isotónica OOS.*

### 5. Iniciar Servidor del Terminal

```bash
python src/api/main.py
```
Abre tu navegador en: [http://localhost:8000](http://localhost:8000)

### 6. Ejecutar la Batería Completa de Tests

```bash
python -m pytest tests/ -v
```

---

## 🐳 Ejecución con Docker y Docker Compose

Para levantar el terminal con persistencia de base de datos y modelos en volumen local:

```bash
docker compose up -d --build
```
El terminal estará disponible en `http://localhost:8000`.

---

## ☁️ Despliegue en Render (Paso a Paso)

Trading EZ está preparado para despliegue directo en **Render** como un *Web Service*:

1. **Crear Nuevo Web Service:**
   - En tu panel de Render, selecciona **New +** > **Web Service**.
   - Conecta tu repositorio de GitHub / GitLab.
2. **Configuración de Entorno:**
   - **Environment:** `Docker` (Render detectará automáticamente el `Dockerfile`).
   - **Region:** `Frankfurt` u `Oregon` (la más cercana a tu operativa).
   - **Branch:** `main`.
3. **Variables de Entorno (Environment Variables):**
   - `PORT`: (Asignado automáticamente por Render; nuestra aplicación ya escucha en `$PORT`).
   - `APP_ENV`: `production`
   - `DATABASE_URL`: `sqlite:////app/data/db/trading_ez.db` (o tu URL de PostgreSQL si deseas escalar).
   - `GEMINI_API_KEY`: *(Opcional)* Tu clave de Google AI Studio.
4. **Almacenamiento Persistente (Disk):**
   - Agrega un **Persistent Disk** montado en `/app/data` con un tamaño de `1 GB` a `5 GB` para persistir el historial de Parquet, las versiones del modelo LightGBM y la base de datos de Paper Trading / Diario.
5. **Health Check:**
   - Ruta: `/api/health`
6. **Deploy:** Haz clic en **Create Web Service**. ¡Listo! Tu terminal estará en vivo con HTTPS automático.

---

## 📊 Módulos del Terminal (11 Vistas)

1. **🎯 Oportunidades:** Ranking diario ordenado por expectativa matemática en R con fichas operativas listas para copiar (Entrada, Stop Loss, TP1 1.5R, TP2 3R, tamaño en USD y condición de invalidación).
2. **📡 Mercado en Vivo:** Watchlist interactivo de los activos del universo con cotizaciones en tiempo real y gráfico Canvas dinámico.
3. **🗺️ Mapa de Calor:** Rendimiento sectorial en tiempo real con ponderación por intensidad de color.
4. **💼 Paper Trading:** Cartera virtual de $10,000 USD con ejecución instantánea de órdenes desde las fichas de oportunidad.
5. **📈 Backtest Riguroso:** Simulación event-driven sin sesgo prospectivo, curva de equidad en Canvas, simulación Monte Carlo (1,000 iteraciones) y desglose por regímenes.
6. **🔍 Escáner Técnico:** Filtros combinables multicriterio (RSI, RVOL, cruce dorado, compresión de Bollinger, velas martillo).
7. **📰 Noticias & Sentimiento:** Titulares financieros estructurados con puntuación de impacto NLP.
8. **📅 Calendario Macro:** Fechas clave de FOMC, CPI, NFP y PIB con fuentes oficiales (FED, BLS, BEA).
9. **📓 Diario de Trading:** Registro estructurado de operaciones reales, probabilidades y lecciones aprendidas.
10. **🔔 Alertas de Precios:** Creación y monitorización de alertas por superación de cotización objetivo.
11. **🔬 Estado del Modelo:** Transparencia de calibración (Brier Score, OOS AUC), monitor de drift y botón de rollback a versiones anteriores.
