from __future__ import annotations

import uuid
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: str | uuid.UUID) -> Optional[User]:
    return db.get(User, uuid.UUID(str(user_id)))
