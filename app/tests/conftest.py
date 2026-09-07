"""Fixtures de test — DB SQLite en mémoire + client FastAPI."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db

# Importer TOUS les modèles pour que Base.metadata les connaisse
from app.modules.auth.models import User, PlatformConnection  # noqa: F401
from app.modules.trading_config.models import TradingConfig, BotState  # noqa: F401
from app.modules.market_analysis.models import TechnicalSignal  # noqa: F401
from app.modules.trading_engine.models import Position, Trade  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401
from app.modules.tax_tracking.models import TaxableConversion  # noqa: F401

# SQLite en mémoire — StaticPool pour partager la même connexion (même DB)
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def client():
    """Client FastAPI avec DB SQLite en mémoire — tables créées/détruites par test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    from app.main import app as real_app
    real_app.dependency_overrides[get_db] = override_get_db

    with TestClient(real_app, raise_server_exceptions=False) as c:
        yield c

    real_app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def auth_headers(client) -> dict:
    """Crée un utilisateur et retourne les headers JWT."""
    client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    })
    response = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpassword123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
