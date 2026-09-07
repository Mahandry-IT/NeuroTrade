"""Accès aux données — module history.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class HistoryRepository:
    """Repository pour le module history."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
