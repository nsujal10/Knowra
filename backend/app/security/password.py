# Security domain placeholder

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not isinstance(hashed_password, str) or hashed_password.startswith("!"):
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
