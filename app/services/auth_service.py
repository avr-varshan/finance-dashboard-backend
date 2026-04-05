import re
import uuid
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.models.token_blacklist import RevokedToken
from app.models.user import User
from app.utils.errors import (
    InvalidCredentialsError,
    TokenExpiredError,
    UnauthorizedError,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_REGEX = re.compile(
    r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against stored bcrypt hash.
    Bcrypt supports only first 72 bytes, so truncate safely.
    """
    plain_password = str(plain_password).strip()[:72]
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash password safely for bcrypt.
    Prevents 72-byte bcrypt overflow issues.
    """
    password = str(password).strip()[:72]
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> None:
    """
    Require:
    - at least 8 chars
    - one uppercase
    - one digit
    - one special character
    """
    if not PASSWORD_REGEX.match(password):
        raise InvalidCredentialsError(
            "Weak password",
            details={
                "password": (
                    "Password must be at least 8 characters long "
                    "and include uppercase, digit, and special character."
                )
            },
        )


def _create_jwt_token(data: dict, expire_delta: timedelta) -> str:
    """
    Internal helper for access + refresh JWT creation.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + expire_delta

    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
    )

    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_access_token(user: User) -> dict:
    expires_in = int(settings.access_token_expires.total_seconds())

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }

    token = _create_jwt_token(
        token_data,
        settings.access_token_expires,
    )

    return {
        "access_token": token,
        "expires_in": expires_in,
    }


def create_refresh_token(user: User) -> dict:
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": "refresh",
    }

    token = _create_jwt_token(
        token_data,
        settings.refresh_token_expires,
    )

    return {"refresh_token": token}


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload

    except JWTError as exc:
        message = str(exc).lower()

        if "expired" in message:
            raise TokenExpiredError("Token expired")

        raise UnauthorizedError("Could not validate credentials")


async def is_revoked_jti(session, jti: str) -> bool:
    query = select(RevokedToken).where(RevokedToken.jti == jti)
    result = await session.execute(query)
    return result.scalars().first() is not None


async def revoke_jti(session, jti: str, expires_at: datetime) -> None:
    revoked = RevokedToken(
        jti=jti,
        expires_at=expires_at,
    )
    session.add(revoked)
    await session.commit()