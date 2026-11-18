"""
Trading EZ - Modelos de Base de Datos Relacionales (SQLAlchemy 2.0).
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, Date
from src.db.database import Base, engine

class AssetModel(Base):
    __tablename__ = "assets"

    symbol = Column(String(32), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    asset_class = Column(String(32), nullable=False, index=True)  # stocks, etfs, crypto, commodities
    sector = Column(String(64), nullable=False)
    market = Column(String(32), nullable=False)
    currency = Column(String(8), default="USD")
    tick_size = Column(Float, default=0.01)
    est_cost_bps = Column(Float, default=5.0)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class OpportunityModel(Base):
    __tablename__ = "opportunities"

    id = Column(String(64), primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    target_date = Column(String(16), nullable=False)
    horizon = Column(String(16), default="medium")
    direction = Column(String(8), default="LONG")

    calibrated_prob = Column(Float, nullable=False)
    expected_r = Column(Float, nullable=False)

    entry_market = Column(Float, nullable=False)
    entry_limit = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float, nullable=False)

    suggested_shares = Column(Integer, default=0)
    capital_at_risk = Column(Float, default=0.0)

    score_breakdown_json = Column(Text, default="{}")
    reasons_json = Column(Text, default="[]")
    contradictions_json = Column(Text, default="[]")
    warnings_json = Column(Text, default="[]")
    invalidation_condition = Column(Text, default="")
    model_version = Column(String(64), default="")

    status = Column(String(32), default="ACTIVE")  # ACTIVE | FILLED | CLOSED_WIN | CLOSED_LOSS | EXPIRED | INVALIDATED
    actual_outcome_r = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)

class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"

    id = Column(String(64), primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    name = Column(String(128), nullable=False)
    universe_config_json = Column(Text, default="[]")
    start_date = Column(String(16), nullable=False)
    end_date = Column(String(16), nullable=False)

    is_validated = Column(Boolean, default=False)
    total_cagr = Column(Float, default=0.0)
    benchmark_cagr = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    max_drawdown_duration_days = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    expectancy_r = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)

    equity_curve_json = Column(Text, default="[]")
    trades_json = Column(Text, default="[]")
    monte_carlo_json = Column(Text, default="{}")
    regime_breakdown_json = Column(Text, default="{}")

class PaperPortfolioModel(Base):
    __tablename__ = "paper_portfolio"

    id = Column(String(32), primary_key=True, default="default")
    initial_capital = Column(Float, default=10000.0)
    current_cash = Column(Float, default=10000.0)
    total_realized_pnl = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PaperPositionModel(Base):
    __tablename__ = "paper_positions"

    id = Column(String(64), primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    direction = Column(String(8), default="LONG")
    shares = Column(Integer, default=0)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(16), default="OPEN")  # OPEN | CLOSED
    exit_price = Column(Float, default=0.0, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String(32), default="", nullable=True)
    realized_pnl = Column(Float, default=0.0, nullable=True)
    realized_r = Column(Float, default=0.0, nullable=True)

class TradingJournalModel(Base):
    __tablename__ = "trading_journal"

    id = Column(String(64), primary_key=True, index=True)
    opportunity_id = Column(String(64), nullable=True)
    symbol = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, default="")
    signal_prob = Column(Float, default=0.0)
    actual_outcome_r = Column(Float, default=0.0)
    lessons_learned = Column(Text, default="")
    tags_json = Column(Text, default="[]")

class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    condition = Column(String(16), default="ABOVE")  # ABOVE | BELOW
    target_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    triggered_at = Column(DateTime, nullable=True)

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Auto-migración segura para columnas nuevas en paper_positions
def _ensure_paper_columns():
    try:
        import sqlalchemy as sa
        with engine.connect() as conn:
            insp = sa.inspect(engine)
            cols = [c['name'] for c in insp.get_columns('paper_positions')]
            for col_name, col_def in [
                ('exit_price', 'FLOAT DEFAULT 0.0'),
                ('closed_at', 'DATETIME'),
                ('close_reason', "VARCHAR(32) DEFAULT ''"),
                ('realized_pnl', 'FLOAT DEFAULT 0.0'),
                ('realized_r', 'FLOAT DEFAULT 0.0'),
            ]:
                if col_name not in cols:
                    conn.execute(sa.text(f"ALTER TABLE paper_positions ADD COLUMN {col_name} {col_def}"))
            conn.commit()
    except Exception:
        pass

_ensure_paper_columns()
