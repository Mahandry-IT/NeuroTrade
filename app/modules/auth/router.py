"""Router auth — endpoints d'authentification + connexion plateforme."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.auth.service import AuthService
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    PlatformConnectRequest, PlatformStatusResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        return service.register(body.username, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        token = service.login(body.username, body.password)
        return TokenResponse(access_token=token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/platform-connect", response_model=dict)
def platform_connect(
    body: PlatformConnectRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return service.connect_platform(user_id, body.platform_name, body.api_key, body.api_secret)


@router.get("/platform-status", response_model=dict)
def platform_status(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    result = service.get_platform_status(user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No platform connected")
    return result
