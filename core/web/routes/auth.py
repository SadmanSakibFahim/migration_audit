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
    auth = AuthService(db)
    user = auth.authenticate_user(username, password)
    
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    if not auth.check_access(user):
         return templates.TemplateResponse("login.html", {"request": request, "error": "Access Denied: License Expired or Inactive"})

    # Set Session
    request.session["user"] = {"username": user.username, "role": user.role, "id": user.id}
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
