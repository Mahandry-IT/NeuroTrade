"""Factory — construit le bon executor selon le mode simulation/réel.

Un seul point de bascule dans le pipeline : le scheduler construit
le TradingEngineService avec l'executor approprié à chaque cycle.
"""

from sqlalchemy.orm import Session

from app.modules.kraken.client import KrakenSpotClient
from app.modules.kraken.executor import SimulatedExecutor, RealExecutor
from app.modules.auth.repository import PlatformConnectionRepository
from app.core.security import decrypt_api_key


def build_executor(
    db: Session,
    user_id: int,
    is_simulated: bool,
) -> RealExecutor | SimulatedExecutor:
    """Construit l'executor approprié selon le mode.

    Args:
        db: session SQLAlchemy.
        user_id: ID utilisateur.
        is_simulated: True pour simulation, False pour réel.

    Returns:
        SimulatedExecutor ou RealExecutor selon le mode.
    """
    from app.modules.trading_engine.repository import TradeRepository

    platform_repo = PlatformConnectionRepository(db)
    conn = platform_repo.get_by_user(user_id)

    client: KrakenSpotClient | None = None
    if conn and conn.platform_name == "kraken":
        client = KrakenSpotClient(
            api_key_encrypted=conn.encrypted_api_key,
            api_secret_encrypted=conn.encrypted_api_secret,
        )

    # Pas de clé API → client public uniquement (suffisant pour la simulation)
    if client is None:
        client = KrakenSpotClient()

    trade_repo = TradeRepository(db)

    if is_simulated:
        return SimulatedExecutor(client=client, trade_repo=trade_repo, user_id=user_id)
    else:
        if not conn or conn.platform_name != "kraken":
            raise ValueError("Kraken platform connection required for real trading")
        return RealExecutor(client=client)
