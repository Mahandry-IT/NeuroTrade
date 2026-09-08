"""Service simulation — bascule simulation/réel (RG-5).

Le mode simulation est activé par défaut. La désactivation nécessite
une confirmation explicite non réversible par erreur.
"""

from sqlalchemy.orm import Session

from app.modules.trading_config.service import TradingConfigService


class SimulationService:
    def __init__(self, db: Session):
        self.config_service = TradingConfigService(db)

    def toggle_simulation(self, user_id: int, simulation_mode: bool, confirm: bool) -> str:
        """Bascule simulation/réel avec confirmation obligatoire."""
        return self.config_service.set_simulation_mode(user_id, simulation_mode, confirm)

    def is_simulation_active(self, user_id: int) -> bool:
        config = self.config_service.get_config(user_id)
        return config["simulation_mode"]
