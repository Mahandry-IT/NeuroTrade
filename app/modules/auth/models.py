"""Entités auth — User + PlatformConnection."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PlatformConnectionStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    platform_connections = relationship("PlatformConnection", back_populates="user")


class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform_name = Column(String(100), nullable=False)  # ex: binance, bybit
    encrypted_api_key = Column(Text, nullable=False)  # Fernet — jamais en clair
    encrypted_api_secret = Column(Text, nullable=False)
    status = Column(Enum(PlatformConnectionStatus), default=PlatformConnectionStatus.DISCONNECTED)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="platform_connections")
