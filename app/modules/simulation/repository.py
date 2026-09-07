"""Accès aux données — module simulation.

TODO: implémenter les requêtes (voir plan, section 4. Repository).
"""


class SimulationRepository:
    """Repository pour le module simulation."""

    def __init__(self, db_session):
        self.db = db_session

    # TODO: méthodes CRUD / requêtes agrégées
