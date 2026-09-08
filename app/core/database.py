"""Connexion base de données (SQLAlchemy async + sync support)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base déclarative pour tous les modèles SQLAlchemy."""
    pass


def get_db():
    """FastAPI dependency — fournit une session DB par request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
