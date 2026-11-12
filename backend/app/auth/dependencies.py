from typing import Optional
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.config import settings
from app.db.session import get_db
from app.models.database import User

security_scheme = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    token_param: Optional[str] = Query(None, alias="token"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Extracts user from Bearer header or '?token=' query parameter (used by EventSource).
    Returns User if authenticated, None if anonymous.
    """
    token = None
    if credentials:
        token = credentials.credentials
    elif token_param:
        token = token_param

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    user: Optional[User] = Depends(get_optional_current_user),
) -> User:
    """
    FastAPI dependency requiring an authenticated, active user.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def verify_ownership(
    resource_owner_id: Optional[str],
    current_user: Optional[User],
    resource_type: str = "Resource",
) -> None:
    """
    Verifies that the current user owns the target resource.
    - If resource has no owner (legacy/sample), access is allowed.
    - If resource has an owner and current user is unauthenticated, raises 401.
    - If resource owner != current_user and user is not superuser, raises 403.
    """
    if resource_owner_id is None:
        return

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required to access this {resource_type.lower()}.",
        )

    if current_user.is_superuser:
        return

    if current_user.id != resource_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: You do not own this {resource_type.lower()}.",
        )
