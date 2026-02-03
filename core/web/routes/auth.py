from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from core.auth.service import AuthService
from core.auth.models import User

router = APIRouter()
templates = Jinja2Templates(directory="core/web/templates")

# Dependency to get DB session
# For MVP we create a new engine/session per request or re-use a global one. 
# Best practice is dependency injection.
DB_PATH = "sqlite:///data/auth.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
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
    db: Session = Depends(get_db)
):
    from core.audit.logger import log_audit_event
    client_ip = request.client.host

    auth = AuthService(db)
    user = auth.authenticate_user(username, password)
    
    if not user:
        log_audit_event("LOGIN_FAILED", user_id=username, ip_address=client_ip, details=f"Failed login attempt for {username}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    if not auth.check_access(user):
         log_audit_event("LOGIN_DENIED", user_id=username, ip_address=client_ip, details=f"Access denied for {username} - License issue")
         return templates.TemplateResponse("login.html", {"request": request, "error": "Access Denied: License Expired or Inactive"})

    # Set Session
    request.session["user"] = {"username": user.username, "role": user.role, "id": user.id}
    log_audit_event("LOGIN_SUCCESS", user_id=username, ip_address=client_ip, details=f"User {username} logged in successfully")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def logout(request: Request):
    from core.audit.logger import log_audit_event
    user = request.session.get("user")
    user_id = user["username"] if user else "anonymous"
    client_ip = request.client.host
    
    log_audit_event("LOGOUT", user_id=user_id, ip_address=client_ip, details=f"User {user_id} logged out")
    
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
