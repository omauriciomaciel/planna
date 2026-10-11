from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import Household, HouseholdMember, Session, User
from app.security import hash_secret, session_cookie_name, verify_cookie


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


@dataclass
class AuthContext:
    user: User
    household: Household
    session: Session


async def get_auth_context(
    db: DbSession,
    session_cookie: Annotated[str | None, Cookie(alias=session_cookie_name())] = None,
) -> AuthContext:
    raw_cookie = verify_cookie(session_cookie) if session_cookie else None
    if raw_cookie is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    now = datetime.now(UTC)
    row = (
        await db.execute(
            select(User, Household, Session)
            .join(Session, Session.user_id == User.id)
            .join(HouseholdMember, HouseholdMember.user_id == User.id)
            .join(Household, Household.id == HouseholdMember.household_id)
            .where(
                Session.cookie_id == hash_secret(raw_cookie),
                Session.revoked_at.is_(None),
                Session.expires_at > now,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    return AuthContext(user=row[0], household=row[1], session=row[2])


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]
