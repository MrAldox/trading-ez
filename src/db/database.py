"""
Trading EZ - Configuración de Base de Datos Relacional (SQLAlchemy 2.0 / SQLite WAL).
Diseñado para persistencia local y migración sin fricciones a PostgreSQL en producción/Render.
"""
from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import settings, BASE_DIR

db_url = settings.data.db_path
if not db_url.startswith("sqlite") and not db_url.startswith("postgresql"):
    # Si es ruta relativa a archivo sqlite
    db_file = BASE_DIR / db_url
    db_file.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_file}"

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
    echo=False,
)

# Habilitar modo WAL en SQLite para soporte de alta concurrencia en FastAPI
if db_url.startswith("sqlite"):
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency injection para FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
