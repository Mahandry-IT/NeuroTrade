"""Accès aux données — module trading_config.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class TradingConfigRepository:
    """Repository pour le module trading_config."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
