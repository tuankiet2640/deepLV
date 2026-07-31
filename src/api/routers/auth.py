import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.models.user import User
from src.api.services.auth import (
    create_access_token,
    get_user_by_email,
    hash_password,
    verify_password,
)

log = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    id: str
    email: str
    created_at: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    existing = await get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    user = User(email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    log.info("user_registered", user_id=str(user.id), email=user.email)
    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        created_at=user.created_at.isoformat(),
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    user = await get_user_by_email(db, req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.id)
    log.info("user_login", user_id=str(user.id))
    return LoginResponse(access_token=token, expires_in=86400)
