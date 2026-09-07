"""Accès aux données — module auth.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class AuthRepository:
    """Repository pour le module auth."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
