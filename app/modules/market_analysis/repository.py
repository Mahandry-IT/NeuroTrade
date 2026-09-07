"""Accès aux données — module market_analysis.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class MarketAnalysisRepository:
    """Repository pour le module market_analysis."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
