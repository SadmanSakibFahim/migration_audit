import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Load env for SECRET_KEY
load_dotenv()

app = FastAPI(title="Migration Audit Platform")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]
)  # Restrict this in production

# Session Middleware for Auth (Cookie-based)
# In prod, SECRET_KEY should be truly secret and random
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-default-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount Static Files
# Use absolute path based on this file's location to be safe
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
from core.web.routes import api

app.include_router(api.router)
