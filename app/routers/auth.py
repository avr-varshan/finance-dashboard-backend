from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models.token_blacklist import RevokedToken
from app.models.user import User, Role
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshRequest, ChangePasswordRequest
from app.schemas.common import SuccessResponse
from app.services.auth_service import verify_password, create_access_token, create_refresh_token, decode_token, validate_password_strength, get_password_hash, revoke_jti
from app.services.user_service import get_user_by_email, create_user
from app.dependencies import get_current_user
from app.utils.errors import InvalidCredentialsError, TokenRevokedError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


@router.post("/register", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED, description="Register new reviewer account")
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    validate_password_strength(payload.password)
    user = await create_user(db, payload, role=Role.viewer)
    return SuccessResponse(data={"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role.value}, message="Registration successful")


@router.post("/login", response_model=SuccessResponse, description="Login with credentials")
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid credentials")
    access_tokens = create_access_token(user)
    refresh_tokens = create_refresh_token(user)
    tokens = {**access_tokens, **refresh_tokens}
    return SuccessResponse(data=TokenResponse(**tokens, token_type="bearer").dict(), message="OK")


@router.post("/token", description="OAuth2 password token")
async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid credentials")

    access_tokens = create_access_token(user)
    refresh_tokens = create_refresh_token(user)
    return {
        "access_token": access_tokens["access_token"],
        "token_type": "bearer",
        "refresh_token": refresh_tokens["refresh_token"],
        "expires_in": access_tokens["expires_in"],
    }


@router.post("/refresh", response_model=SuccessResponse, description="Refresh JWT tokens")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise InvalidCredentialsError("Invalid credentials")

    existing = await db.execute(select(RevokedToken).where(RevokedToken.jti == decoded.get("jti")))
    if existing.scalars().first():
        raise TokenRevokedError("Token revoked")

    user = await db.get(User, decoded.get("sub"))
    if not user:
        raise InvalidCredentialsError("Invalid credentials")

    await revoke_jti(db, decoded.get("jti"), datetime.utcfromtimestamp(decoded.get("exp")))
    tokens = create_access_token(user)
    tokens.update(create_refresh_token(user))
    return SuccessResponse(data=TokenResponse(**tokens, token_type="bearer").dict())


@router.post("/logout", response_model=SuccessResponse, description="Logout from current session")
async def logout(current_user=Depends(get_current_user), token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    decoded = decode_token(token)
    jti = decoded.get("jti")
    exp = datetime.utcfromtimestamp(decoded.get("exp"))
    await revoke_jti(db, jti, exp)
    return SuccessResponse(message="Logged out successfully")


@router.post("/change-password", response_model=SuccessResponse, description="Change password")
async def change_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise InvalidCredentialsError("Invalid credentials")
    validate_password_strength(payload.new_password)
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    await db.commit()
    return SuccessResponse(message="Password updated")
