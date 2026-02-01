from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

# Load env for SECRET_KEY
load_dotenv()

app = FastAPI(title="Migration Audit Platform")

# Session Middleware for Auth (Cookie-based)
# In prod, SECRET_KEY should be truly secret and random
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-default-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount Static Files (if we have them, create dir even if empty for now)
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="core/web/templates")

@app.get("/")
async def root(request: Request):
    """Landing page - Redirect to Dashboard or Login"""
    from starlette.responses import RedirectResponse
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

# Include Routers
from core.web.routes import auth, dashboard
app.include_router(auth.router)
app.include_router(dashboard.router)
