import asyncio
import smtplib
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import DbSession
from app.models import Household, HouseholdMember, MagicLinkToken, Session, User
from app.schemas import HouseholdRead, MagicLinkRequest, MemberRead, MeRead, Message
from app.security import (
    email_limiter,
    hash_secret,
    ip_limiter,
    new_secret,
    session_cookie_name,
    sign_cookie,
    verify_cookie,
)

router = APIRouter(prefix="/auth", tags=["auth"])
SESSION_COOKIE = session_cookie_name()
MAGIC_LINK_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)
PRIVACY_VERSION = "2026-09-12"


def _send_email(recipient: str, link: str) -> None:
    if not settings.smtp_host:
        return

    message = EmailMessage()
    message["Subject"] = "Seu acesso ao Planna"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(f"Use este link em até 15 minutos para entrar no Planna:\n\n{link}")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def issue_magic_link(
    db: AsyncSession,
    email: str,
    ip: str | None,
    *,
    ai_consent: bool = False,
) -> tuple[str, str] | None:
    normalized = email.strip().lower()
    if not email_limiter.allow(normalized) or not ip_limiter.allow(ip or "unknown"):
        return None

    user = await db.scalar(select(User).where(User.email == normalized))
    if user is None:
        return None

    now = datetime.now(UTC)
    await db.execute(delete(MagicLinkToken).where(MagicLinkToken.expires_at <= now))
    await db.execute(
        delete(Session).where(or_(Session.expires_at <= now, Session.revoked_at.is_not(None)))
    )
    await db.execute(
        update(MagicLinkToken)
        .where(MagicLinkToken.email == normalized, MagicLinkToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = new_secret()
    user.privacy_accepted_at = now
    user.privacy_version = PRIVACY_VERSION
    user.ai_consent_at = now if ai_consent else None
    db.add(
        MagicLinkToken(
            email=normalized,
            token_hash=hash_secret(raw_token),
            expires_at=now + MAGIC_LINK_TTL,
            ip_request=ip,
        )
    )
    await db.commit()

    link = f"{settings.public_api_url}/auth/callback?token={quote(raw_token)}"
    return normalized, link


@dataclass
class AuthContext:
    user: User
    household: Household
    session: Session


async def get_auth_context(
    db: DbSession,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
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


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> Message:
    started = time.monotonic()
    delivery = await issue_magic_link(
        db,
        str(payload.email),
        request.client.host if request.client else None,
        ai_consent=payload.ai_consent,
    )
    if delivery and settings.smtp_host:
        background_tasks.add_task(_send_email, *delivery)
    await asyncio.sleep(max(0, 0.2 - (time.monotonic() - started)))
    return Message(
        message="Se o e-mail estiver autorizado, você receberá um link de acesso.",
        dev_link=(
            delivery[1]
            if delivery and settings.app_env == "development" and not settings.smtp_host
            else None
        ),
    )


@router.get("/callback", response_model=None)
async def auth_callback(
    token: Annotated[str, Query(min_length=32, max_length=128)], db: DbSession
) -> RedirectResponse:
    now = datetime.now(UTC)
    email = (
        await db.execute(
            update(MagicLinkToken)
            .where(
                MagicLinkToken.token_hash == hash_secret(token),
                MagicLinkToken.used_at.is_(None),
                MagicLinkToken.expires_at > now,
            )
            .values(used_at=now)
            .returning(MagicLinkToken.email)
        )
    ).scalar_one_or_none()
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Link inválido ou expirado"
        )

    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Link inválido ou expirado"
        )

    raw_cookie = new_secret()
    db.add(
        Session(
            user_id=user.id,
            cookie_id=hash_secret(raw_cookie),
            expires_at=now + SESSION_TTL,
        )
    )
    await db.commit()

    response = RedirectResponse(settings.frontend_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE,
        sign_cookie(raw_cookie),
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/logout")
async def logout(auth: CurrentAuth, db: DbSession, response: Response) -> Message:
    auth.session.revoked_at = datetime.now(UTC)
    await db.commit()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    return Message(message="Sessão encerrada.")


@router.get("/me")
async def me(auth: CurrentAuth, db: DbSession) -> MeRead:
    member_rows = (
        await db.execute(
            select(User, HouseholdMember)
            .join(HouseholdMember, HouseholdMember.user_id == User.id)
            .where(HouseholdMember.household_id == auth.household.id)
            .order_by(User.name)
        )
    ).all()
    members = [
        MemberRead(id=user.id, name=user.name, email=user.email, role=membership.role)
        for user, membership in member_rows
    ]
    return MeRead(
        id=auth.user.id,
        name=auth.user.name,
        email=auth.user.email,
        household=HouseholdRead(id=auth.household.id, name=auth.household.name, members=members),
    )
