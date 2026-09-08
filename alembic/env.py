"""Alembic env.py — lit DATABASE_URL depuis .env."""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Lire DATABASE_URL depuis .env
from dotenv import load_dotenv
load_dotenv()

# Ajouter le répertoire parent au path pour importer les modèles
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
# Importer tous les modèles pour que Alembic les détecte
from app.modules.auth.models import User, PlatformConnection
from app.modules.trading_config.models import TradingConfig, BotState
from app.modules.market_analysis.models import TechnicalSignal
from app.modules.trading_engine.models import Position, Trade
from app.modules.notifications.models import Notification
from app.modules.tax_tracking.models import TaxableConversion

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url avec DATABASE_URL de l'environnement
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
