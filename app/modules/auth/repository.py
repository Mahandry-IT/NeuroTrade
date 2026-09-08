"""Repository auth — accès données User + PlatformConnection."""

from typing import Optional

from sqlalchemy.orm import Session

from app.modules.auth.models import User, PlatformConnection, PlatformConnectionStatus


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, username: str, email: str, hashed_password: str) -> User:
        user = User(username=username, email=email, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class PlatformConnectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> Optional[PlatformConnection]:
        return self.db.query(PlatformConnection).filter(
            PlatformConnection.user_id == user_id
        ).first()

    def create_or_update(
        self,
        user_id: int,
        platform_name: str,
        encrypted_api_key: str,
        encrypted_api_secret: str,
    ) -> PlatformConnection:
        conn = self.get_by_user(user_id)
        if conn:
            conn.platform_name = platform_name
            conn.encrypted_api_key = encrypted_api_key
            conn.encrypted_api_secret = encrypted_api_secret
            conn.status = PlatformConnectionStatus.DISCONNECTED
        else:
            conn = PlatformConnection(
                user_id=user_id,
                platform_name=platform_name,
                encrypted_api_key=encrypted_api_key,
                encrypted_api_secret=encrypted_api_secret,
            )
            self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def update_status(
        self, user_id: int, status: PlatformConnectionStatus
    ) -> Optional[PlatformConnection]:
        conn = self.get_by_user(user_id)
        if conn:
            conn.status = status
            self.db.commit()
            self.db.refresh(conn)
        return conn
