from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET = os.getenv("AUTH_SECRET", "change-this-development-secret")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "60"))


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_value, digest_value = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode())
        expected = base64.urlsafe_b64decode(digest_value.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _load_users() -> dict[str, dict[str, str]]:
    raw = os.getenv("AUTH_USERS_JSON")
    if raw:
        users = json.loads(raw)
        if not isinstance(users, dict):
            raise RuntimeError("AUTH_USERS_JSON must be an object keyed by username")
        return users
    if os.getenv("APP_ENV", "development").lower() in {"production", "prod", "staging"} and "pytest" not in sys.modules:
        raise RuntimeError("AUTH_USERS_JSON must be configured outside development")
    return {
        "doctor": {"password_hash": _hash_password("doctor-demo", b"doctor-development-salt"), "role": "doctor", "display_name": "Development Doctor"},
        "nurse": {"password_hash": _hash_password("nurse-demo", b"nurse-development-salt"), "role": "nurse", "display_name": "Development Nurse"},
    }


USERS = _load_users()
security = HTTPBearer(auto_error=False)


class User(BaseModel):
    username: str
    role: str
    display_name: str


def authenticate(username: str, password: str) -> User | None:
    record = USERS.get(username)
    if not record or not _verify_password(password, record["password_hash"]):
        return None
    return User(username=username, role=record["role"], display_name=record["display_name"])


def create_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": user.username, "role": user.role, "exp": expires}, SECRET, algorithm=ALGORITHM)


def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        record = USERS.get(username)
        if not username or not role or not record or record["role"] != role:
            raise ValueError("invalid claims")
        return User(username=username, role=role, display_name=record["display_name"])
    except (JWTError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from error


def require_role(*roles: str):
    def dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot access this data")
        return user
    return dependency
