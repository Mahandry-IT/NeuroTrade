"""Accès aux données — module trading_engine.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class TradingEngineRepository:
    """Repository pour le module trading_engine."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
