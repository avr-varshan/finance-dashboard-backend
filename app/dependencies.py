from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.token_blacklist import RevokedToken
from app.models.user import User
from app.services.auth_service import decode_token, is_revoked_jti
from app.utils.errors import TokenRevokedError, UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_token(token)
    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not user_id or not jti:
        raise UnauthorizedError("Could not validate credentials")

    if await is_revoked_jti(db, jti):
        raise TokenRevokedError("Token revoked")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("Inactive user")

    return user


def require_role(*roles):
    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in [r.value for r in roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency
