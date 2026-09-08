"""Service auth — use cases d'authentification et connexion plateforme."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import (
    encrypt_api_key, decrypt_api_key, get_password_hash,
    verify_password, create_access_token,
)
from app.modules.auth.repository import UserRepository, PlatformConnectionRepository
from app.modules.auth.models import PlatformConnectionStatus

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.platform_repo = PlatformConnectionRepository(db)

    def register(self, username: str, email: str, password: str) -> dict:
        if self.user_repo.get_by_username(username):
            raise ValueError("Username already taken")
        if self.user_repo.get_by_email(email):
            raise ValueError("Email already registered")

        user = self.user_repo.create(username, email, get_password_hash(password))
        logger.info("user_registered user_id=%d", user.id)
        return {"id": user.id, "username": user.username, "email": user.email}

    def login(self, username: str, password: str) -> str:
        user = self.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        token = create_access_token({"sub": str(user.id), "username": user.username})
        logger.info("user_login user_id=%d", user.id)
        return token

    def connect_platform(
        self, user_id: int, platform_name: str, api_key: str, api_secret: str
    ) -> dict:
        enc_key = encrypt_api_key(api_key)
        enc_secret = encrypt_api_key(api_secret)
        conn = self.platform_repo.create_or_update(
            user_id, platform_name, enc_key, enc_secret
        )

        # Health check réel via Kraken API si plateforme = kraken
        if platform_name.lower() == "kraken":
            from app.modules.kraken.client import KrakenSpotClient
            try:
                client = KrakenSpotClient(api_key_encrypted=enc_key, api_secret_encrypted=enc_secret)
                client.get_time()  # vérifie la connectivité (public)
                client.get_balance()  # vérifie les credentials (privé)
                self.platform_repo.update_status(user_id, PlatformConnectionStatus.CONNECTED)
            except Exception as e:
                logger.warning("kraken_health_check_failed user_id=%d error=%s", user_id, str(e))
                self.platform_repo.update_status(user_id, PlatformConnectionStatus.ERROR)
                raise ValueError(f"Kraken connection failed: {e}")
        else:
            self.platform_repo.update_status(user_id, PlatformConnectionStatus.CONNECTED)

        logger.info("platform_connected user_id=%d platform=%s", user_id, platform_name)
        return {
            "platform_name": conn.platform_name,
            "status": conn.status.value if conn.status else "connected",
        }

    def get_platform_status(self, user_id: int) -> Optional[dict]:
        conn = self.platform_repo.get_by_user(user_id)
        if not conn:
            return None
        return {
            "platform_name": conn.platform_name,
            "status": conn.status.value,
            "last_health_check": conn.last_health_check,
        }

    def is_platform_connected(self, user_id: int) -> bool:
        conn = self.platform_repo.get_by_user(user_id)
        return conn is not None and conn.status == PlatformConnectionStatus.CONNECTED
