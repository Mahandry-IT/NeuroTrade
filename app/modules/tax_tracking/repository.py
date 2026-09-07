"""Accès aux données — module tax_tracking.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class TaxTrackingRepository:
    """Repository pour le module tax_tracking."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
