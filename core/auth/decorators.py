from functools import wraps
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from core.auth.service import AuthService
from core.auth.models import User


def requires_permission(action: str):
    """Decorator for FastAPI endpoints that enforces a permission check.

    The decorated endpoint must accept a ``request`` argument so that the
    user's session can be accessed. A database session is retrieved from
    ``request.state.db`` (set via middleware or dependency in app). The
    decorator will load the full ``User`` object and call
    ``AuthService.check_permission``.

    If the user is not logged in or does not have the permission, a
    401/403 HTTPException is raised.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_data = request.session.get("user")
            if not user_data:
                raise HTTPException(status_code=401, detail="Unauthorized")

            # attempt to load SQLAlchemy session from request.state
            db: Session = getattr(request.state, "db", None)
            if db is None:
                raise HTTPException(
                    status_code=500,
                    detail="Database session not available for permission check",
                )

            user: User = db.query(User).filter_by(username=user_data["username"]).first()
            if not user:
                raise HTTPException(status_code=401, detail="Unauthorized")

            auth = AuthService(db)
            if not auth.check_permission(user, action):
                raise HTTPException(status_code=403, detail="Forbidden")

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
