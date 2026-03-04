import os

import yaml
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="core/web/templates")


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    from core.audit.logger import log_audit_event

    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    db = getattr(request.state, "db", None)

    log_audit_event(
        "VIEW_DASHBOARD",
        user_id=user["username"],
        ip_address=request.client.host if request.client else "unknown",
        details="User accessed dashboard",
        db=db
    )

    # Load Config to see available tables
    config_path = "config/audit.yaml"
    tables = []
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            tables = list(cfg.get("tables", {}).keys())

    # List reports
    reports = []
    output_dir = "outputs"
    if os.path.exists(output_dir):
        # Just simple listing of subdirectories
        reports = sorted(
            [
                d
                for d in os.listdir(output_dir)
                if os.path.isdir(os.path.join(output_dir, d))
            ],
            reverse=True,
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "tables": tables, "reports": reports},
    )


@router.post("/run-audit")
async def run_audit_endpoint(request: Request, background_tasks: BackgroundTasks):
    from core.audit.logger import log_audit_event

    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    db = getattr(request.state, "db", None)

    log_audit_event(
        "TRIGGER_AUDIT",
        user_id=user["username"],
        ip_address=request.client.host if request.client else "unknown",
        details="User triggered new audit",
        db=db
    )

    # In a real app, we would read form data for specific tables
    # form = await request.form()
    # selected_tables = form.getlist("tables")

    # Trigger Audit in Background
    # We need to import run_audit here to avoid circular imports?
    # Or just run it as a subprocess to be safe/clean
    import subprocess

    def _run_audit_task():
        # Running via subprocess to ensure clean state and independence
        subprocess.run(
            ["python", "run_audit.py", "--no-auth", "--headless"], capture_output=True
        )

    # Dispatch the task to the FastAPI background worker pool securely
    background_tasks.add_task(_run_audit_task)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "tables": [],
            "reports": [],
            "message": "Audit triggered and is running in the background successfully via headless detached mode!",
        },
    )
