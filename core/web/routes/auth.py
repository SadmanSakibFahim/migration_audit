from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.auth.service import AuthService

router = APIRouter()
import os
from authlib.integrations.starlette_client import OAuth

router = APIRouter()
templates = Jinja2Templates(directory="core/web/templates")

oauth = OAuth()
oauth.register(
    name="sso",
    client_id=os.getenv("SSO_CLIENT_ID", "mock-client-id"),
    client_secret=os.getenv("SSO_CLIENT_SECRET", "mock-secret"),
    server_metadata_url=os.getenv("SSO_METADATA_URL", "https://accounts.google.com/.well-known/openid-configuration"),
    client_kwargs={
        "scope": "openid email profile"
    }
)

# Dependency to get DB session
# For MVP we create a new engine/session per request or re-use a global one.
# Best practice is dependency injection.
import os

from core.db.drivers import validate_driver_or_raise

DB_PATH = os.getenv("AUTH_DB_URI", "postgresql://postgres:postgres@localhost:5432/auth_db")
validate_driver_or_raise(DB_PATH)

connect_args = {"check_same_thread": False} if DB_PATH.startswith("sqlite") else {}
engine = create_engine(DB_PATH, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    from core.audit.logger import log_audit_event

    client_ip = request.client.host if request.client else "unknown"

    auth = AuthService(db)
    user = auth.authenticate_user(username, password)

    if not user:
        log_audit_event(
            "LOGIN_FAILED",
            user_id=username,
            ip_address=client_ip,
            details=f"Failed login attempt for {username}",
            db=db
        )
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid credentials"}
        )

    if not auth.check_access(user):
        log_audit_event(
            "LOGIN_DENIED",
            user_id=username,
            ip_address=client_ip,
            details=f"Access denied for {username} - License issue",
            db=db
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Access Denied: License Expired or Inactive"},
        )

    # Set Session
    request.session["user"] = {
        "username": user.username,
        "role": user.role,
        "id": user.id,
    }
    log_audit_event(
        "LOGIN_SUCCESS",
        user_id=username,
        ip_address=client_ip,
        details=f"User {username} logged in successfully",
        db=db
    )
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    from core.audit.logger import log_audit_event

    user = request.session.get("user")
    user_id = user["username"] if user else "anonymous"
    client_ip = request.client.host if request.client else "unknown"

    log_audit_event(
        "LOGOUT",
        user_id=user_id,
        ip_address=client_ip,
        details=f"User {user_id} logged out",
        db=db
    )

    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/login/sso")
async def login_via_sso(request: Request):
    """Initiates the SSO flow via Authlib"""
    redirect_uri = request.url_for("auth_callback")
    return await oauth.sso.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handles the SSO response mechanism after authenticating"""
    from core.audit.logger import log_audit_event
    client_ip = request.client.host if request.client else "unknown"
    
    token = await oauth.sso.authorize_access_token(request)
    user_info = token.get("userinfo")
    
    if not user_info or "email" not in user_info:
        return RedirectResponse(url="/login?error=sso_failed")

    auth = AuthService(db)
    
    # Check if user exists by SSO ID or just find by username (email)
    from core.auth.models import User
    user = db.query(User).filter_by(sso_id=user_info["sub"]).first()
    
    if not user:
        # Fallback to email mapping or reject if strict linking is required.
        user = db.query(User).filter_by(username=user_info["email"]).first()
        
        if user:
            # Associate missing SSO credentials
            user.sso_id = user_info["sub"]
            user.sso_provider = "oidc"
            db.commit()
    
    if not user:
        # Standard auto-provisioning could go here... skipping for MVP strict roles
        log_audit_event(
            "LOGIN_DENIED",
            user_id=user_info["email"],
            ip_address=client_ip,
            details=f"Unrecognized SSO user attempted to login: {user_info['email']}",
            db=db
        )
        return RedirectResponse(url="/login?error=unregistered_sso_user")
        
    if not auth.check_access(user):
        return RedirectResponse(url="/login?error=license_expired")
        
    request.session["user"] = {
        "username": user.username,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "id": user.id,
    }
    
    log_audit_event(
        "LOGIN_SUCCESS",
        user_id=user.username,
        ip_address=client_ip,
        details=f"User {user.username} logged in successfully via SSO",
        db=db
    )
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/api/token")
async def generate_token(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Issues API JWTs natively across clients based on core credentials"""
    auth = AuthService(db)
    user = auth.authenticate_user(username, password)
    
    if not user or not auth.check_access(user):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid API credentials or License")
        
    token = auth.create_jwt_token(user, os.getenv("SECRET_KEY", "fallback_secret_key_used_in_tests"))
    return {"access_token": token, "token_type": "bearer"}
