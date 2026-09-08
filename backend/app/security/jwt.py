import jwt
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Tuple, Dict
from app.core.config import settings
from app.security.exceptions import CredentialsException

def create_access_token(user_id: UUID, session_id: UUID, org_id: UUID) -> Tuple[str, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "sid": str(session_id),
        "org": str(org_id),
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, expire

def decode_access_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise CredentialsException(detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise CredentialsException(detail="Token expired")
    except jwt.InvalidTokenError:
        raise CredentialsException(detail="Invalid token")
