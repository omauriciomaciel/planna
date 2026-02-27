import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.user import UserRepository
from app.repositories.user_settings import UserSettingsRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(UTC) + expires_delta
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        settings_repo: UserSettingsRepository,
    ):
        self.user_repo = user_repo
        self.settings_repo = settings_repo

    async def register_user(self, email: str, name: str, password: str) -> User:
        user = User(email=email, name=name, password_hash=hash_password(password))
        self.user_repo.db.add(user)
        await self.user_repo.db.flush()

        user_settings = UserSettings(user_id=user.id)
        self.user_repo.db.add(user_settings)

        await self.user_repo.db.commit()
        await self.user_repo.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if user and verify_password(password, user.password_hash):
            return user
        return None

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self.user_repo.get_by_id(uuid.UUID(user_id))

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.user_repo.get_by_email(email)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_user_settings_repository(
    db: AsyncSession = Depends(get_db),
) -> UserSettingsRepository:
    return UserSettingsRepository(db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    settings_repo: UserSettingsRepository = Depends(get_user_settings_repository),
) -> AuthService:
    return AuthService(user_repo, settings_repo)
