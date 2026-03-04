from functools import wraps
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from core.auth.service import AuthService
from core.auth.models import User


from typing import Any, Optional

def requires_permission(action: str) -> Any:
    """Decorator for FastAPI endpoints that enforces a permission check.

    The decorated endpoint must accept a ``request`` argument so that the
    user's session can be accessed. A database session is retrieved from
    ``request.state.db`` (set via middleware or dependency in app). The
    decorator will load the full ``User`` object and call
    ``AuthService.check_permission``.

    If the user is not logged in or does not have the permission, a
    401/403 HTTPException is raised.
    """

    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            import os
            import jwt
            
            user_data = request.session.get("user")
            
            # If no session, try checking for an Authorization HTTP header
            if not user_data:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        secret = os.getenv("SECRET_KEY", "fallback_secret_key_used_in_tests")
                        payload = jwt.decode(token, secret, algorithms=["HS256"])
                        # Re-construct user_data mimicking the session behavior
                        user_data = {
                            "username": payload.get("username"),
                            "role": payload.get("role"),
                            "id": payload.get("sub")
                        }
                    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                        pass

            if not user_data:
                raise HTTPException(status_code=401, detail="Unauthorized")

            # attempt to load SQLAlchemy session from request.state
            db: Optional[Session] = getattr(request.state, "db", None)
            if db is None:
                raise HTTPException(
                    status_code=500,
                    detail="Database session not available for permission check",
                )

            user: Optional[User] = db.query(User).filter_by(username=user_data["username"]).first()
            if not user:
                raise HTTPException(status_code=401, detail="Unauthorized")

            auth = AuthService(db)
            if not auth.check_permission(user, action):
                raise HTTPException(status_code=403, detail="Forbidden")

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
