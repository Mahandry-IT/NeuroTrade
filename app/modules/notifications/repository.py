"""Accès aux données — module notifications.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class NotificationsRepository:
    """Repository pour le module notifications."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
